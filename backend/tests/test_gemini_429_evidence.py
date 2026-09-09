import asyncio
import uuid

import pytest
from fastapi import HTTPException

from app.core.config import settings
from app.models.generation_job import GenerationJob
from app.models.project import Project
from app.models.scene import Scene
from app.models.shot import Shot
from app.providers.image.base import ImageGenerationParams
from app.providers.image.gemini_adapter import GeminiImageProviderAdapter
from app.services.keyframe_generation import KeyframeGenerationService
from app.services.pricing import ProviderPricingService


class _FakeResponse:
    def __init__(self, payload):
        self.status_code = 429
        self._payload = payload

    def json(self):
        return self._payload


class _FakeAsyncClient:
    def __init__(self, response, **_kwargs):
        self.response = response

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, _url, json, headers):
        assert json
        assert headers["x-goog-api-key"] == "test-key"
        return self.response


def _patch_429(monkeypatch, payload):
    response = _FakeResponse(payload)

    def factory(**kwargs):
        return _FakeAsyncClient(response, **kwargs)

    monkeypatch.setattr("app.providers.image.gemini_adapter.httpx.AsyncClient", factory)


def _run_429(monkeypatch, payload):
    _patch_429(monkeypatch, payload)
    adapter = GeminiImageProviderAdapter(api_key="test-key")
    return asyncio.run(
        adapter.generate_image(
            ImageGenerationParams(
                shot_id=str(uuid.uuid4()),
                prompt="A safe production keyframe",
            )
        )
    )


def _quota_payload(*, quota_metric, quota_id, quota_value="1", retry_delay=None):
    details = [
        {
            "@type": "type.googleapis.com/google.rpc.QuotaFailure",
            "violations": [
                {
                    "quotaMetric": quota_metric,
                    "quotaId": quota_id,
                    "quotaDimensions": {
                        "model": settings.GEMINI_IMAGE_MODEL,
                        "location": "global",
                        "project": "must-not-persist",
                    },
                    "quotaValue": quota_value,
                    "description": "private provider detail must not persist",
                }
            ],
        }
    ]
    if retry_delay is not None:
        details.append(
            {
                "@type": "type.googleapis.com/google.rpc.RetryInfo",
                "retryDelay": retry_delay,
                "debug": "must-not-persist",
            }
        )
    return {
        "error": {
            "code": 429,
            "status": "RESOURCE_EXHAUSTED",
            "message": "secret-bearing human message must not persist",
            "api_key": "test-key",
            "details": details,
        }
    }


def test_429_quota_zero_is_safely_classified(monkeypatch):
    payload = _quota_payload(
        quota_metric="generativelanguage.googleapis.com/generate_requests_per_model_per_day",
        quota_id="GenerateRequestsPerDayPerProjectPerModel-FreeTier",
        quota_value="0",
    )
    result = _run_429(monkeypatch, payload)

    assert result.status == "FAILED"
    assert result.status_code == 429
    assert result.retryable is True
    assert result.submission_uncertain is False
    assert result.raw_response == {
        "provider": "gemini_image",
        "model": settings.GEMINI_IMAGE_MODEL,
        "http_status": 429,
        "error_code": "HTTP_ERROR",
        "retryable": True,
        "submission_uncertain": False,
        "provider_status": "RESOURCE_EXHAUSTED",
        "quota_failures": [
            {
                "quota_metric": "generativelanguage.googleapis.com/generate_requests_per_model_per_day",
                "quota_id": "GenerateRequestsPerDayPerProjectPerModel-FreeTier",
                "quota_value": "0",
                "quota_dimensions": {
                    "model": settings.GEMINI_IMAGE_MODEL,
                    "location": "global",
                },
            }
        ],
        "quota_class": "QUOTA_ZERO",
    }
    rendered = str(result.raw_response)
    assert "secret-bearing" not in rendered
    assert "test-key" not in rendered
    assert "must-not-persist" not in rendered
    assert "project" not in rendered


def test_429_daily_quota_is_classified_without_message(monkeypatch):
    result = _run_429(
        monkeypatch,
        _quota_payload(
            quota_metric="generativelanguage.googleapis.com/generate_requests_per_model_per_day",
            quota_id="GenerateRequestsPerDayPerProjectPerModel-PaidTier",
            quota_value="100",
        ),
    )
    assert result.raw_response["quota_class"] == "DAILY_QUOTA"
    assert "message" not in result.raw_response


def test_429_rate_limit_and_retry_delay_are_allowlisted(monkeypatch):
    result = _run_429(
        monkeypatch,
        _quota_payload(
            quota_metric="generativelanguage.googleapis.com/generate_requests_per_model_per_minute",
            quota_id="GenerateRequestsPerMinutePerProjectPerModel",
            quota_value="10",
            retry_delay="42s",
        ),
    )
    assert result.raw_response["quota_class"] == "RATE_LIMIT"
    assert result.raw_response["retry_delay"] == "42s"


def test_429_unknown_detail_types_are_not_persisted(monkeypatch):
    payload = {
        "error": {
            "code": 429,
            "status": "RESOURCE_EXHAUSTED",
            "message": "private text",
            "details": [
                {
                    "@type": "type.googleapis.com/google.rpc.Help",
                    "links": [{"description": "private", "url": "https://example.invalid/private"}],
                },
                {
                    "@type": "type.googleapis.com/google.rpc.RetryInfo",
                    "retryDelay": "not-a-safe-delay",
                },
            ],
        }
    }
    result = _run_429(monkeypatch, payload)
    assert result.raw_response == {
        "provider": "gemini_image",
        "model": settings.GEMINI_IMAGE_MODEL,
        "http_status": 429,
        "error_code": "HTTP_ERROR",
        "retryable": True,
        "submission_uncertain": False,
        "provider_status": "RESOURCE_EXHAUSTED",
        "quota_class": "RESOURCE_EXHAUSTED",
    }


def test_non_dict_429_body_falls_back_to_base_http_evidence(monkeypatch):
    result = _run_429(monkeypatch, ["unexpected", "body"])
    assert result.raw_response == {
        "provider": "gemini_image",
        "model": settings.GEMINI_IMAGE_MODEL,
        "http_status": 429,
        "error_code": "HTTP_ERROR",
        "retryable": True,
        "submission_uncertain": False,
    }


def test_keyframe_service_persists_sanitized_429_quota_evidence(monkeypatch, db_session):
    ProviderPricingService.reset()
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "test-key")
    _patch_429(
        monkeypatch,
        _quota_payload(
            quota_metric="generativelanguage.googleapis.com/generate_requests_per_model_per_day",
            quota_id="GenerateRequestsPerDayPerProjectPerModel-FreeTier",
            quota_value="0",
            retry_delay="60s",
        ),
    )

    project = Project(
        title="Gemini 429 Evidence Project",
        video_mode="STORY",
        status="SHOT_PLAN_APPROVED",
        budget_limit=1.0,
    )
    db_session.add(project)
    db_session.flush()
    scene = Scene(project_id=project.id, scene_number=1)
    db_session.add(scene)
    db_session.flush()
    shot = Shot(
        scene_id=scene.id,
        shot_number=1,
        shot_type="AI_GENERATED",
        visual_prompt="A production keyframe",
    )
    db_session.add(shot)
    db_session.commit()

    with pytest.raises(HTTPException) as exc_info:
        KeyframeGenerationService.generate_shot_keyframe(
            db=db_session,
            project_id=project.id,
            shot_id=shot.id,
            provider_name="gemini_image",
            cost_authorized=True,
        )

    assert exc_info.value.status_code == 500
    job = db_session.query(GenerationJob).filter(GenerationJob.shot_id == shot.id).one()
    assert job.status == "FAILED"
    assert job.cost_usd == pytest.approx(0.0)
    assert job.result["http_status"] == 429
    assert job.result["provider_status"] == "RESOURCE_EXHAUSTED"
    assert job.result["quota_class"] == "QUOTA_ZERO"
    assert job.result["retry_delay"] == "60s"
    assert job.result["quota_failures"][0]["quota_value"] == "0"
    assert "secret-bearing" not in str(job.result)
    assert "test-key" not in str(job.result)
