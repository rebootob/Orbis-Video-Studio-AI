import asyncio
import hashlib
import uuid
from unittest.mock import AsyncMock, patch

import pytest

from app.models.asset import Asset
from app.models.generation_job import GenerationJob
from app.models.project import Project
from app.models.scene import Scene
from app.models.shot import Shot
from app.models.usage_ledger import UsageLedger
from app.providers.base import ProviderJobResult
from app.providers.factory import ProviderFactory
from app.services.job_dispatch import JobDispatchService
from app.services.video_materialization import VideoMaterializationError, VideoMaterializationService


class CompletedProvider:
    @property
    def provider_id(self):
        return "vidu"

    def validate_config(self, config):
        return True

    async def submit_generation_job(self, params):
        return ProviderJobResult(
            provider_job_id=f"materialize-{params.shot_id}",
            status="COMPLETED",
            video_url=f"https://video.example.invalid/{params.shot_id}.mp4",
            cost_usd=0.123,
        )

    async def check_job_status(self, provider_job_id):
        return ProviderJobResult(
            provider_job_id=provider_job_id,
            status="COMPLETED",
            video_url=f"https://video.example.invalid/{provider_job_id}.mp4",
            cost_usd=0.123,
        )

    async def cancel_job(self, provider_job_id):
        return True


def seed(db):
    project = Project(
        id=uuid.uuid4(),
        title="Video materialization",
        video_mode="STORY",
        status="SHOT_PLAN_APPROVED",
        budget_limit=10.0,
    )
    db.add(project)
    db.flush()
    scene = Scene(id=uuid.uuid4(), project_id=project.id, scene_number=1)
    db.add(scene)
    db.flush()
    shot = Shot(
        id=uuid.uuid4(),
        scene_id=scene.id,
        shot_number=1,
        shot_type="AI_GENERATED",
        visual_prompt="safe prompt",
        duration_seconds=4.0,
    )
    db.add(shot)
    db.commit()
    return project, shot


async def fake_download(url, target_file_path):
    payload = b"ORBIT_VIDEO_MATERIALIZATION_TEST"
    with open(target_file_path, "wb") as output:
        output.write(payload)
    return "video/mp4", len(payload), hashlib.sha256(payload).hexdigest()


def test_completed_video_materializes_asset_and_is_idempotent(db_session, mock_storage):
    project, shot = seed(db_session)
    job = GenerationJob(
        id=uuid.uuid4(),
        shot_id=shot.id,
        job_type="VIDEO",
        provider_name="vidu",
        provider_job_id="already-complete",
        status="PROCESSING",
    )
    db_session.add(job)
    db_session.commit()
    result = ProviderJobResult(
        provider_job_id="already-complete",
        status="COMPLETED",
        video_url="https://video.example.invalid/out.mp4",
        cost_usd=0.123,
    )

    first = asyncio.run(VideoMaterializationService.materialize_completed_result(
        db_session, job.id, result, storage_provider=mock_storage, downloader=fake_download
    ))
    second = asyncio.run(VideoMaterializationService.materialize_completed_result(
        db_session, job.id, result, storage_provider=mock_storage, downloader=fake_download
    ))
    assert first.id == second.id
    db_session.refresh(job)
    db_session.refresh(shot)
    assert job.output_asset_id == first.id
    assert shot.source_asset_id == first.id
    assert db_session.query(Asset).filter(Asset.project_id == project.id, Asset.asset_type == "VIDEO").count() == 1
    assert mock_storage.object_exists(first.storage_bucket, first.storage_key)


def test_completed_provider_with_materialization_failure_requires_reconciliation(db_session, mock_storage):
    project, shot = seed(db_session)
    job = JobDispatchService.create_and_dispatch_job(
        db_session,
        shot.id,
        provider_name="vidu",
        idempotency_key="wp020-materialization-failure",
    )
    claimed = JobDispatchService.claim_next_job(db_session, worker_id="materialization-test", job_id=job.id)
    assert claimed is not None

    async def broken_download(url, target_file_path):
        raise VideoMaterializationError("synthetic local persistence failure")

    with (
        patch.object(ProviderFactory, "get_provider", return_value=CompletedProvider()),
        patch("app.services.video_materialization.get_storage_provider", return_value=mock_storage),
        patch.object(
            VideoMaterializationService,
            "_download_video_to_file",
            new=AsyncMock(side_effect=broken_download),
        ),
    ):
        settled = asyncio.run(JobDispatchService.process_job(
            db_session, job.id, claim_token=claimed.claim_token
        ))

    assert settled.status == "RECONCILIATION_REQUIRED"
    assert settled.output_asset_id is None
    db_session.refresh(shot)
    assert shot.source_asset_id is None
    ledger = db_session.query(UsageLedger).filter(UsageLedger.job_id == job.id).one()
    assert ledger.cost_status == "CONFIRMED"
    assert ledger.actual_cost == pytest.approx(0.123)


def test_materializer_rejects_private_or_non_https_urls():
    with pytest.raises(VideoMaterializationError):
        asyncio.run(VideoMaterializationService._validate_public_https_url("http://example.com/video.mp4"))
    with pytest.raises(VideoMaterializationError):
        asyncio.run(VideoMaterializationService._validate_public_https_url("https://127.0.0.1/video.mp4"))
