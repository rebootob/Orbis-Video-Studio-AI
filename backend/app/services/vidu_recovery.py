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
import hashlib
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


class ViduTransportCancellationFailureError(ViduRecoveryError):
    """Raised when transport-level cancellation fails to terminate the underlying worker operation."""
    pass


_SURVIVING_WORKERS = set()


def get_surviving_workers() -> list:
    """Return list of still-alive worker threads from un-terminated operations."""
    return [w for w in _SURVIVING_WORKERS if w.is_alive()]


def clear_surviving_workers() -> None:
    """Clear registered surviving workers (for test isolation)."""
    _SURVIVING_WORKERS.clear()


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
        auto_compensate_storage: bool = True,
        fence_id: Optional[uuid.UUID] = None,
        seed_historical_credits: bool = False,
    ) -> ViduRecoveryResult:
        """Query provider by GET only and materialize into durable Asset & Shot lineage.

        HARD INVARIANTS:
        - Only TARGET_HISTORICAL_PROVIDER_JOB_ID is accepted.
        - Zero POST requests / zero submit_generation_job calls.
        - Transaction atomicity: no ghost DB records on error; compensates newly created storage objects.
        - Transaction ownership:
            - When commit=True (default): executes nested savepoint, commits durable DB transaction upon success,
              and performs storage compensation + rollback on any commit failure.
            - When commit=False (caller-owned transaction): executes inside a savepoint, releases savepoint on success,
              and rolls back the savepoint while compensating newly uploaded storage objects on failure, leaving
              the caller's outer transaction uncorrupted.
        """
        # Step 1: Preflight ID bounding BEFORE any GET, DB, or storage calls
        cls.validate_authorized_job_id(provider_job_id)

        tx_state = "INITIAL"
        db_rolled_back = False
        unresolved_commit = False
        uploaded_new_object = False
        final_storage_bucket = None
        final_storage_key = None

        # Step 2: GET status from provider BEFORE committing or creating DB lineage
        try:
            vidu_adapter = adapter or ViduProviderAdapter()
            job_result: ProviderJobResult = await vidu_adapter.check_job_status(provider_job_id)

            # Validate returned provider_job_id if present
            if job_result.provider_job_id and job_result.provider_job_id != TARGET_HISTORICAL_PROVIDER_JOB_ID:
                raise ViduConflictingLineageError(
                    f"Provider returned mismatched provider_job_id '{job_result.provider_job_id}', "
                    f"expected '{TARGET_HISTORICAL_PROVIDER_JOB_ID}'"
                )

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
        except Exception as prov_err:
            try:
                from app.services.recovery_auth import RecoveryAuthService
                RecoveryAuthService.record_failure_audit(
                    db=db,
                    provider_job_id=provider_job_id,
                    failure_stage="PROVIDER_GET_OR_VALIDATION",
                    error_class=prov_err.__class__.__name__,
                    error_message=str(prov_err),
                    db_transaction_state="NOT_STARTED",
                    compensation_status="NOT_APPLICABLE",
                    fence_id=fence_id,
                )
            except Exception as audit_err:
                from app.services.recovery_auth import AuditWriteFailureError
                if isinstance(audit_err, AuditWriteFailureError):
                    raise
                raise AuditWriteFailureError(f"Failed to record failure audit: {audit_err}") from audit_err
            raise

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
            if existing_job.provider_name != "vidu":
                raise ViduConflictingLineageError(
                    f"Existing GenerationJob {existing_job.id} provider_name '{existing_job.provider_name}' != 'vidu'"
                )
            if existing_job.provider_job_id != provider_job_id:
                raise ViduConflictingLineageError(
                    f"Existing GenerationJob {existing_job.id} has provider_job_id {existing_job.provider_job_id} != {provider_job_id}"
                )
            if existing_job.job_type != "VIDEO":
                raise ViduConflictingLineageError(
                    f"Existing GenerationJob {existing_job.id} job_type '{existing_job.job_type}' != 'VIDEO'"
                )
            if existing_job.status != "COMPLETED":
                raise ViduConflictingLineageError(
                    f"Existing GenerationJob {existing_job.id} status '{existing_job.status}' != 'COMPLETED'"
                )
            if existing_job.shot_id != shot_id:
                raise ViduConflictingLineageError(
                    f"Existing GenerationJob {existing_job.id} shot_id {existing_job.shot_id} != {shot_id}"
                )
            if existing_job.output_asset_id != existing_asset.id:
                raise ViduConflictingLineageError(
                    f"Existing GenerationJob {existing_job.id} output_asset_id conflicts with Asset {existing_asset.id}"
                )

            # Asset validations
            if existing_asset.project_id != project_id:
                raise ViduConflictingLineageError(
                    f"Existing Asset {existing_asset.id} project_id {existing_asset.project_id} conflicts with expected {project_id}"
                )
            if existing_asset.asset_type != "VIDEO":
                raise ViduConflictingLineageError(
                    f"Existing Asset {existing_asset.id} asset_type '{existing_asset.asset_type}' != 'VIDEO'"
                )

            # Scene and Shot validations
            if existing_project and existing_scene and existing_scene.project_id != existing_project.id:
                raise ViduConflictingLineageError(
                    f"Existing Scene {existing_scene.id} project_id {existing_scene.project_id} != {existing_project.id}"
                )
            if existing_scene and existing_shot and existing_shot.scene_id != existing_scene.id:
                raise ViduConflictingLineageError(
                    f"Existing Shot {existing_shot.id} scene_id {existing_shot.scene_id} != {existing_scene.id}"
                )
            if existing_shot and existing_shot.source_asset_id is not None and existing_shot.source_asset_id != existing_asset.id:
                raise ViduConflictingLineageError(
                    f"Existing Shot {existing_shot.id} source_asset_id {existing_shot.source_asset_id} conflicts with Asset {existing_asset.id}"
                )

            if not existing_job.imported_historical:
                raise ViduConflictingLineageError(
                    f"Existing GenerationJob {existing_job.id} has conflicting imported_historical={existing_job.imported_historical}, expected True"
                )
            if not existing_job.execution_disabled:
                raise ViduConflictingLineageError(
                    f"Existing GenerationJob {existing_job.id} has conflicting execution_disabled={existing_job.execution_disabled}, expected True"
                )

            # UsageLedger validations (if present, fail closed on conflicting fields)
            if existing_ledger:
                if existing_ledger.project_id != project_id:
                    raise ViduConflictingLineageError(
                        f"Existing UsageLedger {existing_ledger.id} project_id {existing_ledger.project_id} != {project_id}"
                    )
                if existing_ledger.shot_id != shot_id:
                    raise ViduConflictingLineageError(
                        f"Existing UsageLedger {existing_ledger.id} shot_id {existing_ledger.shot_id} != {shot_id}"
                    )
                if existing_ledger.job_id != job_id:
                    raise ViduConflictingLineageError(
                        f"Existing UsageLedger {existing_ledger.id} job_id {existing_ledger.job_id} != {job_id}"
                    )
                if existing_ledger.provider != "vidu":
                    raise ViduConflictingLineageError(
                        f"Existing UsageLedger {existing_ledger.id} provider '{existing_ledger.provider}' != 'vidu'"
                    )
                if existing_ledger.operation != "historical_recovery_get":
                    raise ViduConflictingLineageError(
                        f"Existing UsageLedger {existing_ledger.id} operation '{existing_ledger.operation}' != 'historical_recovery_get'"
                    )
                if existing_ledger.provider_event_id != provider_job_id:
                    raise ViduConflictingLineageError(
                        f"Existing UsageLedger {existing_ledger.id} provider_event_id '{existing_ledger.provider_event_id}' != '{provider_job_id}'"
                    )
                if existing_ledger.idempotency_key != f"vidu-recovery-{provider_job_id}":
                    raise ViduConflictingLineageError(
                        f"Existing UsageLedger {existing_ledger.id} idempotency_key '{existing_ledger.idempotency_key}' != 'vidu-recovery-{provider_job_id}'"
                    )
                if existing_ledger.cost_status != "UNKNOWN":
                    raise ViduConflictingLineageError(
                        f"Existing UsageLedger {existing_ledger.id} has conflicting cost_status '{existing_ledger.cost_status}', expected 'UNKNOWN'"
                    )
                if not existing_ledger.imported_historical:
                    raise ViduConflictingLineageError(
                        f"Existing UsageLedger {existing_ledger.id} has conflicting imported_historical={existing_ledger.imported_historical}, expected True"
                    )
                if existing_ledger.actual_cost is not None:
                    raise ViduConflictingLineageError(
                        f"Existing UsageLedger {existing_ledger.id} has conflicting non-null actual_cost: {existing_ledger.actual_cost}"
                    )
                if existing_ledger.estimated_cost is not None:
                    raise ViduConflictingLineageError(
                        f"Existing UsageLedger {existing_ledger.id} has conflicting non-null estimated_cost: {existing_ledger.estimated_cost}"
                    )

            # 2. Reconcile provider credits reported:
            # If current GET reports credits, use them.
            # If current GET omits credits but prior evidence retained credits, preserve retained credits.
            prior_credits = None
            if existing_job.result and isinstance(existing_job.result, dict):
                prior_credits = existing_job.result.get("provider_credits_reported")
            if job_result.provider_credits is not None and prior_credits is not None and prior_credits != job_result.provider_credits:
                raise ViduConflictingLineageError(
                    f"Existing GenerationJob.result provider_credits_reported {prior_credits} conflicts with provider {job_result.provider_credits}"
                )
            effective_credits = job_result.provider_credits if job_result.provider_credits is not None else prior_credits

            # 3. Validate GenerationJob.result strictly against invariants:
            expected_result_invariants = {
                "provider_job_id": provider_job_id,
                "recovery_method": "GET_ONLY_EXISTING_JOB",
                "new_generation_posts": 0,
                "provider_status": job_result.status or "COMPLETED",
                "actual_credits_consumed": "UNKNOWN / NOT CONFIRMED",
                "usd_equivalent": "UNKNOWN / NOT CONVERTED",
                "imported_historical": True,
                "execution_disabled": True,
            }

            needs_flush = False
            if existing_job.result is not None:
                if not isinstance(existing_job.result, dict):
                    raise ViduConflictingLineageError("Existing GenerationJob.result is not a dictionary")
                for k, expected_v in expected_result_invariants.items():
                    if k in existing_job.result and existing_job.result[k] != expected_v:
                        raise ViduConflictingLineageError(
                            f"Existing GenerationJob.result has conflicting {k}: '{existing_job.result[k]}' != '{expected_v}'"
                        )
                # Fill only genuinely missing, non-conflicting fields, preserving compatible additional evidence
                repaired_result = dict(existing_job.result)
                missing_filled = False
                for k, expected_v in expected_result_invariants.items():
                    if k not in repaired_result:
                        repaired_result[k] = expected_v
                        missing_filled = True
                if "provider_credits_reported" not in repaired_result:
                    repaired_result["provider_credits_reported"] = effective_credits
                    missing_filled = True
                elif effective_credits is not None and repaired_result.get("provider_credits_reported") is None:
                    repaired_result["provider_credits_reported"] = effective_credits
                    missing_filled = True

                if missing_filled:
                    existing_job.result = repaired_result
                    needs_flush = True
            else:
                existing_job.result = dict(expected_result_invariants)
                existing_job.result["provider_credits_reported"] = effective_credits
                needs_flush = True

            if existing_shot and existing_shot.source_asset_id is None:
                existing_shot.source_asset_id = existing_asset.id
                existing_shot.updated_at = _utc_now()
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
                provider_credits_reported=effective_credits,
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
        result_payload = None

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

            if job_result.provider_credits is not None:
                effective_credits = job_result.provider_credits
                credits_provenance = "PROVIDER_GET_REPORTED"
            elif seed_historical_credits:
                effective_credits = 30.0
                credits_provenance = "SEEDED_HISTORICAL_CONTRACT_METADATA"
            else:
                effective_credits = None
                credits_provenance = "UNREPORTED"

            job.output_asset_id = asset.id
            job.status = "COMPLETED"
            job.imported_historical = True
            job.execution_disabled = True
            job.result = {
                "provider_job_id": provider_job_id,
                "recovery_method": "GET_ONLY_EXISTING_JOB",
                "new_generation_posts": 0,
                "provider_status": job_result.status or "COMPLETED",
                "provider_credits_reported": effective_credits,
                "credits_provenance": credits_provenance,
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

            # Capture/build immutable result data BEFORE committing where safe
            result_payload = ViduRecoveryResult(
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
                provider_credits_reported=effective_credits,
                posts_attempted=0,
                get_calls_attempted=1,
                imported_historical=True,
                execution_disabled=True,
            )

            savepoint.commit()
            if commit:
                tx_state = "COMMITTING"
                db.commit()
                tx_state = "COMMITTED"

        except Exception as exc:
            # If an exception occurred while committing, outcome is authoritatively unknown (ambiguous)
            unresolved_commit = (tx_state == "COMMITTING")
            db_rolled_back = False

            # Safely rollback DB state
            try:
                if savepoint.is_active:
                    savepoint.rollback()
                db.rollback()
                db_rolled_back = True
                tx_state = "AMBIGUOUS_COMMIT" if unresolved_commit else "ROLLED_BACK"
            except Exception as rb_err:
                db_rolled_back = False
                unresolved_commit = True
                tx_state = "ROLLBACK_FAILED"
                logger.warning("DB rollback failed during recovery cleanup: %s", rb_err)

            # Storage cleanup executes ONLY if affirmative guards pass
            comp_status = "NOT_APPLICABLE"
            if auto_compensate_storage and uploaded_new_object and uploaded_bucket and uploaded_key:
                safe_to_delete = cls.check_storage_compensation_guards(
                    db=db,
                    bucket=uploaded_bucket,
                    key=uploaded_key,
                    is_new_object="TRUE" if uploaded_new_object else "UNKNOWN",
                    db_rolled_back=db_rolled_back,
                    unresolved_commit=unresolved_commit,
                )
                if safe_to_delete:
                    try:
                        storage.delete_object(uploaded_bucket, uploaded_key)
                        comp_status = "COMPENSATED_DELETED"
                    except Exception as del_err:
                        logger.warning("Storage compensation failed for %s/%s: %s", uploaded_bucket, uploaded_key, del_err)
                        comp_status = "COMPENSATION_DELETE_FAILED"
                else:
                    logger.warning("Storage compensation skipped (universal guards not satisfied); retaining %s/%s", uploaded_bucket, uploaded_key)
                    comp_status = "RETAINED_OBJECT_UNSAFE_TO_DELETE"

            try:
                from app.services.recovery_auth import RecoveryAuthService
                RecoveryAuthService.record_failure_audit(
                    db=db,
                    provider_job_id=provider_job_id,
                    failure_stage="STORAGE_OR_DB_MATERIALIZATION",
                    error_class=exc.__class__.__name__,
                    error_message=str(exc),
                    db_transaction_state=tx_state,
                    compensation_status=comp_status,
                    fence_id=fence_id,
                    orphan_bucket=uploaded_bucket if uploaded_new_object else None,
                    orphan_key=uploaded_key if uploaded_new_object else None,
                )
            except Exception as audit_err:
                from app.services.recovery_auth import AuditWriteFailureError
                if isinstance(audit_err, AuditWriteFailureError):
                    raise
                raise AuditWriteFailureError(f"Failed to record failure audit in exception handler: {audit_err}") from audit_err

            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception:
                    pass

            # Never mask the original failure
            if isinstance(exc, ViduRecoveryError):
                raise
            raise ViduRecoveryError(f"Video recovery failed: {exc}") from exc
        finally:
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception:
                    pass

        return result_payload

    @classmethod
    def check_storage_compensation_guards(
        cls,
        db: Session,
        bucket: str,
        key: str,
        is_new_object: str,
        db_rolled_back: bool,
        unresolved_commit: bool,
    ) -> bool:
        """Universal storage compensation guard.

        Returns True ONLY if ALL criteria are affirmatively proven:
        1. Ownership: is_new_object == 'TRUE'
        2. Affirmative DB rollback proven (db_rolled_back == True)
        3. Zero committed Asset records reference (bucket, key) via independent fresh query
        4. No unresolved commit (unresolved_commit == False)
        If ambiguous/unknown/failed read: returns False (retain object).
        """
        if is_new_object != "TRUE":
            return False
        if not db_rolled_back:
            return False
        if unresolved_commit:
            return False

        # Independent fresh authoritative read to avoid identity-map cache
        try:
            from sqlalchemy.orm import sessionmaker
            engine = db.get_bind()
            fresh_session_factory = sessionmaker(bind=engine, expire_on_commit=False)
            with fresh_session_factory() as fresh_db:
                ref_count = fresh_db.query(Asset).filter(
                    Asset.storage_bucket == bucket,
                    Asset.storage_key == key,
                ).count()
                if ref_count > 0:
                    return False
        except Exception as read_err:
            logger.warning("Independent DB read failed in compensation guard: %s", read_err)
            return False
        return True

    @classmethod
    def stream_verify_storage_object(
        cls,
        storage: ObjectStorageProvider,
        bucket: str,
        key: str,
        expected_size: int,
        expected_sha256: str,
        max_size_bytes: int = 50 * 1024 * 1024,
        max_duration_seconds: float = 30.0,
    ) -> None:
        """Bounded streaming verification of storage object without unbounded download or full payload in RAM.

        Enforces:
        1. Fail-closed metadata check: metadata failures immediately raise ViduRecoveryError.
        2. Bounded response streaming: byte bounds and timeouts enforced during chunk streaming.
        3. Object-version consistency: validates that object size and ETag have not mutated between HEAD and GET.
        4. Incremental 64KB hashing directly from network/storage stream.
        """
        import socket
        import threading
        import time

        def _abort_stream(body_obj):
            """Abort underlying transport socket and close stream to cancel any in-flight read."""
            sock = None
            if hasattr(body_obj, "_raw_stream") and hasattr(body_obj._raw_stream, "sock"):
                sock = body_obj._raw_stream.sock
            elif hasattr(body_obj, "_sock"):
                sock = body_obj._sock
            elif hasattr(body_obj, "sock"):
                sock = body_obj.sock
            if sock is not None:
                try:
                    if hasattr(sock, "shutdown") and hasattr(socket, "SHUT_RDWR"):
                        sock.shutdown(socket.SHUT_RDWR)
                except Exception:
                    pass
                try:
                    sock.close()
                except Exception:
                    pass
            if hasattr(body_obj, "close"):
                try:
                    body_obj.close()
                except Exception:
                    pass

        def _execute_with_transport_cancellation(func, timeout_seconds: float, desc: str, abort_action=None):
            """Execute a network/storage operation with strict transport deadline and cancellation.

            Guarantees:
            1. Execution is bounded by timeout_seconds.
            2. On timeout, triggers abort_action() to terminate the underlying transport socket/connection.
            3. Authoritatively confirms worker thread termination; if surviving workers exist or cannot be terminated,
               fails closed without claiming zero surviving operations and halts to prevent unbounded daemon accumulation.
            4. Fails closed with ViduRecoveryError or ViduTransportCancellationFailureError.
            """
            surviving_active = [w for w in _SURVIVING_WORKERS if w.is_alive()]
            if surviving_active:
                raise ViduTransportCancellationFailureError(
                    f"Transport execution rejected: {len(surviving_active)} un-terminated worker(s) still active; "
                    "unbounded daemon accumulation prevented (fail-closed)"
                )

            result = [None]
            exc = [None]
            done = threading.Event()

            def worker():
                try:
                    result[0] = func()
                except Exception as e:
                    exc[0] = e
                finally:
                    done.set()

            t = threading.Thread(target=worker, daemon=True)
            t.start()

            if not done.wait(timeout_seconds):
                if abort_action:
                    try:
                        abort_action()
                    except Exception:
                        pass
                t.join(timeout=0.3)
                if t.is_alive():
                    _SURVIVING_WORKERS.add(t)
                    logger.error("Transport cancellation failed to terminate worker for %s (surviving thread detected)", desc)
                    raise ViduTransportCancellationFailureError(
                        f"{desc} timed out after {timeout_seconds}s and transport cancellation could not verify worker termination "
                        "(surviving worker detected; fail-closed without claiming zero surviving work)"
                    )
                raise ViduRecoveryError(
                    f"{desc} timed out after {timeout_seconds}s (transport deadline enforced and underlying worker terminated)"
                )

            if exc[0]:
                raise exc[0]
            return result[0]

        def _read_chunk_with_transport_cancellation(body_stream, chunk_sz: int, timeout_sec: float) -> bytes:
            """Read a single chunk with socket-level timeout configuration, bounded by transport deadline."""
            raw_sock = None
            orig_timeout = None
            if hasattr(body_stream, "_raw_stream") and hasattr(body_stream._raw_stream, "sock") and body_stream._raw_stream.sock:
                raw_sock = body_stream._raw_stream.sock
            elif hasattr(body_stream, "_sock") and body_stream._sock:
                raw_sock = body_stream._sock
            elif hasattr(body_stream, "sock") and body_stream.sock:
                raw_sock = body_stream.sock

            if raw_sock and hasattr(raw_sock, "gettimeout") and hasattr(raw_sock, "settimeout"):
                try:
                    orig_timeout = raw_sock.gettimeout()
                    raw_sock.settimeout(timeout_sec)
                except Exception:
                    pass

            def _abort():
                _abort_stream(body_stream)

            def _read_direct():
                t_chunk_start = time.monotonic()
                try:
                    data = body_stream.read(chunk_sz)
                    if time.monotonic() - t_chunk_start > timeout_sec:
                        raise ViduRecoveryError(
                            f"Storage stream read blocked and timed out after {timeout_sec}s (transport deadline enforced)"
                        )
                    return data
                except Exception as read_ex:
                    _abort()
                    if isinstance(read_ex, ViduRecoveryError):
                        raise
                    if "timed out" in str(read_ex).lower() or isinstance(read_ex, (TimeoutError, socket.timeout)):
                        raise ViduRecoveryError(
                            f"Storage stream read blocked and timed out after {timeout_sec}s (transport deadline enforced)"
                        ) from read_ex
                    raise

            try:
                return _execute_with_transport_cancellation(
                    _read_direct,
                    timeout_seconds=timeout_sec,
                    desc=f"Storage stream chunk read ({chunk_sz} bytes)",
                    abort_action=_abort,
                )
            finally:
                if raw_sock and orig_timeout is not None and hasattr(raw_sock, "settimeout"):
                    try:
                        raw_sock.settimeout(orig_timeout)
                    except Exception:
                        pass

        # 1. Pre-transfer metadata check (fail-closed on any error)
        head_len = None
        head_etag = None

        if hasattr(storage, "client") and hasattr(storage.client, "head_object"):
            def _call_head():
                return storage.client.head_object(Bucket=bucket, Key=key)

            def _abort_head():
                if hasattr(storage.client, "close"):
                    try:
                        storage.client.close()
                    except Exception:
                        pass

            try:
                head = _execute_with_transport_cancellation(
                    _call_head,
                    timeout_seconds=5.0,
                    desc=f"Storage metadata access for '{bucket}/{key}'",
                    abort_action=_abort_head,
                )
                head_len = head.get("ContentLength")
                head_etag = head.get("ETag")
            except Exception as h_err:
                if isinstance(h_err, ViduRecoveryError):
                    raise
                raise ViduRecoveryError(f"Storage metadata access failed for '{bucket}/{key}': {h_err}") from h_err

            if head_len is None:
                raise ViduRecoveryError(f"Storage metadata missing ContentLength for '{bucket}/{key}'")
            if head_len > max_size_bytes:
                raise ViduRecoveryError(f"Storage object exceeds maximum allowed size ({head_len} > {max_size_bytes})")
            if head_len != expected_size:
                raise ViduRecoveryError(f"Storage size mismatch: head ContentLength {head_len} != expected {expected_size}")

        elif hasattr(storage, "_store"):
            item = storage._store.get((bucket, key))
            if not item:
                raise KeyError(f"Object '{key}' not found in bucket '{bucket}'")
            raw_len = len(item[0]) if isinstance(item[0], (bytes, bytearray)) else 0
            head_len = raw_len
            if raw_len > max_size_bytes:
                raise ViduRecoveryError(f"Storage object exceeds maximum allowed size ({raw_len} > {max_size_bytes})")
            if raw_len != expected_size:
                raise ViduRecoveryError(f"Storage size mismatch: actual {raw_len} != expected {expected_size}")
        else:
            raise ViduRecoveryError(f"Storage provider does not support metadata inspection for '{bucket}/{key}'")

        # 2. Response streaming with in-flight byte and time bounding
        hasher = hashlib.sha256()
        bytes_transferred = 0
        start_time = time.monotonic()

        if hasattr(storage, "client") and hasattr(storage.client, "get_object"):
            def _call_get():
                return storage.client.get_object(Bucket=bucket, Key=key)

            def _abort_get():
                if hasattr(storage.client, "close"):
                    try:
                        storage.client.close()
                    except Exception:
                        pass

            try:
                response = _execute_with_transport_cancellation(
                    _call_get,
                    timeout_seconds=min(max_duration_seconds, 10.0),
                    desc=f"Storage stream retrieval for '{bucket}/{key}'",
                    abort_action=_abort_get,
                )
            except Exception as get_err:
                if isinstance(get_err, ViduRecoveryError):
                    raise
                raise ViduRecoveryError(f"Failed to initiate stream retrieval for '{bucket}/{key}': {get_err}") from get_err

            body = response.get("Body") if isinstance(response, dict) else getattr(response, "Body", None)
            try:
                # Version consistency check against initial HEAD (Guaranteed body cleanup on mismatch)
                curr_etag = response.get("ETag") if isinstance(response, dict) else getattr(response, "ETag", None)
                curr_len = response.get("ContentLength") if isinstance(response, dict) else getattr(response, "ContentLength", None)
                if head_etag is not None and curr_etag != head_etag:
                    raise ViduRecoveryError(
                        f"Storage object modified between HEAD and stream retrieval (ETag mismatch: '{curr_etag}' != '{head_etag}')"
                    )
                if head_len is not None and curr_len != head_len:
                    raise ViduRecoveryError(
                        f"Storage object modified between HEAD and stream retrieval (Length mismatch: {curr_len} != {head_len})"
                    )

                if body is None:
                    raise ViduRecoveryError(f"Storage get_object response missing Body stream for '{bucket}/{key}'")

                chunk_size = 64 * 1024
                deadline = start_time + max_duration_seconds

                while True:
                    remaining_time = deadline - time.monotonic()
                    if remaining_time <= 0:
                        raise ViduRecoveryError(f"Storage stream transfer exceeded timeout of {max_duration_seconds}s")

                    chunk_timeout = min(remaining_time, 10.0)
                    try:
                        chunk = _read_chunk_with_transport_cancellation(body, chunk_size, chunk_timeout)
                    except Exception as read_err:
                        if hasattr(body, "close"):
                            try:
                                body.close()
                            except Exception:
                                pass
                        if isinstance(read_err, ViduRecoveryError):
                            raise
                        raise ViduRecoveryError(f"Storage stream read failure: {read_err}") from read_err

                    # Verify deadline again after read completes (prevents slow EOF / blocking read overrun)
                    if time.monotonic() > deadline:
                        raise ViduRecoveryError(f"Storage stream transfer exceeded timeout of {max_duration_seconds}s")

                    if not chunk:
                        break

                    bytes_transferred += len(chunk)
                    if bytes_transferred > max_size_bytes:
                        raise ViduRecoveryError(
                            f"Storage stream transfer exceeded maximum budget of {max_size_bytes} bytes during response streaming"
                        )
                    hasher.update(chunk)
            finally:
                if hasattr(body, "close"):
                    try:
                        body.close()
                    except Exception:
                        pass

        elif hasattr(storage, "_store"):
            item_now = storage._store.get((bucket, key))
            if not item_now:
                raise KeyError(f"Object '{key}' disappeared during stream verification")
            raw_now = item_now[0] if isinstance(item_now, tuple) else item_now
            curr_len = len(raw_now) if isinstance(raw_now, (bytes, bytearray)) else 0
            if curr_len != head_len:
                raise ViduRecoveryError(
                    f"Storage object modified between HEAD and stream retrieval (Length mismatch: {curr_len} != {head_len})"
                )

            chunk_size = 64 * 1024
            offset = 0
            while offset < len(raw_now):
                if time.monotonic() - start_time > max_duration_seconds:
                    raise ViduRecoveryError(f"Storage stream transfer exceeded timeout of {max_duration_seconds}s")
                chunk = raw_now[offset : offset + chunk_size]
                offset += len(chunk)
                bytes_transferred += len(chunk)
                if bytes_transferred > max_size_bytes:
                    raise ViduRecoveryError(
                        f"Storage stream transfer exceeded maximum budget of {max_size_bytes} bytes during response streaming"
                    )
                hasher.update(chunk)

        # 3. Final integrity validation
        if bytes_transferred != expected_size:
            raise ViduRecoveryError(f"Storage size mismatch: transferred {bytes_transferred} != expected {expected_size}")

        calc_sha256 = hasher.hexdigest()
        if calc_sha256 != expected_sha256:
            raise ViduRecoveryError(
                f"Storage checksum mismatch: actual {calc_sha256} != expected {expected_sha256}"
            )

    @classmethod
    def reconcile_offline_historical_job(
        cls,
        db: Session,
        *,
        storage_provider: Optional[ObjectStorageProvider] = None,
        provider_job_id: str = TARGET_HISTORICAL_PROVIDER_JOB_ID,
    ) -> ViduRecoveryResult:
        """Dedicated offline reconciliation entrypoint.

        Strict invariants:
        - ZERO PROVIDER STATUS GET / ZERO GENERATION POST.
        - Bounded read-only I/O against database and private storage.
        - Verifies durable historical result:
          GenerationJob.imported_historical = True, GenerationJob.execution_disabled = True
          UsageLedger.imported_historical = True
          Deterministic UUIDs and lineage (Project, Scene, Shot, Asset, GenerationJob, UsageLedger)
          Storage object exists, file size matches, streaming SHA-256 matches Asset.checksum_sha256
        - If any data is missing, conflicting, or corrupted, or if DB/storage is unavailable:
          STOPS immediately. NEVER falls through to GET-first recover_existing_job().
        """
        import hashlib

        # 1. Preflight bounding
        cls.validate_authorized_job_id(provider_job_id)

        # 2. Compute deterministic lineage IDs
        job_id = uuid.uuid5(uuid.NAMESPACE_URL, f"orbis://vidu-recovery/job/{provider_job_id}")
        asset_id = uuid.uuid5(uuid.NAMESPACE_URL, f"orbis://video-generation/{job_id}")
        project_id = uuid.uuid5(uuid.NAMESPACE_URL, f"orbis://vidu-recovery/project/{provider_job_id}")
        scene_id = uuid.uuid5(uuid.NAMESPACE_URL, f"orbis://vidu-recovery/scene/{provider_job_id}/1")
        shot_id = uuid.uuid5(uuid.NAMESPACE_URL, f"orbis://vidu-recovery/shot/{provider_job_id}/1")
        ledger_id = uuid.uuid5(uuid.NAMESPACE_URL, f"orbis://vidu-recovery/ledger/{provider_job_id}")

        # 3. Query existing primary DB entities
        try:
            asset = db.get(Asset, asset_id)
            job = db.get(GenerationJob, job_id)
            project = db.get(Project, project_id)
            scene = db.get(Scene, scene_id)
            shot = db.get(Shot, shot_id)
            ledger = db.get(UsageLedger, ledger_id)
        except Exception as db_err:
            raise ViduRecoveryError(f"Offline reconciliation DB query failed: {db_err}") from db_err

        # 4. Require complete lineage including UsageLedger
        if not asset or not job or not project or not scene or not shot or not ledger:
            raise ViduRecoveryError(
                f"Offline reconciliation failed: incomplete lineage for historical job {provider_job_id} "
                f"(asset={bool(asset)}, job={bool(job)}, project={bool(project)}, "
                f"scene={bool(scene)}, shot={bool(shot)}, ledger={bool(ledger)})"
            )

        # 5. Verify lineage integrity & historical flags
        if job.provider_name != "vidu":
            raise ViduConflictingLineageError(f"Job provider_name '{job.provider_name}' != 'vidu'")
        if job.provider_job_id != provider_job_id:
            raise ViduConflictingLineageError(f"Job provider_job_id '{job.provider_job_id}' != '{provider_job_id}'")
        if job.job_type != "VIDEO":
            raise ViduConflictingLineageError(f"Job job_type '{job.job_type}' != 'VIDEO'")
        if job.status != "COMPLETED":
            raise ViduConflictingLineageError(f"Job status '{job.status}' != 'COMPLETED'")
        if job.shot_id != shot_id:
            raise ViduConflictingLineageError(f"Job shot_id '{job.shot_id}' != '{shot_id}'")
        if job.output_asset_id != asset.id:
            raise ViduConflictingLineageError(f"Job output_asset_id '{job.output_asset_id}' != '{asset.id}'")
        if not job.imported_historical:
            raise ViduConflictingLineageError(f"Job imported_historical is not True")
        if not job.execution_disabled:
            raise ViduConflictingLineageError(f"Job execution_disabled is not True")

        # Full GenerationJob.result validation
        if not isinstance(job.result, dict):
            raise ViduRecoveryError("Offline reconciliation failed: job.result is missing or not a dictionary")
        if job.result.get("recovery_method") != "GET_ONLY_EXISTING_JOB":
            raise ViduRecoveryError("Offline reconciliation failed: job.result.recovery_method != 'GET_ONLY_EXISTING_JOB'")
        if job.result.get("provider_job_id") != provider_job_id:
            raise ViduConflictingLineageError(f"Offline reconciliation failed: job.result.provider_job_id '{job.result.get('provider_job_id')}' != '{provider_job_id}'")
        if job.result.get("new_generation_posts") != 0:
            raise ViduConflictingLineageError(f"Offline reconciliation failed: job.result.new_generation_posts '{job.result.get('new_generation_posts')}' != 0")
        if job.result.get("provider_status") != "COMPLETED":
            raise ViduConflictingLineageError(f"Offline reconciliation failed: job.result.provider_status '{job.result.get('provider_status')}' != 'COMPLETED'")
        if job.result.get("actual_credits_consumed") != "UNKNOWN / NOT CONFIRMED":
            raise ViduConflictingLineageError("Offline reconciliation failed: job.result.actual_credits_consumed != 'UNKNOWN / NOT CONFIRMED'")
        if job.result.get("usd_equivalent") != "UNKNOWN / NOT CONVERTED":
            raise ViduConflictingLineageError("Offline reconciliation failed: job.result.usd_equivalent != 'UNKNOWN / NOT CONVERTED'")
        if job.result.get("imported_historical") is not True:
            raise ViduConflictingLineageError("Offline reconciliation failed: job.result.imported_historical is not True")
        if job.result.get("execution_disabled") is not True:
            raise ViduConflictingLineageError("Offline reconciliation failed: job.result.execution_disabled is not True")
        if job.result.get("provider_credits_reported") is None:
            raise ViduRecoveryError("Offline reconciliation failed: job.result missing required provider_credits_reported")

        if asset.project_id != project_id:
            raise ViduConflictingLineageError(f"Asset project_id '{asset.project_id}' != '{project_id}'")
        if asset.asset_type != "VIDEO":
            raise ViduConflictingLineageError(f"Asset asset_type '{asset.asset_type}' != 'VIDEO'")

        if scene.project_id != project_id:
            raise ViduConflictingLineageError(f"Scene project_id '{scene.project_id}' != '{project_id}'")
        if shot.scene_id != scene_id:
            raise ViduConflictingLineageError(f"Shot scene_id '{shot.scene_id}' != '{scene_id}'")

        if not ledger.imported_historical:
            raise ViduConflictingLineageError(f"Ledger imported_historical is not True")
        if ledger.cost_status != "UNKNOWN":
            raise ViduConflictingLineageError(f"Ledger cost_status '{ledger.cost_status}' must be strictly 'UNKNOWN' for conservative recovery truth")
        if ledger.actual_cost is not None:
            raise ViduConflictingLineageError(f"Ledger actual_cost '{ledger.actual_cost}' must be None for historical recovery")
        if ledger.estimated_cost is not None:
            raise ViduConflictingLineageError(f"Ledger estimated_cost '{ledger.estimated_cost}' must be None for historical recovery")
        if ledger.job_id != job.id:
            raise ViduConflictingLineageError(f"Ledger job_id '{ledger.job_id}' != '{job.id}'")
        if ledger.project_id != project.id:
            raise ViduConflictingLineageError(f"Ledger project_id '{ledger.project_id}' != '{project.id}'")
        if ledger.shot_id != shot.id:
            raise ViduConflictingLineageError(f"Ledger shot_id '{ledger.shot_id}' != '{shot.id}'")

        # 6. Verify storage object presence and bounded streaming checksum
        storage = storage_provider or get_storage_provider()
        try:
            exists = storage.object_exists(asset.storage_bucket, asset.storage_key)
        except Exception as st_err:
            raise ViduRecoveryError(f"Offline reconciliation storage access failed: {st_err}") from st_err

        if not exists:
            raise ViduRecoveryError(
                f"Offline reconciliation failed: storage object {asset.storage_bucket}/{asset.storage_key} does not exist"
            )

        # Bounded streaming read-back: chunks up to 50MB max without loading full payload to RAM
        cls.stream_verify_storage_object(
            storage=storage,
            bucket=asset.storage_bucket,
            key=asset.storage_key,
            expected_size=asset.file_size_bytes,
            expected_sha256=asset.checksum_sha256,
            max_size_bytes=50 * 1024 * 1024,
        )

        reported_credits = float(job.result["provider_credits_reported"])

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
            provider_credits_reported=reported_credits,
            actual_credits_consumed="UNKNOWN / NOT CONFIRMED",
            usd_equivalent="UNKNOWN / NOT CONVERTED",
            posts_attempted=0,
            get_calls_attempted=0,  # Strictly ZERO provider GET
            imported_historical=True,
            execution_disabled=True,
            idempotent_reused=True,
        )
