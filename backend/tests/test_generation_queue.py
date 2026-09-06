import pytest
import uuid
import httpx
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient

from app.models.project import Project
from app.models.story import Story
from app.models.scene import Scene
from app.models.shot import Shot
from app.models.asset import Asset
from app.models.generation_job import GenerationJob
from app.providers.base import (
    VideoGenerationParams,
    ProviderJobResult,
    ReferenceImageInput,
)
from app.providers.vidu import ViduProviderAdapter
from app.providers.factory import ProviderFactory
from app.services.job_dispatch import (
    JobDispatchService,
    is_retryable_error,
    sanitize_secret_text,
)


@pytest.fixture
def sample_shot(db_session):
    project = Project(id=uuid.uuid4(), title="Test Project Queue")
    db_session.add(project)
    db_session.commit()

    story = Story(id=uuid.uuid4(), project_id=project.id, logline="Test logline")
    db_session.add(story)
    db_session.commit()

    scene = Scene(id=uuid.uuid4(), story_id=story.id, scene_number=1, heading="INT. LAB - DAY")
    db_session.add(scene)
    db_session.commit()

    shot = Shot(
        id=uuid.uuid4(),
        scene_id=scene.id,
        shot_number=1,
        shot_type="MEDIUM_SHOT",
        video_prompt="A futuristic robot typing on a glowing cybernetic console.",
        duration_seconds=5.0,
    )
    db_session.add(shot)
    db_session.commit()
    db_session.refresh(shot)
    return shot


# 1. VIDU API CONTRACT & AUTH / HEADERS
def test_vidu_adapter_validate_config():
    adapter = ViduProviderAdapter(api_key="test_key")
    assert adapter.provider_id == "vidu"
    assert adapter.validate_config({}) is True

    adapter_invalid = ViduProviderAdapter(api_key="")
    assert adapter_invalid.validate_config({}) is False


def test_vidu_auth_header_and_secret_masking():
    adapter = ViduProviderAdapter(api_key="secret_vidu_key_123")
    headers = adapter._get_headers()
    # Must use Token {api_key} per official Vidu API contract
    assert headers["Authorization"] == "Token secret_vidu_key_123"
    assert "Bearer" not in headers["Authorization"]

    # Secret masking verification
    leaked_str = "Error with Authorization: Token secret_vidu_key_123 in request"
    sanitized = adapter._sanitize_error(leaked_str)
    assert "secret_vidu_key_123" not in sanitized
    assert "[REDACTED]" in sanitized


def test_provider_factory():
    provider = ProviderFactory.get_provider("vidu", api_key="test")
    assert isinstance(provider, ViduProviderAdapter)
    assert provider.provider_id == "vidu"

    with pytest.raises(ValueError, match="Unsupported provider"):
        ProviderFactory.get_provider("unknown_provider")


# 2. EXPLICIT TEXT-TO-VIDEO MAPPING
@pytest.mark.anyio
async def test_vidu_text_to_video_mapping():
    adapter = ViduProviderAdapter(
        api_key="mock_key",
        base_url="https://api.vidu.com/ent/v2",
        model="viduq2-pro",
    )
    params = VideoGenerationParams(
        shot_id=str(uuid.uuid4()),
        prompt="A neon cyber city in the rain",
        aspect_ratio="16:9",
        duration_seconds=4.0,
        seed=42,
    )

    mock_resp_data = {
        "task_id": "vidu_t2v_999",
        "state": "created",
    }
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_resp_data

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response

        res = await adapter.submit_generation_job(params)

        assert mock_post.call_count == 1
        call_url = mock_post.call_args[0][0]
        assert call_url == "https://api.vidu.com/ent/v2/text2video"

        sent_payload = mock_post.call_args[1]["json"]
        assert sent_payload["model"] == "viduq2-pro"
        assert sent_payload["prompt"] == "A neon cyber city in the rain"
        assert sent_payload["duration"] == 4
        assert sent_payload["aspect_ratio"] == "16:9"
        assert sent_payload["seed"] == 42
        assert "images" not in sent_payload

        assert res.provider_job_id == "vidu_t2v_999"
        assert res.status == "QUEUED"


# 3. EXPLICIT REFERENCE-TO-VIDEO MAPPING
@pytest.mark.anyio
async def test_vidu_reference_to_video_mapping():
    adapter = ViduProviderAdapter(
        api_key="mock_key",
        base_url="https://api.vidu.com/ent/v2",
        model="viduq2-pro",
    )
    params = VideoGenerationParams(
        shot_id=str(uuid.uuid4()),
        prompt="Character walking through neon market",
        aspect_ratio="16:9",
        duration_seconds=5.0,
        reference_images=[
            ReferenceImageInput(type="character", url="https://example.com/hero.png")
        ],
    )

    mock_resp_data = {
        "task_id": "vidu_r2v_888",
        "state": "queueing",
    }
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_resp_data

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response

        res = await adapter.submit_generation_job(params)

        assert mock_post.call_count == 1
        call_url = mock_post.call_args[0][0]
        assert call_url == "https://api.vidu.com/ent/v2/reference2video"

        sent_payload = mock_post.call_args[1]["json"]
        assert sent_payload["model"] == "viduq2-pro"
        assert sent_payload["images"] == ["https://example.com/hero.png"]

        assert res.provider_job_id == "vidu_r2v_888"
        assert res.status == "QUEUED"


# 4. SUBMIT / STATUS / CANCEL MOCKED
@pytest.mark.anyio
async def test_vidu_status_and_cancel_mocked():
    adapter = ViduProviderAdapter(api_key="mock_key", base_url="https://api.vidu.com/ent/v2")

    mock_status_data = {
        "id": "vidu_task_12345",
        "state": "success",
        "creations": [
            {
                "id": "creation_1",
                "url": "https://cdn.vidu.com/output.mp4",
                "cover_url": "https://cdn.vidu.com/cover.jpg",
            }
        ],
    }
    mock_get_response = MagicMock()
    mock_get_response.status_code = 200
    mock_get_response.json.return_value = mock_status_data

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_get_response
        res = await adapter.check_job_status("vidu_task_12345")

        assert mock_get.call_args[0][0] == "https://api.vidu.com/ent/v2/tasks/vidu_task_12345/creations"
        assert res.status == "COMPLETED"
        assert res.video_url == "https://cdn.vidu.com/output.mp4"
        assert res.thumbnail_url == "https://cdn.vidu.com/cover.jpg"

    # Test cancel
    mock_cancel_resp = MagicMock()
    mock_cancel_resp.status_code = 200
    mock_cancel_resp.json.return_value = {"state": "cancelled"}
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_cancel_resp
        cancelled = await adapter.cancel_job("vidu_task_12345")
        assert cancelled is True
        assert mock_post.call_args[0][0] == "https://api.vidu.com/ent/v2/tasks/vidu_task_12345/cancel"


# 5. RETRY CLASSIFICATION TESTS
def test_retry_classification_rules():
    # Retryable: network, timeout, 429, 5xx
    assert is_retryable_error(exc=httpx.ConnectTimeout("Connection timed out")) is True
    assert is_retryable_error(exc=httpx.NetworkError("Network reset")) is True
    assert is_retryable_error(status_code=429) is True
    assert is_retryable_error(status_code=500) is True
    assert is_retryable_error(status_code=503) is True
    assert is_retryable_error(error_message="Vidu API HTTP 504: Gateway Timeout") is True
    assert is_retryable_error(error_message="Rate limit 429 exceeded") is True

    # Non-retryable: 400, 401, 403, config, provider rejection, unsupported
    assert is_retryable_error(status_code=400) is False
    assert is_retryable_error(status_code=401) is False
    assert is_retryable_error(status_code=403) is False
    assert is_retryable_error(exc=ValueError("Invalid config")) is False
    assert is_retryable_error(error_message="Vidu API HTTP 401: Unauthorized") is False
    assert is_retryable_error(error_message="Content moderation rejected prompt") is False
    assert is_retryable_error(error_message="Policy violation: NSFW") is False
    assert is_retryable_error(error_message="Unsupported provider: xyz") is False


# 6. NO RETRY ON 400/401/403 & REJECTION
def test_no_retry_on_client_errors_and_rejection(client: TestClient, sample_shot):
    create_resp = client.post(
        "/api/v1/jobs",
        json={"shot_id": str(sample_shot.id), "provider_name": "vidu", "max_retries": 3},
    )
    job_id = create_resp.json()["id"]

    # 401 Unauthorized -> immediate FAILED without retrying
    fail_401 = ProviderJobResult(
        provider_job_id="",
        status="FAILED",
        error_message="Vidu API HTTP 401: Invalid Token",
        raw_response={"status_code": 401, "error": "Invalid Token"},
    )
    with patch.object(ViduProviderAdapter, "submit_generation_job", new_callable=AsyncMock) as mock_submit:
        mock_submit.return_value = fail_401
        res = client.post(f"/api/v1/jobs/{job_id}/dispatch")
        assert res.status_code == 200
        assert res.json()["status"] == "FAILED"
        assert res.json()["retry_count"] == 0  # No retry incremented

    # Provider moderation rejection -> immediate FAILED without retrying
    job_rejection = client.post(
        "/api/v1/jobs",
        json={"shot_id": str(sample_shot.id), "provider_name": "vidu", "max_retries": 3},
    ).json()["id"]

    rejection_result = ProviderJobResult(
        provider_job_id="",
        status="FAILED",
        error_message="Prompt rejected: content moderation policy violation",
        raw_response={"status_code": 400, "error": "Prompt rejected"},
    )
    with patch.object(ViduProviderAdapter, "submit_generation_job", new_callable=AsyncMock) as mock_submit:
        mock_submit.return_value = rejection_result
        res = client.post(f"/api/v1/jobs/{job_rejection}/dispatch")
        assert res.status_code == 200
        assert res.json()["status"] == "FAILED"
        assert res.json()["retry_count"] == 0


# 7. BOUNDED RETRY (TIMEOUT / 429 / 5XX)
def test_bounded_retry_behavior(client: TestClient, sample_shot):
    create_resp = client.post(
        "/api/v1/jobs",
        json={"shot_id": str(sample_shot.id), "provider_name": "vidu", "max_retries": 2},
    )
    job_id = create_resp.json()["id"]

    timeout_fail = ProviderJobResult(
        provider_job_id="",
        status="FAILED",
        error_message="Vidu API HTTP 504: Gateway Timeout",
        raw_response={"status_code": 504, "error": "Gateway Timeout"},
    )

    # 1st failure -> retry_count = 1, status reset to PENDING
    with patch.object(ViduProviderAdapter, "submit_generation_job", new_callable=AsyncMock) as mock_submit:
        mock_submit.return_value = timeout_fail
        res1 = client.post(f"/api/v1/jobs/{job_id}/dispatch")
        assert res1.json()["retry_count"] == 1
        assert res1.json()["status"] == "PENDING"

    # 2nd failure -> retry_count = 2 reaches max_retries=2 -> FAILED
    with patch.object(ViduProviderAdapter, "submit_generation_job", new_callable=AsyncMock) as mock_submit:
        mock_submit.return_value = timeout_fail
        res2 = client.post(f"/api/v1/jobs/{job_id}/dispatch")
        assert res2.json()["retry_count"] == 2
        assert res2.json()["status"] == "FAILED"


# 8. BOUNDED POLLING
@pytest.mark.anyio
async def test_bounded_polling(db_session, sample_shot):
    job = JobDispatchService.create_and_dispatch_job(
        db=db_session,
        shot_id=sample_shot.id,
        provider_name="vidu",
    )
    job.provider_job_id = "task_poll_limit_123"
    job.status = "PROCESSING"
    db_session.commit()

    mock_poll = ProviderJobResult(
        provider_job_id="task_poll_limit_123",
        status="PROCESSING",
        progress_percentage=20.0,
    )

    with patch.object(ViduProviderAdapter, "check_job_status", new_callable=AsyncMock) as mock_check:
        mock_check.return_value = mock_poll

        # Poll with max_polls = 2
        j1 = await JobDispatchService.poll_job_status(db=db_session, job_id=job.id, max_polls=2)
        assert j1.status == "PROCESSING"

        j2 = await JobDispatchService.poll_job_status(db=db_session, job_id=job.id, max_polls=2)
        assert j2.status == "PROCESSING"

        # 3rd poll exceeds max_polls=2 -> transitions to FAILED
        j3 = await JobDispatchService.poll_job_status(db=db_session, job_id=job.id, max_polls=2)
        assert j3.status == "FAILED"
        assert "Bounded polling limit exceeded" in (j3.error_message or "")


# 9. DB IDEMPOTENCY & CONCURRENCY
def test_db_idempotency_and_concurrency(client: TestClient, sample_shot):
    payload = {
        "shot_id": str(sample_shot.id),
        "provider_name": "vidu",
        "idempotency_key": "unique_idem_key_42",
    }
    r1 = client.post("/api/v1/jobs", json=payload)
    assert r1.status_code == 201
    job_id1 = r1.json()["id"]

    # Re-sending same shot + idempotency key returns existing job
    r2 = client.post("/api/v1/jobs", json=payload)
    assert r2.status_code == 201
    assert r2.json()["id"] == job_id1


# 10. NO DUPLICATE PROVIDER SUBMISSION AFTER RETRY / RESTART
@pytest.mark.anyio
async def test_no_duplicate_provider_submission(db_session, sample_shot):
    job = JobDispatchService.create_and_dispatch_job(
        db=db_session,
        shot_id=sample_shot.id,
        provider_name="vidu",
    )
    job.provider_job_id = "already_submitted_vidu_123"
    job.status = "PROCESSING"
    db_session.commit()

    # Re-dispatching an already submitted job MUST NOT call submit_generation_job
    with patch.object(ViduProviderAdapter, "submit_generation_job", new_callable=AsyncMock) as mock_submit:
        res = await JobDispatchService.process_job(db=db_session, job_id=job.id)
        assert mock_submit.call_count == 0
        assert res.provider_job_id == "already_submitted_vidu_123"
        assert res.status == "PROCESSING"


# 11. RESTART RECOVERY
def test_restart_recovery(db_session, sample_shot):
    # Job stuck in CLAIMED without provider_job_id
    stuck_job = GenerationJob(
        id=uuid.uuid4(),
        shot_id=sample_shot.id,
        provider_name="vidu",
        status="CLAIMED",
        provider_job_id=None,
        retry_count=0,
        max_retries=3,
    )
    # Active job in PROCESSING with provider_job_id
    active_job = GenerationJob(
        id=uuid.uuid4(),
        shot_id=sample_shot.id,
        provider_name="vidu",
        status="PROCESSING",
        provider_job_id="vidu_active_99",
        retry_count=0,
        max_retries=3,
    )
    db_session.add_all([stuck_job, active_job])
    db_session.commit()

    recovered = JobDispatchService.recover_pending_jobs(db=db_session)
    assert recovered >= 1

    db_session.refresh(stuck_job)
    db_session.refresh(active_job)

    # Stuck job without provider_job_id is reset to PENDING for retry
    assert stuck_job.status == "PENDING"
    # Active job with provider_job_id stays in PROCESSING (no re-submission)
    assert active_job.status == "PROCESSING"
    assert active_job.provider_job_id == "vidu_active_99"


# 12. SECRET LEAKAGE PREVENTION
def test_secret_leakage_safety():
    raw_error = "Failed connecting to https://api.vidu.com with Token abc123supersecret and password=pass456"
    sanitized = sanitize_secret_text(raw_error)
    assert "abc123supersecret" not in sanitized
    assert "pass456" not in sanitized
    assert "[REDACTED]" in sanitized


# 13. OUTPUT ASSET SAFETY (NO FABRICATED ASSET RECORD)
@pytest.mark.anyio
async def test_no_fabricated_asset_metadata(db_session, sample_shot):
    job = JobDispatchService.create_and_dispatch_job(
        db=db_session,
        shot_id=sample_shot.id,
        provider_name="vidu",
    )
    job.provider_job_id = "task_done_777"
    job.status = "PROCESSING"
    db_session.commit()

    completed_result = ProviderJobResult(
        provider_job_id="task_done_777",
        status="COMPLETED",
        progress_percentage=100.0,
        video_url="https://storage.vidu.com/rendered_output.mp4",
        thumbnail_url="https://storage.vidu.com/thumb.jpg",
    )

    with patch.object(ViduProviderAdapter, "check_job_status", new_callable=AsyncMock) as mock_check:
        mock_check.return_value = completed_result
        polled_job = await JobDispatchService.poll_job_status(db=db_session, job_id=job.id)

        assert polled_job.status == "COMPLETED"
        # Output Asset Safety:
        # 1. output_asset_id MUST BE NONE (no fake Asset created)
        assert polled_job.output_asset_id is None
        # 2. No Asset in DB with dummy sha256 or 0 file size
        fake_assets = (
            db_session.query(Asset)
            .filter(Asset.checksum_sha256 == "0000000000000000000000000000000000000000000000000000000000000000")
            .all()
        )
        assert len(fake_assets) == 0
        # 3. Provider video_url safely kept in result
        assert polled_job.result["video_url"] == "https://storage.vidu.com/rendered_output.mp4"


# 14. DB-BACKED CLAIM / WORKER BEHAVIOR
def test_db_claim_worker_behavior(db_session, sample_shot):
    j1 = JobDispatchService.create_and_dispatch_job(
        db=db_session, shot_id=sample_shot.id, provider_name="vidu"
    )
    j2 = JobDispatchService.create_and_dispatch_job(
        db=db_session, shot_id=sample_shot.id, provider_name="vidu"
    )

    # Worker claims first job
    claimed1 = JobDispatchService.claim_next_job(db=db_session, worker_id="worker_1")
    assert claimed1 is not None
    assert claimed1.id == j1.id
    assert claimed1.status == "CLAIMED"

    # Next claim gets second job
    claimed2 = JobDispatchService.claim_next_job(db=db_session, worker_id="worker_2")
    assert claimed2 is not None
    assert claimed2.id == j2.id
    assert claimed2.status == "CLAIMED"

    # Third claim returns None (all claimed)
    claimed3 = JobDispatchService.claim_next_job(db=db_session)
    assert claimed3 is None

