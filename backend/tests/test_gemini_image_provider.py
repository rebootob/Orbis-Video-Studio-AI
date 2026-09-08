import asyncio
import base64
import hashlib
import uuid

import pytest

from app.models.asset import Asset
from app.models.project import Project
from app.models.scene import Scene
from app.models.shot import Shot
from app.providers.image.base import ImageGenerationParams, ReferenceImageInput
from app.providers.image.factory import ImageProviderFactory
from app.providers.image.gemini_adapter import GeminiImageProviderAdapter
from app.services.image_generation import reference_materializer as materializer


class _FakeResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload or {}

    def json(self):
        return self._payload


class _FakeAsyncClient:
    def __init__(self, response, captured, **_kwargs):
        self.response = response
        self.captured = captured

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, url, json, headers):
        self.captured["url"] = url
        self.captured["json"] = json
        self.captured["headers"] = headers
        return self.response


def _patch_http(monkeypatch, response):
    captured = {}

    def factory(**kwargs):
        return _FakeAsyncClient(response, captured, **kwargs)

    monkeypatch.setattr("app.providers.image.gemini_adapter.httpx.AsyncClient", factory)
    return captured


def _success_payload(image_bytes=b"jpeg-bytes", interaction_id="int-123", include_usage=True):
    payload = {
        "id": interaction_id,
        "status": "completed",
        "steps": [
            {
                "type": "model_output",
                "content": [
                    {
                        "type": "image",
                        "mime_type": "image/jpeg",
                        "data": base64.b64encode(image_bytes).decode("ascii"),
                    }
                ],
            }
        ],
    }
    if include_usage:
        payload["usage"] = {
            "input_tokens_by_modality": [{"modality": "text", "tokens": 24}],
            "output_tokens_by_modality": [{"modality": "image", "tokens": 1120}],
        }
    return payload


def test_factory_registers_real_provider_without_removing_mock():
    assert ImageProviderFactory.get_provider("mock_image").provider_id == "mock_image"
    adapter = ImageProviderFactory.get_provider("gemini_image", api_key="test-key")
    assert isinstance(adapter, GeminiImageProviderAdapter)
    assert adapter.provider_id == "gemini_image"


def test_missing_credentials_fail_closed_without_http(monkeypatch):
    def forbidden_client(**_kwargs):
        raise AssertionError("HTTP must not be opened with invalid credentials")

    monkeypatch.setattr("app.providers.image.gemini_adapter.httpx.AsyncClient", forbidden_client)
    adapter = GeminiImageProviderAdapter(api_key="")
    result = asyncio.run(
        adapter.generate_image(
            ImageGenerationParams(shot_id=str(uuid.uuid4()), prompt="A cinematic factory keyframe")
        )
    )
    assert result.status == "FAILED"
    assert result.error_code == "INVALID_CONFIG"
    assert result.submission_uncertain is False


def test_success_maps_aspect_ratio_inline_image_and_metered_cost(monkeypatch):
    image_bytes = b"\xff\xd8fake-jpeg\xff\xd9"
    captured = _patch_http(monkeypatch, _FakeResponse(200, _success_payload(image_bytes)))
    adapter = GeminiImageProviderAdapter(api_key="test-key")
    result = asyncio.run(
        adapter.generate_image(
            ImageGenerationParams(
                shot_id=str(uuid.uuid4()),
                prompt="A technician inspecting a precision mold",
                aspect_ratio="16:9",
                negative_prompt="blurry, duplicate people",
            )
        )
    )

    assert result.status == "COMPLETED"
    assert result.provider_job_id == "int-123"
    assert result.image_data == image_bytes
    assert result.content_type == "image/jpeg"
    assert result.cost_usd == pytest.approx(0.067212)
    assert captured["json"]["response_format"]["aspect_ratio"] == "16:9"
    assert captured["json"]["response_format"]["image_size"] == "1K"
    assert "Avoid these visual elements" in captured["json"]["input"][-1]["text"]
    assert captured["headers"]["x-goog-api-key"] == "test-key"
    assert result.raw_response["usage_summary"] == {
        "input_tokens": 24,
        "output_text_tokens": 0,
        "output_image_tokens": 1120,
    }
    assert "usage" not in (result.raw_response or {})
    assert "test-key" not in str(result.raw_response)


def test_completed_image_without_cost_evidence_requires_reconciliation(monkeypatch):
    _patch_http(monkeypatch, _FakeResponse(200, _success_payload(include_usage=False)))
    adapter = GeminiImageProviderAdapter(api_key="test-key")
    result = asyncio.run(
        adapter.generate_image(
            ImageGenerationParams(shot_id=str(uuid.uuid4()), prompt="A safe image prompt")
        )
    )
    assert result.status == "COMPLETED"
    assert result.image_data is not None
    assert result.cost_usd is None
    assert result.submission_uncertain is True
    assert result.error_code == "COST_EVIDENCE_MISSING"


def test_reference_images_are_materialized_and_sent_inline(monkeypatch):
    captured = _patch_http(monkeypatch, _FakeResponse(200, _success_payload()))
    calls = []

    def resolver(url):
        calls.append(url)
        return b"reference-bytes", "image/png"

    adapter = GeminiImageProviderAdapter(api_key="test-key", reference_resolver=resolver)
    params = ImageGenerationParams(
        shot_id=str(uuid.uuid4()),
        prompt="Keep the same employee and location continuity",
        aspect_ratio="9:16",
        reference_images=[
            ReferenceImageInput(type="character", url=f"/assets/{uuid.uuid4()}/download"),
            ReferenceImageInput(type="location", url=f"/assets/{uuid.uuid4()}/download"),
        ],
    )
    result = asyncio.run(adapter.generate_image(params))

    assert result.status == "COMPLETED"
    assert len(calls) == 2
    assert captured["json"]["response_format"]["aspect_ratio"] == "9:16"
    image_blocks = [b for b in captured["json"]["input"] if b["type"] == "image"]
    assert len(image_blocks) == 2
    assert all(base64.b64decode(block["data"]) == b"reference-bytes" for block in image_blocks)
    assert result.raw_response["reference_count"] == 2


def test_unsupported_seed_and_unknown_provider_params_fail_before_http(monkeypatch):
    def forbidden_client(**_kwargs):
        raise AssertionError("HTTP must not be opened for unsupported params")

    monkeypatch.setattr("app.providers.image.gemini_adapter.httpx.AsyncClient", forbidden_client)
    adapter = GeminiImageProviderAdapter(api_key="test-key")

    seeded = asyncio.run(
        adapter.generate_image(
            ImageGenerationParams(shot_id=str(uuid.uuid4()), prompt="shot", seed=42)
        )
    )
    assert seeded.error_code == "UNSUPPORTED_SEED"

    unknown = asyncio.run(
        adapter.generate_image(
            ImageGenerationParams(
                shot_id=str(uuid.uuid4()),
                prompt="shot",
                provider_specific_params={"grounding": True},
            )
        )
    )
    assert unknown.error_code == "UNSUPPORTED_PROVIDER_PARAMETERS"


def test_http_503_is_retryable_and_submission_uncertain(monkeypatch):
    _patch_http(monkeypatch, _FakeResponse(503, {"error": {"message": "do not persist me"}}))
    adapter = GeminiImageProviderAdapter(api_key="test-key")
    result = asyncio.run(
        adapter.generate_image(
            ImageGenerationParams(shot_id=str(uuid.uuid4()), prompt="A safe prompt")
        )
    )
    assert result.status == "FAILED"
    assert result.error_code == "HTTP_ERROR"
    assert result.status_code == 503
    assert result.retryable is True
    assert result.submission_uncertain is True
    assert result.raw_response is None


class _NonClosingSessionContext:
    def __init__(self, session):
        self.session = session

    def __enter__(self):
        return self.session

    def __exit__(self, exc_type, exc, tb):
        return False


def test_reference_materializer_enforces_project_ownership(monkeypatch, db_session, mock_storage):
    project = Project(title="Owner Project", video_mode="STORY", status="SHOT_PLAN_APPROVED")
    other = Project(title="Other Project", video_mode="STORY", status="SHOT_PLAN_APPROVED")
    db_session.add_all([project, other])
    db_session.flush()
    scene = Scene(project_id=project.id, scene_number=1)
    db_session.add(scene)
    db_session.flush()
    shot = Shot(scene_id=scene.id, shot_number=1, shot_type="AI_GENERATED", visual_prompt="shot")
    db_session.add(shot)

    payload = b"reference-image"
    asset = Asset(
        project_id=project.id,
        name="Hero reference",
        original_filename="hero.png",
        asset_type="REFERENCE",
        content_type="image/png",
        file_size_bytes=len(payload),
        checksum_sha256=hashlib.sha256(payload).hexdigest(),
        storage_bucket="test",
        storage_key="refs/hero.png",
    )
    foreign_asset = Asset(
        project_id=other.id,
        name="Foreign reference",
        original_filename="foreign.png",
        asset_type="REFERENCE",
        content_type="image/png",
        file_size_bytes=len(payload),
        checksum_sha256=hashlib.sha256(payload).hexdigest(),
        storage_bucket="test",
        storage_key="refs/foreign.png",
    )
    db_session.add_all([asset, foreign_asset])
    db_session.commit()
    mock_storage.put_object("test", "refs/hero.png", payload, "image/png")
    mock_storage.put_object("test", "refs/foreign.png", payload, "image/png")

    monkeypatch.setattr(materializer, "SessionLocal", lambda: _NonClosingSessionContext(db_session))
    monkeypatch.setattr(materializer, "get_storage_provider", lambda: mock_storage)

    resolved, mime = materializer.materialize_reference_image(
        f"/assets/{asset.id}/download", str(shot.id)
    )
    assert resolved == payload
    assert mime == "image/png"

    with pytest.raises(materializer.ReferenceMaterializationError, match="REFERENCE_PROJECT_MISMATCH"):
        materializer.materialize_reference_image(
            f"/assets/{foreign_asset.id}/download", str(shot.id)
        )

    with pytest.raises(materializer.ReferenceMaterializationError, match="REFERENCE_URL_UNSUPPORTED"):
        materializer.materialize_reference_image("https://example.com/image.png", str(shot.id))
