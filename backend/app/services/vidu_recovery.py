"""Vidu existing provider job recovery service.

Strict invariants:
1. VIDU_GENERATION_POSTS = 0 (never calls submit_generation_job or POST /text2video /reference2video).
2. GET-only recovery: queries existing provider_job_id using check_job_status.
3. Durable lineage reconstruction: idempotently binds Project -> Scene -> Shot -> GenerationJob -> VIDEO Asset.
4. Billing conservatism: provider credits reported are treated as historical/non-deductive; never claims USD=0 or exact balance deduction.
"""
from __future__ import annotations

import logging
import re
import uuid
from dataclasses import dataclass
from typing import Optional

from sqlalchemy.orm import Session

from app.models.asset import Asset
from app.models.generation_job import GenerationJob
from app.models.project import Project
from app.models.scene import Scene
from app.models.shot import Shot
from app.providers.base import IVideoGenerationProviderAdapter, ProviderJobResult
from app.providers.vidu import ViduProviderAdapter
from app.services.storage import ObjectStorageProvider
from app.services.video_materialization import (
    DownloadFn,
    VideoMaterializationError,
    VideoMaterializationService,
)

logger = logging.getLogger(__name__)

TARGET_HISTORICAL_PROVIDER_JOB_ID = "995880130565918720"


class ViduRecoveryError(RuntimeError):
    """Base error for recovery failures."""
    pass


class ViduJobNotFoundError(ViduRecoveryError):
    """Provider reports task does not exist."""
    pass


class ViduJobNotCompletedError(ViduRecoveryError):
    """Provider task is not in COMPLETED state."""
    pass


class ViduMissingOutputUrlError(ViduRecoveryError):
    """Provider completed without output video URL."""
    pass


@dataclass(frozen=True)
class ViduRecoveryResult:
    provider_job_id: str
    status: str
    asset_id: uuid.UUID
    generation_job_id: uuid.UUID
    shot_id: uuid.UUID
    project_id: uuid.UUID
    storage_bucket: str
    storage_key: str
    content_type: str
    file_size_bytes: int
    checksum_sha256: str
    provider_credits_reported: Optional[float]
    actual_credits_consumed: str = "UNKNOWN / NOT CONFIRMED"
    usd_equivalent: str = "UNKNOWN / NOT CONVERTED"
    posts_attempted: int = 0
    get_calls_attempted: int = 1


class ViduExistingJobRecoveryService:
    @staticmethod
    def ensure_or_reconstruct_lineage(
        db: Session,
        *,
        provider_job_id: str,
        project_title: str = "WP020 Reconstructed Video Project",
        scene_number: int = 1,
        shot_number: int = 1,
    ) -> tuple[Project, Scene, Shot, GenerationJob]:
        """Ensure deterministic lineage exists for this provider_job_id without overwriting existing records.

        Uses deterministic UUIDs derived from provider_job_id so repeated runs are completely idempotent.
        """
        if not provider_job_id or not re.fullmatch(r"[A-Za-z0-9_-]{1,255}", provider_job_id):
            raise ViduRecoveryError("Invalid provider_job_id format")

        project_id = uuid.uuid5(uuid.NAMESPACE_URL, f"orbis://vidu-recovery/project/{provider_job_id}")
        scene_id = uuid.uuid5(uuid.NAMESPACE_URL, f"orbis://vidu-recovery/scene/{provider_job_id}/{scene_number}")
        shot_id = uuid.uuid5(uuid.NAMESPACE_URL, f"orbis://vidu-recovery/shot/{provider_job_id}/{shot_number}")
        job_id = uuid.uuid5(uuid.NAMESPACE_URL, f"orbis://vidu-recovery/job/{provider_job_id}")

        project = db.get(Project, project_id)
        if not project:
            project = Project(
                id=project_id,
                title=project_title,
                video_mode="STORY",
                status="SHOT_PLAN_APPROVED",
                budget_limit=10.0,
            )
            db.add(project)
            db.flush()

        scene = db.get(Scene, scene_id)
        if not scene:
            scene = Scene(
                id=scene_id,
                project_id=project.id,
                scene_number=scene_number,
                heading="Recovered Scene",
            )
            db.add(scene)
            db.flush()

        shot = db.get(Shot, shot_id)
        if not shot:
            shot = Shot(
                id=shot_id,
                scene_id=scene.id,
                shot_number=shot_number,
                shot_type="AI_GENERATED",
                visual_prompt=f"Recovered Shot for Vidu task {provider_job_id}",
                duration_seconds=4.0,
            )
            db.add(shot)
            db.flush()

        job = db.get(GenerationJob, job_id)
        if not job:
            job = GenerationJob(
                id=job_id,
                shot_id=shot.id,
                job_type="VIDEO",
                provider_name="vidu",
                provider_job_id=provider_job_id,
                status="PROCESSING",
            )
            db.add(job)
            db.flush()
        else:
            if job.shot_id != shot.id:
                raise ViduRecoveryError("Existing GenerationJob shot_id mismatch")
            if job.provider_job_id != provider_job_id:
                raise ViduRecoveryError("Existing GenerationJob provider_job_id mismatch")

        db.commit()
        return project, scene, shot, job

    @classmethod
    async def recover_existing_job(
        cls,
        db: Session,
        provider_job_id: str,
        *,
        adapter: Optional[IVideoGenerationProviderAdapter] = None,
        storage_provider: Optional[ObjectStorageProvider] = None,
        downloader: Optional[DownloadFn] = None,
    ) -> ViduRecoveryResult:
        """Query provider by GET only and materialize into durable Asset & Shot lineage.

        HARD INVARIANT: No calls to submit_generation_job, zero POST requests.
        """
        if not provider_job_id or not isinstance(provider_job_id, str):
            raise ViduRecoveryError("provider_job_id must be a non-empty string")

        # 1. Ensure deterministic lineage
        project, scene, shot, job = cls.ensure_or_reconstruct_lineage(db, provider_job_id=provider_job_id)

        # 2. Check if already materialized
        asset_id = uuid.uuid5(uuid.NAMESPACE_URL, f"orbis://video-generation/{job.id}")
        existing_asset = db.get(Asset, asset_id)
        if existing_asset and job.output_asset_id == existing_asset.id and shot.source_asset_id == existing_asset.id:
            logger.info("Provider job %s already durably materialized", provider_job_id)
            return ViduRecoveryResult(
                provider_job_id=provider_job_id,
                status="COMPLETED",
                asset_id=existing_asset.id,
                generation_job_id=job.id,
                shot_id=shot.id,
                project_id=project.id,
                storage_bucket=existing_asset.storage_bucket,
                storage_key=existing_asset.storage_key,
                content_type=existing_asset.content_type,
                file_size_bytes=existing_asset.file_size_bytes,
                checksum_sha256=existing_asset.checksum_sha256,
                provider_credits_reported=None,
                posts_attempted=0,
                get_calls_attempted=0,
            )

        # 3. GET status from provider (Strictly check_job_status, NO POST)
        vidu_adapter = adapter or ViduProviderAdapter()
        job_result: ProviderJobResult = await vidu_adapter.check_job_status(provider_job_id)

        # 4. Handle provider response safely
        if job_result.status == "FAILED":
            if job_result.provider_error_code in ("TASK_NOT_FOUND", "NOT_FOUND") or job_result.status_code == 404:
                raise ViduJobNotFoundError(f"Provider task {provider_job_id} not found")
            raise ViduRecoveryError(f"Provider task failed: {job_result.error_code or job_result.error_message}")

        if job_result.status != "COMPLETED":
            raise ViduJobNotCompletedError(
                f"Provider task is not COMPLETED (current status: {job_result.status})"
            )

        if not job_result.video_url:
            raise ViduMissingOutputUrlError("Provider reported COMPLETED but no video_url present")

        # 5. Materialize into Orbis object storage, Asset, GenerationJob, and Shot
        try:
            asset = await VideoMaterializationService.materialize_completed_result(
                db,
                job.id,
                job_result,
                storage_provider=storage_provider,
                downloader=downloader,
            )
            job.status = "COMPLETED"
            db.flush()
            db.commit()
        except VideoMaterializationError as exc:
            db.rollback()
            raise ViduRecoveryError(f"Video materialization failed: {exc}") from exc

        return ViduRecoveryResult(
            provider_job_id=provider_job_id,
            status="COMPLETED",
            asset_id=asset.id,
            generation_job_id=job.id,
            shot_id=shot.id,
            project_id=project.id,
            storage_bucket=asset.storage_bucket,
            storage_key=asset.storage_key,
            content_type=asset.content_type,
            file_size_bytes=asset.file_size_bytes,
            checksum_sha256=asset.checksum_sha256,
            provider_credits_reported=job_result.provider_credits,
            posts_attempted=0,
            get_calls_attempted=1,
        )
