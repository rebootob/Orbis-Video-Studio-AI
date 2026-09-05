import pytest
import uuid
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient

from app.models.project import Project
from app.models.story import Story
from app.models.scene import Scene
from app.models.shot import Shot
from app.models.generation_job import GenerationJob
from app.providers.base import (
    VideoGenerationParams,
    ProviderJobResult,
)
from app.providers.vidu import ViduProviderAdapter
from app.providers.factory import ProviderFactory


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


def test_vidu_adapter_validate_config():
    adapter = ViduProviderAdapter(api_key="test_key")
    assert adapter.provider_id == "vidu"
    assert adapter.validate_config({}) is True

    adapter_invalid = ViduProviderAdapter(api_key="")
    assert adapter_invalid.validate_config({}) is False


def test_provider_factory():
    provider = ProviderFactory.get_provider("vidu", api_key="test")
    assert isinstance(provider, ViduProviderAdapter)
    assert provider.provider_id == "vidu"

    with pytest.raises(ValueError, match="Unsupported provider"):
        ProviderFactory.get_provider("unknown_provider")


@pytest.mark.anyio
async def test_vidu_adapter_submit_job_mocked():
    adapter = ViduProviderAdapter(api_key="mock_key", base_url="https://api.vidu.com/v1")
    params = VideoGenerationParams(
        shot_id=str(uuid.uuid4()),
        prompt="A high tech laboratory with blue lights",
        aspect_ratio="16:9",
        duration_seconds=4.0,
    )

    mock_resp_data = {
        "id": "vidu_task_12345",
        "state": "QUEUED",
        "progress": 0.0,
    }

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_resp_data

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response

        res = await adapter.submit_generation_job(params)

        assert res.provider_job_id == "vidu_task_12345"
        assert res.status == "QUEUED"
        assert res.progress_percentage == 0.0


@pytest.mark.anyio
async def test_vidu_adapter_check_status_mocked():
    adapter = ViduProviderAdapter(api_key="mock_key", base_url="https://api.vidu.com/v1")

    mock_resp_data = {
        "id": "vidu_task_12345",
        "state": "SUCCESS",
        "progress": 100.0,
        "video_url": "https://cdn.vidu.com/output.mp4",
    }

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_resp_data

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response

        res = await adapter.check_job_status("vidu_task_12345")

        assert res.provider_job_id == "vidu_task_12345"
        assert res.status == "COMPLETED"
        assert res.video_url == "https://cdn.vidu.com/output.mp4"


def test_create_job_endpoint(client: TestClient, sample_shot):
    payload = {
        "shot_id": str(sample_shot.id),
        "provider_name": "vidu",
        "idempotency_key": "key_001",
    }
    response = client.post("/api/v1/jobs", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["shot_id"] == str(sample_shot.id)
    assert data["status"] == "PENDING"
    assert data["idempotency_key"] == "key_001"
    job_id = data["id"]

    # Idempotency check
    response_dup = client.post("/api/v1/jobs", json=payload)
    assert response_dup.status_code == 201
    assert response_dup.json()["id"] == job_id


def test_dispatch_and_poll_job_flow(client: TestClient, sample_shot):
    # 1. Create job
    create_resp = client.post(
        "/api/v1/jobs",
        json={"shot_id": str(sample_shot.id), "provider_name": "vidu"},
    )
    assert create_resp.status_code == 201
    job_id = create_resp.json()["id"]

    # 2. Mock Vidu submission in dispatch
    mock_submit_result = ProviderJobResult(
        provider_job_id="vidu_job_999",
        status="PROCESSING",
        progress_percentage=10.0,
    )
    with patch.object(ViduProviderAdapter, "submit_generation_job", new_callable=AsyncMock) as mock_submit:
        mock_submit.return_value = mock_submit_result
        dispatch_resp = client.post(f"/api/v1/jobs/{job_id}/dispatch")
        assert dispatch_resp.status_code == 200
        assert dispatch_resp.json()["status"] == "PROCESSING"
        assert dispatch_resp.json()["provider_job_id"] == "vidu_job_999"

    # 3. Mock Vidu status check in poll
    mock_poll_result = ProviderJobResult(
        provider_job_id="vidu_job_999",
        status="COMPLETED",
        progress_percentage=100.0,
        video_url="https://storage.vidu.com/render.mp4",
    )
    with patch.object(ViduProviderAdapter, "check_job_status", new_callable=AsyncMock) as mock_poll:
        mock_poll.return_value = mock_poll_result
        poll_resp = client.post(f"/api/v1/jobs/{job_id}/poll")
        assert poll_resp.status_code == 200
        assert poll_resp.json()["status"] == "COMPLETED"
        assert poll_resp.json()["output_asset_id"] is not None


def test_retry_and_bounded_failure_behavior(client: TestClient, sample_shot):
    # Create job with max_retries=2
    create_resp = client.post(
        "/api/v1/jobs",
        json={"shot_id": str(sample_shot.id), "provider_name": "vidu", "max_retries": 2},
    )
    job_id = create_resp.json()["id"]

    fail_result = ProviderJobResult(
        provider_job_id="",
        status="FAILED",
        error_message="Simulated Vidu Rate Limit Error",
    )

    # First failed dispatch -> retry_count=1, status reset to PENDING
    with patch.object(ViduProviderAdapter, "submit_generation_job", new_callable=AsyncMock) as mock_submit:
        mock_submit.return_value = fail_result
        res1 = client.post(f"/api/v1/jobs/{job_id}/dispatch")
        assert res1.status_code == 200
        assert res1.json()["retry_count"] == 1
        assert res1.json()["status"] == "PENDING"

    # Second failed dispatch -> retry_count=2, max_retries reached -> status FAILED
    with patch.object(ViduProviderAdapter, "submit_generation_job", new_callable=AsyncMock) as mock_submit:
        mock_submit.return_value = fail_result
        res2 = client.post(f"/api/v1/jobs/{job_id}/dispatch")
        assert res2.status_code == 200
        assert res2.json()["retry_count"] == 2
        assert res2.json()["status"] == "FAILED"
