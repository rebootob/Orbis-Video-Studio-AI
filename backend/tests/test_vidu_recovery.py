import asyncio
import hashlib
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.asset import Asset
from app.models.generation_job import GenerationJob
from app.models.project import Project
from app.models.scene import Scene
from app.models.shot import Shot
from app.providers.base import IVideoGenerationProviderAdapter, ProviderJobResult
from app.providers.vidu import ViduProviderAdapter
from app.services.vidu_recovery import (
    TARGET_HISTORICAL_PROVIDER_JOB_ID,
    ViduExistingJobRecoveryService,
    ViduJobNotCompletedError,
    ViduJobNotFoundError,
    ViduMissingOutputUrlError,
    ViduRecoveryError,
)


class MockViduAdapter(IVideoGenerationProviderAdapter):
    def __init__(self, job_result: ProviderJobResult):
        self.job_result = job_result
        self.check_status_calls = []
        self.submit_calls = []

    @property
    def provider_id(self):
        return "vidu"

    def validate_config(self, config):
        return True

    async def submit_generation_job(self, params):
        self.submit_calls.append(params)
        raise AssertionError("submit_generation_job MUST NEVER be called during recovery")

    async def check_job_status(self, provider_job_id):
        self.check_status_calls.append(provider_job_id)
        return self.job_result

    async def cancel_job(self, provider_job_id):
        return True


async def fake_downloader(url: str, target_file_path: str):
    data = b"RECOVERED_HISTORICAL_VIDU_VIDEO_BYTES_995880130565918720"
    with open(target_file_path, "wb") as f:
        f.write(data)
    return "video/mp4", len(data), hashlib.sha256(data).hexdigest()


def test_vidu_adapter_check_status_uses_get_and_never_posts():
    """Verify that ViduProviderAdapter.check_job_status issues GET, never POST."""
    adapter = ViduProviderAdapter(api_key="test-key", base_url="https://api.vidu.com")

    with patch.object(adapter, "_request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = ProviderJobResult(
            provider_job_id=TARGET_HISTORICAL_PROVIDER_JOB_ID,
            status="COMPLETED",
            video_url="https://video.example.invalid/out.mp4",
        )
        res = asyncio.run(adapter.check_job_status(TARGET_HISTORICAL_PROVIDER_JOB_ID))

        assert mock_request.await_count == 1
        call_args, call_kwargs = mock_request.call_args
        # First positional arg is method
        assert call_args[0] == "GET"
        assert f"/tasks/{TARGET_HISTORICAL_PROVIDER_JOB_ID}/creations" in call_args[1]
        assert "submitting" not in call_kwargs or call_kwargs["submitting"] is False


def test_recovery_service_queries_via_get_and_materializes(db_session, mock_storage):
    """Verify recovery executes GET-only, never calls submit, creates lineage, Asset, and binds Shot."""
    job_result = ProviderJobResult(
        provider_job_id=TARGET_HISTORICAL_PROVIDER_JOB_ID,
        status="COMPLETED",
        video_url="https://video.example.invalid/historical_run1.mp4",
        provider_credits=30.0,
    )
    adapter = MockViduAdapter(job_result)

    result = asyncio.run(
        ViduExistingJobRecoveryService.recover_existing_job(
            db_session,
            TARGET_HISTORICAL_PROVIDER_JOB_ID,
            adapter=adapter,
            storage_provider=mock_storage,
            downloader=fake_downloader,
        )
    )

    # Invariants verification
    assert len(adapter.submit_calls) == 0
    assert len(adapter.check_status_calls) == 1
    assert adapter.check_status_calls[0] == TARGET_HISTORICAL_PROVIDER_JOB_ID
    assert result.posts_attempted == 0
    assert result.get_calls_attempted == 1

    # Lineage verification
    asset = db_session.get(Asset, result.asset_id)
    assert asset is not None
    assert asset.asset_type == "VIDEO"
    assert asset.content_type == "video/mp4"
    assert asset.file_size_bytes == len(b"RECOVERED_HISTORICAL_VIDU_VIDEO_BYTES_995880130565918720")

    job = db_session.get(GenerationJob, result.generation_job_id)
    assert job is not None
    assert job.provider_job_id == TARGET_HISTORICAL_PROVIDER_JOB_ID
    assert job.output_asset_id == asset.id
    assert job.status == "COMPLETED"

    shot = db_session.get(Shot, result.shot_id)
    assert shot is not None
    assert shot.source_asset_id == asset.id

    project = db_session.get(Project, result.project_id)
    assert project is not None

    # Storage verification
    assert mock_storage.object_exists(asset.storage_bucket, asset.storage_key)

    # Billing conservatism verification
    assert result.provider_credits_reported == 30.0
    assert result.actual_credits_consumed == "UNKNOWN / NOT CONFIRMED"
    assert result.usd_equivalent == "UNKNOWN / NOT CONVERTED"


def test_recovery_is_idempotent_no_duplicate_asset_or_post(db_session, mock_storage):
    """Verify repeated recovery execution creates no new assets, no new jobs, no POSTs."""
    job_result = ProviderJobResult(
        provider_job_id=TARGET_HISTORICAL_PROVIDER_JOB_ID,
        status="COMPLETED",
        video_url="https://video.example.invalid/historical_run1.mp4",
        provider_credits=30.0,
    )
    adapter = MockViduAdapter(job_result)

    res1 = asyncio.run(
        ViduExistingJobRecoveryService.recover_existing_job(
            db_session,
            TARGET_HISTORICAL_PROVIDER_JOB_ID,
            adapter=adapter,
            storage_provider=mock_storage,
            downloader=fake_downloader,
        )
    )

    res2 = asyncio.run(
        ViduExistingJobRecoveryService.recover_existing_job(
            db_session,
            TARGET_HISTORICAL_PROVIDER_JOB_ID,
            adapter=adapter,
            storage_provider=mock_storage,
            downloader=fake_downloader,
        )
    )

    assert res1.asset_id == res2.asset_id
    assert res1.generation_job_id == res2.generation_job_id
    assert res1.shot_id == res2.shot_id
    # Second run detects already materialized and skips even the GET call
    assert len(adapter.submit_calls) == 0
    assert len(adapter.check_status_calls) == 1
    assert db_session.query(Asset).filter(Asset.project_id == res1.project_id).count() == 1


def test_recovery_fails_safely_when_provider_job_not_found(db_session, mock_storage):
    """Verify missing/deleted provider job stops safely with ViduJobNotFoundError and 0 POSTs."""
    job_result = ProviderJobResult(
        provider_job_id=TARGET_HISTORICAL_PROVIDER_JOB_ID,
        status="FAILED",
        provider_error_code="TASK_NOT_FOUND",
        status_code=404,
    )
    adapter = MockViduAdapter(job_result)

    with pytest.raises(ViduJobNotFoundError, match="not found"):
        asyncio.run(
            ViduExistingJobRecoveryService.recover_existing_job(
                db_session,
                TARGET_HISTORICAL_PROVIDER_JOB_ID,
                adapter=adapter,
                storage_provider=mock_storage,
                downloader=fake_downloader,
            )
        )

    assert len(adapter.submit_calls) == 0
    assert len(adapter.check_status_calls) == 1


def test_recovery_fails_safely_when_output_url_missing(db_session, mock_storage):
    """Verify provider COMPLETED without video_url fails with ViduMissingOutputUrlError."""
    job_result = ProviderJobResult(
        provider_job_id=TARGET_HISTORICAL_PROVIDER_JOB_ID,
        status="COMPLETED",
        video_url=None,
    )
    adapter = MockViduAdapter(job_result)

    with pytest.raises(ViduMissingOutputUrlError, match="no video_url present"):
        asyncio.run(
            ViduExistingJobRecoveryService.recover_existing_job(
                db_session,
                TARGET_HISTORICAL_PROVIDER_JOB_ID,
                adapter=adapter,
                storage_provider=mock_storage,
                downloader=fake_downloader,
            )
        )

    assert len(adapter.submit_calls) == 0
    assert len(adapter.check_status_calls) == 1


def test_recovery_fails_safely_when_task_not_completed(db_session, mock_storage):
    """Verify non-completed task status stops safely without materializing."""
    job_result = ProviderJobResult(
        provider_job_id=TARGET_HISTORICAL_PROVIDER_JOB_ID,
        status="PROCESSING",
        video_url=None,
    )
    adapter = MockViduAdapter(job_result)

    with pytest.raises(ViduJobNotCompletedError, match="not COMPLETED"):
        asyncio.run(
            ViduExistingJobRecoveryService.recover_existing_job(
                db_session,
                TARGET_HISTORICAL_PROVIDER_JOB_ID,
                adapter=adapter,
                storage_provider=mock_storage,
                downloader=fake_downloader,
            )
        )

    assert len(adapter.submit_calls) == 0


def test_recovery_rejects_unsafe_private_url(db_session, mock_storage):
    """Verify SSRF protection: private/non-https URL is rejected by VideoMaterializationService."""
    job_result = ProviderJobResult(
        provider_job_id=TARGET_HISTORICAL_PROVIDER_JOB_ID,
        status="COMPLETED",
        video_url="http://192.168.1.1/secret.mp4",
    )
    adapter = MockViduAdapter(job_result)

    with pytest.raises(ViduRecoveryError, match="Video materialization failed"):
        asyncio.run(
            ViduExistingJobRecoveryService.recover_existing_job(
                db_session,
                TARGET_HISTORICAL_PROVIDER_JOB_ID,
                adapter=adapter,
                storage_provider=mock_storage,
                # Using real downloader logic rather than fake to test URL validation
            )
        )

    assert len(adapter.submit_calls) == 0
