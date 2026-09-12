"""Vidu existing provider job recovery service.

Strict invariants:
1. HARD BOUND: Only authorized historical provider job ID is TARGET_HISTORICAL_PROVIDER_JOB_ID ("995880130565918720").
   All other IDs fail closed immediately before provider requests, DB writes, or storage writes.
2. ZERO GENERATION POSTS: VIDU_GENERATION_POSTS = 0 (never calls submit_generation_job or POST endpoints).
3. GET-ONLY: Queries existing provider_job_id via check_job_status only.
4. TRANSACTION ATOMICITY: No partial/ghost DB lineage on failure. Provider verification happens first;
   DB commit happens only after materialization succeeds. Newly uploaded storage objects are cleaned up on error.
5. HISTORICAL FENCING: GenerationJob has imported_historical=True and execution_disabled=True.
   Cannot be claimed, dispatched, polled, or retried by live workers.
6. CONSERVATIVE BILLING: No live spend added; UsageLedger (if tracked) has imported_historical=True, actual_cost=None;
   credits reported (30.0) are preserved as historical metadata only.
"""
from __future__ import annotations

import logging
import os
import re
import tempfile
import uuid
from dataclasses import dataclass
from typing import Optional

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.asset import Asset
from app.models.generation_job import GenerationJob
from app.models.project import Project
from app.models.scene import Scene
from app.models.shot import Shot
from app.models.usage_ledger import UsageLedger
from app.providers.base import IVideoGenerationProviderAdapter, ProviderJobResult
from app.providers.vidu import ViduProviderAdapter
from app.services.storage import ObjectStorageProvider, get_storage_provider
from app.services.video_materialization import (
    DownloadFn,
    VideoMaterializationError,
    VideoMaterializationService,
    _utc_now,
)

logger = logging.getLogger(__name__)

TARGET_HISTORICAL_PROVIDER_JOB_ID = "995880130565918720"


class ViduRecoveryError(RuntimeError):
    """Base error for recovery failures."""
    pass


class ViduUnauthorizedJobError(ViduRecoveryError):
    """Attempted to recover an unauthorized provider job ID."""
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


class ViduConflictingLineageError(ViduRecoveryError):
    """Existing database records conflict with deterministic recovery lineage."""
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
    imported_historical: bool = True
    execution_disabled: bool = True
    idempotent_reused: bool = False


class ViduExistingJobRecoveryService:
    @classmethod
    def validate_authorized_job_id(cls, provider_job_id: str) -> None:
        """Enforce strict bounding to the exact authorized historical provider job ID."""
        if provider_job_id != TARGET_HISTORICAL_PROVIDER_JOB_ID:
            raise ViduUnauthorizedJobError(
                f"Unauthorized provider job ID '{provider_job_id}'. "
                f"Only historical task '{TARGET_HISTORICAL_PROVIDER_JOB_ID}' is authorized for recovery."
            )

    @classmethod
    def ensure_or_reconstruct_lineage(
        cls,
        db: Session,
        *,
        provider_job_id: str,
        project_title: str = "WP020 Historical Recovered Video Project",
        scene_number: int = 1,
        shot_number: int = 1,
    ) -> tuple[Project, Scene, Shot, GenerationJob]:
        """Ensure deterministic lineage exists for this provider_job_id without committing prematurely.

        Fails closed on any conflicting parent/child hierarchy.
        Fences GenerationJob with imported_historical=True and execution_disabled=True.
        """
        cls.validate_authorized_job_id(provider_job_id)

        project_id = uuid.uuid5(uuid.NAMESPACE_URL, f"orbis://vidu-recovery/project/{provider_job_id}")
        scene_id = uuid.uuid5(uuid.NAMESPACE_URL, f"orbis://vidu-recovery/scene/{provider_job_id}/{scene_number}")
        shot_id = uuid.uuid5(uuid.NAMESPACE_URL, f"orbis://vidu-recovery/shot/{provider_job_id}/{shot_number}")
        job_id = uuid.uuid5(uuid.NAMESPACE_URL, f"orbis://vidu-recovery/job/{provider_job_id}")

        # 1. Project
        project = db.get(Project, project_id)
        if not project:
            # Notice: budget_limit is NOT a live UAT budget; this project is an imported historical container.
            project = Project(
                id=project_id,
                title=project_title,
                video_mode="STORY",
                status="COMPLETED",
                budget_limit=None,
            )
            db.add(project)
            db.flush()

        # 2. Scene
        scene = db.get(Scene, scene_id)
        if not scene:
            scene = Scene(
                id=scene_id,
                project_id=project.id,
                scene_number=scene_number,
                heading="Recovered Historical Scene",
            )
            db.add(scene)
            db.flush()
        else:
            if scene.project_id != project.id:
                raise ViduConflictingLineageError(
                    f"Existing Scene {scene.id} project_id {scene.project_id} conflicts with {project.id}"
                )

        # 3. Shot
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
        else:
            if shot.scene_id != scene.id:
                raise ViduConflictingLineageError(
                    f"Existing Shot {shot.id} scene_id {shot.scene_id} conflicts with {scene.id}"
                )

        # 4. GenerationJob
        job = db.get(GenerationJob, job_id)
        if not job:
            job = GenerationJob(
                id=job_id,
                shot_id=shot.id,
                job_type="VIDEO",
                provider_name="vidu",
                provider_job_id=provider_job_id,
                status="COMPLETED",
                imported_historical=True,
                execution_disabled=True,
            )
            db.add(job)
            db.flush()
        else:
            if job.shot_id != shot.id:
                raise ViduConflictingLineageError(
                    f"Existing GenerationJob {job.id} shot_id {job.shot_id} conflicts with {shot.id}"
                )
            if job.provider_job_id != provider_job_id:
                raise ViduConflictingLineageError(
                    f"Existing GenerationJob {job.id} provider_job_id {job.provider_job_id} conflicts with {provider_job_id}"
                )
            # Ensure historical fence is permanently active
            job.imported_historical = True
            job.execution_disabled = True
            db.flush()

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
        commit: bool = True,
    ) -> ViduRecoveryResult:
        """Query provider by GET only and materialize into durable Asset & Shot lineage.

        HARD INVARIANTS:
        - Only TARGET_HISTORICAL_PROVIDER_JOB_ID is accepted.
        - Zero POST requests / zero submit_generation_job calls.
        - Transaction atomicity: no ghost DB records on error; compensates newly created storage objects.
        """
        # Step 1: Preflight ID bounding BEFORE any GET, DB, or storage calls
        cls.validate_authorized_job_id(provider_job_id)

        # Step 2: GET status from provider BEFORE committing or creating DB lineage
        vidu_adapter = adapter or ViduProviderAdapter()
        job_result: ProviderJobResult = await vidu_adapter.check_job_status(provider_job_id)

        # Step 3: Validate provider response strictly
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

        # Check if already fully materialized and idempotent
        job_id = uuid.uuid5(uuid.NAMESPACE_URL, f"orbis://vidu-recovery/job/{provider_job_id}")
        asset_id = uuid.uuid5(uuid.NAMESPACE_URL, f"orbis://video-generation/{job_id}")
        project_id = uuid.uuid5(uuid.NAMESPACE_URL, f"orbis://vidu-recovery/project/{provider_job_id}")
        scene_id = uuid.uuid5(uuid.NAMESPACE_URL, f"orbis://vidu-recovery/scene/{provider_job_id}/1")
        shot_id = uuid.uuid5(uuid.NAMESPACE_URL, f"orbis://vidu-recovery/shot/{provider_job_id}/1")
        ledger_id = uuid.uuid5(uuid.NAMESPACE_URL, f"orbis://vidu-recovery/ledger/{provider_job_id}")

        existing_asset = db.get(Asset, asset_id)
        existing_job = db.get(GenerationJob, job_id)
        existing_project = db.get(Project, project_id)
        existing_scene = db.get(Scene, scene_id)
        existing_shot = db.get(Shot, shot_id)
        existing_ledger = db.get(UsageLedger, ledger_id)

        if existing_asset and existing_job:
            # 1. Deterministic relationship validation (Fail closed on conflicting state)
            if existing_job.provider_job_id != provider_job_id:
                raise ViduConflictingLineageError(
                    f"Existing GenerationJob {existing_job.id} has provider_job_id {existing_job.provider_job_id} != {provider_job_id}"
                )
            if existing_job.output_asset_id != existing_asset.id:
                raise ViduConflictingLineageError(
                    f"Existing GenerationJob {existing_job.id} output_asset_id conflicts with Asset {existing_asset.id}"
                )
            if existing_asset.project_id != project_id:
                raise ViduConflictingLineageError(
                    f"Existing Asset {existing_asset.id} project_id {existing_asset.project_id} conflicts with expected {project_id}"
                )
            if existing_project and existing_scene and existing_scene.project_id != existing_project.id:
                raise ViduConflictingLineageError(
                    f"Existing Scene {existing_scene.id} project_id {existing_scene.project_id} != {existing_project.id}"
                )
            if existing_scene and existing_shot and existing_shot.scene_id != existing_scene.id:
                raise ViduConflictingLineageError(
                    f"Existing Shot {existing_shot.id} scene_id {existing_shot.scene_id} != {existing_scene.id}"
                )
            if existing_job.shot_id != shot_id:
                raise ViduConflictingLineageError(
                    f"Existing GenerationJob {existing_job.id} shot_id {existing_job.shot_id} != {shot_id}"
                )

            # 2. Repair non-conflicting incomplete fencing/audit state inside transaction
            needs_flush = False
            if not existing_job.imported_historical or not existing_job.execution_disabled:
                existing_job.imported_historical = True
                existing_job.execution_disabled = True
                needs_flush = True

            if existing_shot and existing_shot.source_asset_id != existing_asset.id:
                existing_shot.source_asset_id = existing_asset.id
                existing_shot.updated_at = _utc_now()
                needs_flush = True

            expected_result = {
                "provider_job_id": provider_job_id,
                "recovery_method": "GET_ONLY_EXISTING_JOB",
                "new_generation_posts": 0,
                "provider_status": job_result.status or "COMPLETED",
                "provider_credits_reported": job_result.provider_credits,
                "actual_credits_consumed": "UNKNOWN / NOT CONFIRMED",
                "usd_equivalent": "UNKNOWN / NOT CONVERTED",
                "imported_historical": True,
                "execution_disabled": True,
            }
            if existing_job.result != expected_result:
                existing_job.result = expected_result
                needs_flush = True

            if not existing_ledger:
                ledger_entry = UsageLedger(
                    id=ledger_id,
                    project_id=project_id,
                    shot_id=shot_id,
                    job_id=job_id,
                    provider="vidu",
                    operation="historical_recovery_get",
                    model="viduq2",
                    estimated_cost=None,
                    actual_cost=None,
                    currency="USD",
                    cost_status="UNKNOWN",
                    provider_event_id=provider_job_id,
                    idempotency_key=f"vidu-recovery-{provider_job_id}",
                    description="Historical VIDU2 recovery (GET-only existing job 995880130565918720; zero spend added)",
                    imported_historical=True,
                )
                db.add(ledger_entry)
                needs_flush = True
            elif existing_ledger.cost_status != "UNKNOWN" or not existing_ledger.imported_historical:
                existing_ledger.cost_status = "UNKNOWN"
                existing_ledger.imported_historical = True
                needs_flush = True

            if needs_flush:
                db.flush()
                if commit:
                    db.commit()

            logger.info("Provider job %s already durably materialized and verified", provider_job_id)
            return ViduRecoveryResult(
                provider_job_id=provider_job_id,
                status="COMPLETED",
                asset_id=existing_asset.id,
                generation_job_id=existing_job.id,
                shot_id=existing_job.shot_id,
                project_id=existing_asset.project_id,
                storage_bucket=existing_asset.storage_bucket,
                storage_key=existing_asset.storage_key,
                content_type=existing_asset.content_type,
                file_size_bytes=existing_asset.file_size_bytes,
                checksum_sha256=existing_asset.checksum_sha256,
                provider_credits_reported=job_result.provider_credits,
                posts_attempted=0,
                get_calls_attempted=1,
                imported_historical=True,
                execution_disabled=True,
                idempotent_reused=True,
            )

        # Step 4: Validate URL safety before touching DB or storage
        if not downloader:
            try:
                await VideoMaterializationService._validate_public_https_url(str(job_result.video_url))
            except Exception as exc:
                raise ViduRecoveryError(f"URL validation failed: {exc}") from exc

        # Step 5: Perform DB reconstruction inside nested transaction
        # If storage or commit fails, everything rolls back
        storage = storage_provider or get_storage_provider()
        fetch = downloader or VideoMaterializationService._download_video_to_file
        temp_path = None
        uploaded_bucket = None
        uploaded_key = None
        uploaded_new_object = False

        savepoint = db.begin_nested()
        try:
            project, scene, shot, job = cls.ensure_or_reconstruct_lineage(db, provider_job_id=provider_job_id)

            # Download & persist media
            with tempfile.NamedTemporaryFile(prefix=f"orbis_video_rec_{job.id}_", suffix=".media", delete=False) as tmp:
                temp_path = tmp.name

            content_type, size, checksum = await fetch(str(job_result.video_url), temp_path)
            if size <= 0 or not checksum:
                raise ViduRecoveryError("Downloaded provider output failed integrity checks")

            ext = VideoMaterializationService._extension(content_type)
            bucket = str(getattr(settings, "OBJECT_STORAGE_BUCKET", "") or "orbis-assets")
            storage_key = f"projects/{project.id}/generated-video/{job.id}/{checksum[:16]}.{ext}"
            storage.ensure_bucket_exists(bucket)
            existed = storage.object_exists(bucket, storage_key)
            if not existed:
                storage.upload_file_object(bucket, storage_key, temp_path, content_type)
                uploaded_new_object = True
            uploaded_bucket = bucket
            uploaded_key = storage_key

            # Construct Asset
            asset = Asset(
                id=asset_id,
                project_id=project.id,
                name=f"Recovered Historical Video Shot {shot.shot_number}",
                original_filename=f"recovered_shot_{shot.shot_number}.{ext}",
                asset_type="VIDEO",
                content_type=content_type,
                file_size_bytes=size,
                checksum_sha256=checksum,
                storage_bucket=bucket,
                storage_key=storage_key,
                created_at=_utc_now(),
                updated_at=_utc_now(),
            )
            db.add(asset)
            db.flush()

            job.output_asset_id = asset.id
            job.status = "COMPLETED"
            job.imported_historical = True
            job.execution_disabled = True
            job.result = {
                "provider_job_id": provider_job_id,
                "recovery_method": "GET_ONLY_EXISTING_JOB",
                "new_generation_posts": 0,
                "provider_status": job_result.status or "COMPLETED",
                "provider_credits_reported": job_result.provider_credits,
                "actual_credits_consumed": "UNKNOWN / NOT CONFIRMED",
                "usd_equivalent": "UNKNOWN / NOT CONVERTED",
                "imported_historical": True,
                "execution_disabled": True,
            }

            shot.source_asset_id = asset.id
            shot.updated_at = _utc_now()
            db.flush()

            # Record conservative UsageLedger audit entry (fenced historical, actual_cost=None)
            ledger_id = uuid.uuid5(uuid.NAMESPACE_URL, f"orbis://vidu-recovery/ledger/{provider_job_id}")
            if not db.get(UsageLedger, ledger_id):
                ledger_entry = UsageLedger(
                    id=ledger_id,
                    project_id=project.id,
                    shot_id=shot.id,
                    job_id=job.id,
                    provider="vidu",
                    operation="historical_recovery_get",
                    model="viduq2",
                    estimated_cost=None,
                    actual_cost=None,
                    currency="USD",
                    cost_status="UNKNOWN",
                    provider_event_id=provider_job_id,
                    idempotency_key=f"vidu-recovery-{provider_job_id}",
                    description="Historical VIDU2 recovery (GET-only existing job 995880130565918720; zero spend added)",
                    imported_historical=True,
                )
                db.add(ledger_entry)
                db.flush()

            savepoint.commit()
            if commit:
                db.commit()

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
                imported_historical=True,
                execution_disabled=True,
            )

        except Exception as exc:
            # 1. Safely rollback DB state (savepoint if still active, else db transaction)
            try:
                if savepoint.is_active:
                    savepoint.rollback()
                else:
                    db.rollback()
            except Exception as rb_err:
                logger.warning("DB rollback failed during recovery cleanup: %s", rb_err)

            # 2. Storage cleanup must execute even if savepoint/db rollback failed
            if uploaded_new_object and uploaded_bucket and uploaded_key:
                try:
                    storage.delete_object(uploaded_bucket, uploaded_key)
                except Exception as del_err:
                    logger.warning("Storage compensation failed for %s/%s: %s", uploaded_bucket, uploaded_key, del_err)

            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception:
                    pass

            # 3. Never mask the original failure
            if isinstance(exc, ViduRecoveryError):
                raise
            raise ViduRecoveryError(f"Video recovery failed: {exc}") from exc
        finally:
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception:
                    pass
