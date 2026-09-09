from __future__ import annotations

import importlib.util
import uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.models.project import Project
from app.models.scene import Scene
from app.models.shot import Shot
from app.models.story import Story
from app.providers.base import ProviderJobResult, VideoGenerationParams
from app.providers.factory import ProviderFactory
from app.providers.safety import safe_result
from app.providers.vidu import ViduProviderAdapter
from app.services.job_dispatch import JobDispatchService

ROOT = Path(__file__).resolve().parents[2]
R4_CONTRACT = ROOT / ".github" / "scripts" / "wp020_live_r4_contract.py"


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture(autouse=True)
def deny_unmocked_http(monkeypatch):
    async def denied(*args, **kwargs):
        raise AssertionError("Unmocked provider HTTP is forbidden in R4-C1 tests")

    monkeypatch.setattr(httpx.AsyncClient, "send", denied)


def _load_contract():
    spec = importlib.util.spec_from_file_location("wp020_live_r4_c1_contract_test", R4_CONTRACT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _response(data, status=200):
    return httpx.Response(status, json=data, request=httpx.Request("POST", "https://mock.invalid"))


def _make_shot(db):
    project = Project(id=uuid.uuid4(), title="R4 C1", status="SHOT_PLAN_APPROVED")
    story = Story(id=uuid.uuid4(), project_id=project.id, logline="Evidence")
    scene = Scene(id=uuid.uuid4(), story_id=story.id, scene_number=1, heading="INT. TEST")
    shot = Shot(
        id=uuid.uuid4(),
        scene_id=scene.id,
        shot_number=1,
        shot_type="AI_GENERATED",
        video_prompt="A safe reconciliation test",
        duration_seconds=4,
    )
    db.add_all([project, story, scene, shot])
    db.commit()
    return shot


@pytest.mark.anyio
async def test_vidu_failed_state_preserves_only_safe_reconciliation_metadata():
    adapter = ViduProviderAdapter(api_key="fake-provider-key", model="viduq2")
    provider_payload = {
        "task_id": "task-vidu-r4-c1",
        "state": "failed",
        "err_code": "CONTENT_POLICY",
        "credits": 3.5,
        "error_message": {"authorization": "LEAK"},
        "raw": {"api_key": "LEAK"},
    }
    with patch.object(
        httpx.AsyncClient,
        "request",
        new_callable=AsyncMock,
        return_value=_response(provider_payload),
    ):
        result = await adapter.submit_generation_job(
            VideoGenerationParams(shot_id="shot", prompt="Tree", duration_seconds=4)
        )

    assert result.status == "FAILED"
    assert result.provider_job_id == "task-vidu-r4-c1"
    assert result.error_code == "PROVIDER_REJECTED"
    assert result.provider_status == "failed"
    assert result.provider_error_code == "CONTENT_POLICY"
    assert result.provider_credits == 3.5
    assert result.raw_response is None
    serialized = result.model_dump_json()
    assert "LEAK" not in serialized
    assert "error_message" not in provider_payload or "LEAK" not in serialized


@pytest.mark.anyio
async def test_vidu_unsafe_provider_metadata_is_dropped():
    adapter = ViduProviderAdapter(api_key="fake-provider-key", model="viduq2")
    provider_payload = {
        "task_id": "task-safe",
        "state": "failed",
        "err_code": "authorization=LEAK",
        "credits": float("inf"),
    }
    with patch.object(
        httpx.AsyncClient,
        "request",
        new_callable=AsyncMock,
        return_value=_response(provider_payload),
    ):
        result = await adapter.submit_generation_job(
            VideoGenerationParams(shot_id="shot", prompt="Tree", duration_seconds=4)
        )

    assert result.status == "FAILED"
    assert result.provider_job_id == "task-safe"
    assert result.provider_error_code is None
    assert result.provider_credits is None
    assert "LEAK" not in result.model_dump_json()


def test_safe_result_keeps_typed_reconciliation_fields_and_drops_raw_content():
    result = ProviderJobResult(
        provider_job_id="task-vidu-r4-c1",
        status="FAILED",
        error_code="PROVIDER_REJECTED",
        error_message="password=LEAK",
        retryable=False,
        submission_uncertain=False,
        provider_status="failed",
        provider_error_code="CONTENT_POLICY",
        provider_credits=3.5,
        raw_response={"authorization": "LEAK"},
    )

    evidence = safe_result(result)
    assert evidence["provider_job_id"] == "task-vidu-r4-c1"
    assert evidence["error_code"] == "PROVIDER_REJECTED"
    assert evidence["retryable"] is False
    assert evidence["submission_uncertain"] is False
    assert evidence["provider_status"] == "failed"
    assert evidence["provider_error_code"] == "CONTENT_POLICY"
    assert evidence["provider_credits"] == 3.5
    assert "error_message" not in evidence
    assert "raw_response" not in evidence
    assert "LEAK" not in repr(evidence)


@pytest.mark.anyio
async def test_terminal_vidu_failure_metadata_survives_durable_queue_boundary(db_session):
    shot = _make_shot(db_session)
    adapter = AsyncMock()
    adapter.validate_config = lambda config: True
    adapter.submit_generation_job.return_value = ProviderJobResult(
        provider_job_id="task-durable-r4-c1",
        status="FAILED",
        error_code="PROVIDER_REJECTED",
        provider_status="failed",
        provider_error_code="CONTENT_POLICY",
        provider_credits=2.0,
        retryable=False,
        submission_uncertain=False,
        raw_response={"authorization": "LEAK"},
    )

    with patch.object(ProviderFactory, "get_provider", return_value=adapter):
        job = JobDispatchService.create_and_dispatch_job(
            db_session,
            shot.id,
            provider_name="vidu",
            idempotency_key="r4-c1-durable-failure",
            custom_params={"resolution": "720p"},
            max_retries=1,
        )
        claimed = JobDispatchService.claim_next_job(db_session, worker_id="r4-c1", job_id=job.id)
        assert claimed is not None
        stored = await JobDispatchService.process_job(
            db_session,
            job.id,
            claim_token=claimed.claim_token,
        )

    assert stored.status == "FAILED"
    assert stored.result["provider_job_id"] == "task-durable-r4-c1"
    assert stored.result["error_code"] == "PROVIDER_REJECTED"
    assert stored.result["provider_status"] == "failed"
    assert stored.result["provider_error_code"] == "CONTENT_POLICY"
    assert stored.result["provider_credits"] == 2.0
    assert "LEAK" not in repr(stored.result)
    assert adapter.submit_generation_job.await_count == 1


def test_r4_failure_sanitizer_labels_estimate_and_unknown_external_billing():
    contract = _load_contract()
    job = SimpleNamespace(
        id="job-r4-c1",
        provider_name="vidu",
        provider_job_id=None,
        status="FAILED",
        job_type="VIDEO",
        cost_usd=0.15,
        result={
            "provider_job_id": "task-vidu-r4-c1",
            "error_code": "PROVIDER_REJECTED",
            "retryable": False,
            "submission_uncertain": False,
            "provider_status": "failed",
            "provider_error_code": "CONTENT_POLICY",
            "provider_credits": 3.5,
            "raw_body": "LEAK",
        },
    )

    evidence = contract.sanitize_generation_job(job)
    assert evidence["provider_job_id"] == "task-vidu-r4-c1"
    assert evidence["estimated_cost_usd"] == 0.15
    assert evidence["cost_status"] == "ESTIMATED"
    assert evidence["external_billing_status"] == "UNKNOWN"
    assert "cost_usd" not in evidence
    assert evidence["result"]["provider_error_code"] == "CONTENT_POLICY"
    assert evidence["result"]["provider_credits"] == 3.5
    assert "raw_body" not in evidence["result"]
    assert "LEAK" not in repr(evidence)
