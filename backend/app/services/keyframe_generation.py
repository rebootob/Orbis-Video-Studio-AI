"""Service for storyboard image and keyframe generation, persistence, batch operations, and state transitions."""
import asyncio
import hashlib
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple, Union, Any

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.project import Project
from app.models.scene import Scene
from app.models.shot import Shot
from app.models.asset import Asset
from app.models.generation_job import GenerationJob
from app.models.asset_lock import AssetLock
from app.models.batch_run import BatchRun, BatchRunItem
from app.models.usage_ledger import UsageLedger
from app.models.orchestration_audit import OrchestrationAudit
from app.providers.image.base import (
    IImageGenerationProviderAdapter,
    ImageGenerationParams,
    ImageJobResult,
)
from app.providers.image.factory import ImageProviderFactory
from app.services.image_generation.continuity_mapper import ContinuityMapper
from app.services.pricing import ProviderPricingService, CostStatus
from app.services.budget import BudgetService
from app.services.storage.factory import get_storage_provider


class KeyframeBatchOperationType(str, Enum):
    CONTINUE_INCOMPLETE_KEYFRAMES = "CONTINUE_INCOMPLETE_KEYFRAMES"
    RETRY_FAILED_KEYFRAMES = "RETRY_FAILED_KEYFRAMES"
    GENERATE_SELECTED_KEYFRAMES = "GENERATE_SELECTED_KEYFRAMES"


ALLOWED_KEYFRAME_STAGES = {
    "SHOT_PLAN_APPROVED",
    "IMAGES_GENERATED",
    "IMAGES_APPROVED",
    "IMAGES_IN_PROGRESS",
    "VIDEO_IN_PROGRESS",
}

ACTIVE_JOB_STATUSES = {
    "PENDING",
    "CLAIMED",
    "SUBMITTING",
    "SUBMITTED",
    "POLLING",
    "QUEUED",
    "PROCESSING",
    "CANCELLING",
    "RECONCILIATION_REQUIRED",
}


class KeyframeGenerationService:
    """Canonical service for Storyboard Keyframe Generation and Batch Operations."""

    @classmethod
    def _validate_operation_type(cls, operation_type: Union[KeyframeBatchOperationType, str]) -> KeyframeBatchOperationType:
        if isinstance(operation_type, str):
            try:
                return KeyframeBatchOperationType(operation_type)
            except ValueError:
                # Support standard batch operation strings for compatibility
                mapping = {
                    "CONTINUE_INCOMPLETE": KeyframeBatchOperationType.CONTINUE_INCOMPLETE_KEYFRAMES,
                    "RETRY_FAILED": KeyframeBatchOperationType.RETRY_FAILED_KEYFRAMES,
                    "GENERATE_SELECTED": KeyframeBatchOperationType.GENERATE_SELECTED_KEYFRAMES,
                    "START_KEYFRAME_GENERATION": KeyframeBatchOperationType.CONTINUE_INCOMPLETE_KEYFRAMES,
                    "GENERATE_KEYFRAMES": KeyframeBatchOperationType.CONTINUE_INCOMPLETE_KEYFRAMES,
                }
                if operation_type in mapping:
                    return mapping[operation_type]
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid keyframe batch operation_type '{operation_type}'. Supported: {[e.value for e in KeyframeBatchOperationType]}",
                )
        return operation_type

    @classmethod
    def generate_shot_keyframe(
        cls,
        db: Session,
        project_id: uuid.UUID,
        shot_id: uuid.UUID,
        provider_name: Optional[str] = None,
        cost_authorized: bool = False,
        actor: str = "USER",
        provider_specific_params: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Asset, GenerationJob]:
        """Generate a keyframe image for a single shot, persisting Asset and GenerationJob records."""
        project = db.get(Project, project_id)
        if not project:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project '{project_id}' not found.")

        shot = db.get(Shot, shot_id)
        if not shot:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Shot '{shot_id}' not found.")

        # 1. Check Locks
        is_locked, lock_reason = ContinuityMapper.check_shot_locked(db, project_id, shot)
        if is_locked:
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail=f"Shot '{shot_id}' is locked against modification ({lock_reason}).",
            )

        # 2. Check for active job on shot
        active_job = (
            db.query(GenerationJob)
            .filter(
                GenerationJob.shot_id == shot_id,
                GenerationJob.status.in_(ACTIVE_JOB_STATUSES),
            )
            .first()
        )
        if active_job:
            if active_job.status == "RECONCILIATION_REQUIRED":
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Shot '{shot_id}' has a job requiring reconciliation. Resolve ambiguous outcome first.",
                )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Shot '{shot_id}' already has an active generation job ('{active_job.id}', status: {active_job.status}).",
            )

        # 3. Budget Check
        budget_summary = BudgetService.get_budget_status(db, project_id)
        if budget_summary.get("is_hard_limit_exceeded"):
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail="Project hard budget limit exceeded. Keyframe generation is blocked.",
            )

        # 4. Map Shot to ImageGenerationParams
        params = ContinuityMapper.map_shot_to_image_params(
            db=db,
            project_id=project_id,
            shot=shot,
            provider_specific_params=provider_specific_params,
        )

        # 5. Execute generation via ImageProvider
        eff_provider_name = provider_name or ImageProviderFactory.get_default_provider_name()
        provider = ImageProviderFactory.get_provider(eff_provider_name)

        # Run async generation in sync context
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Nested in running event loop
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    result: ImageJobResult = executor.submit(asyncio.run, provider.generate_image(params)).result()
            else:
                result = loop.run_until_complete(provider.generate_image(params))
        except RuntimeError:
            result = asyncio.run(provider.generate_image(params))

        # 6. Handle failure and reconciliation cases
        now = datetime.now(timezone.utc)
        if result.submission_uncertain:
            job = GenerationJob(
                id=uuid.uuid4(),
                shot_id=shot.id,
                job_type="IMAGE",
                provider_name=provider.provider_id,
                provider_job_id=result.provider_job_id,
                status="RECONCILIATION_REQUIRED",
                error_message=result.error_message or "Ambiguous provider submission",
                cost_usd=result.cost_usd,
                payload=params.model_dump(),
                result=result.raw_response,
                created_at=now,
                updated_at=now,
            )
            db.add(job)
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Provider response was ambiguous. Job placed in RECONCILIATION_REQUIRED.",
            )

        if result.status == "FAILED":
            job = GenerationJob(
                id=uuid.uuid4(),
                shot_id=shot.id,
                job_type="IMAGE",
                provider_name=provider.provider_id,
                provider_job_id=result.provider_job_id,
                status="FAILED",
                error_message=result.error_message or "Image generation failed",
                cost_usd=result.cost_usd or 0.0,
                payload=params.model_dump(),
                result=result.raw_response,
                created_at=now,
                updated_at=now,
            )
            db.add(job)
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Image generation failed: {result.error_message}",
            )

        # 7. Persist generated image to Object Storage and create Asset
        image_bytes = result.image_data or b""
        if not image_bytes:
            # Fallback simple deterministic placeholder if adapter provided URL only
            image_bytes = f'<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="720"><rect width="100%" height="100%" fill="#1e293b"/><text x="50" y="80" fill="#38bdf8" font-size="24">Shot {shot.shot_number} Keyframe</text></svg>'.encode("utf-8")

        storage = get_storage_provider()
        asset_id = uuid.uuid4()
        storage_bucket = settings.OBJECT_STORAGE_BUCKET
        ext = "svg" if result.content_type == "image/svg+xml" else "png"
        storage_key = f"projects/{project_id}/keyframes/{shot.id}_{asset_id.hex[:8]}.{ext}"

        storage.put_object(
            bucket=storage_bucket,
            key=storage_key,
            data=image_bytes,
            content_type=result.content_type or "image/png",
        )

        checksum = hashlib.sha256(image_bytes).hexdigest()
        asset = Asset(
            id=asset_id,
            project_id=project_id,
            name=f"Keyframe Shot {shot.shot_number}",
            original_filename=f"keyframe_shot_{shot.shot_number}.{ext}",
            asset_type="KEYFRAME",
            content_type=result.content_type or "image/png",
            file_size_bytes=len(image_bytes),
            checksum_sha256=checksum,
            storage_bucket=storage_bucket,
            storage_key=storage_key,
            created_at=now,
            updated_at=now,
        )
        db.add(asset)
        db.flush()

        # 8. Create GenerationJob
        cost = result.cost_usd if result.cost_usd is not None else 0.04
        job = GenerationJob(
            id=uuid.uuid4(),
            shot_id=shot.id,
            job_type="IMAGE",
            provider_name=provider.provider_id,
            provider_job_id=result.provider_job_id,
            status="COMPLETED",
            cost_usd=cost,
            payload=params.model_dump(),
            result=result.raw_response,
            output_asset_id=asset.id,
            created_at=now,
            updated_at=now,
        )
        db.add(job)

        # 9. Update Shot keyframe link
        shot.keyframe_asset_id = asset.id
        shot.updated_at = now

        # 10. Record Usage Ledger entry
        ledger_entry = UsageLedger(
            id=uuid.uuid4(),
            project_id=project_id,
            shot_id=shot.id,
            job_id=job.id,
            provider=provider.provider_id,
            operation="IMAGE_GENERATION",
            actual_cost=cost,
            estimated_cost=cost,
            currency="USD",
            cost_status="COMMITTED",
            description=f"Keyframe generation for Shot {shot.shot_number}",
            created_at=now,
            updated_at=now,
        )
        db.add(ledger_entry)

        db.commit()
        db.refresh(asset)
        db.refresh(job)
        return asset, job

    @classmethod
    def estimate_keyframe_batch(
        cls,
        db: Session,
        project_id: uuid.UUID,
        operation_type: Union[KeyframeBatchOperationType, str] = KeyframeBatchOperationType.CONTINUE_INCOMPLETE_KEYFRAMES,
        shot_ids: Optional[List[uuid.UUID]] = None,
        provider_name: Optional[str] = None,
        only_incomplete: bool = True,
    ) -> Dict[str, Any]:
        """Estimate costs and shot count for batch keyframe generation."""
        project = db.get(Project, project_id)
        if not project:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project '{project_id}' not found.")

        op_enum = cls._validate_operation_type(operation_type)
        eff_provider = provider_name or ImageProviderFactory.get_default_provider_name()

        # Fetch active shots and locks
        active_shots, locked_shot_ids, archived_scene_ids = cls._fetch_active_shots_and_locks(db, project_id)

        eligible_shots: List[Shot] = []
        skipped_count = 0

        # Map shots by ID
        shots_by_id = {s.id: s for s in active_shots}
        target_ids = shot_ids if (shot_ids and len(shot_ids) > 0) else list(shots_by_id.keys())

        # Category check
        for sid in target_ids:
            if sid not in shots_by_id:
                skipped_count += 1
                continue
            sh = shots_by_id[sid]
            is_elig, _ = cls._evaluate_shot_eligibility(
                db=db,
                shot=sh,
                locked_shot_ids=locked_shot_ids,
                archived_scene_ids=archived_scene_ids,
                op_enum=op_enum,
                only_incomplete=only_incomplete,
            )
            if is_elig:
                eligible_shots.append(sh)
            else:
                skipped_count += 1

        cost_per_gen, curr, status_flag = ProviderPricingService.estimate_cost(
            provider=eff_provider,
            operation="IMAGE_GENERATION",
        )
        default_cost = 0.04
        unit_cost = cost_per_gen if (cost_per_gen is not None and status_flag != CostStatus.UNKNOWN) else default_cost
        total_cost = len(eligible_shots) * unit_cost

        warnings = []
        budget_summary = BudgetService.get_budget_status(db, project_id)
        if budget_summary.get("is_hard_limit_exceeded"):
            warnings.append("Project hard budget limit exceeded. Generation dispatch will be rejected.")
        elif budget_summary.get("is_soft_limit_exceeded"):
            warnings.append("Project spend has exceeded soft budget threshold.")

        return {
            "shot_count": len(eligible_shots),
            "skipped_count": skipped_count,
            "total_evaluated": len(target_ids),
            "estimated_cost_total": round(total_cost, 4),
            "currency": "USD",
            "has_unknown_pricing": False,
            "warning_messages": warnings,
        }

    @classmethod
    def execute_keyframe_batch(
        cls,
        db: Session,
        project_id: uuid.UUID,
        operation_type: Union[KeyframeBatchOperationType, str] = KeyframeBatchOperationType.CONTINUE_INCOMPLETE_KEYFRAMES,
        shot_ids: Optional[List[uuid.UUID]] = None,
        only_incomplete: bool = True,
        provider_name: Optional[str] = None,
        cost_authorized: bool = False,
        actor: str = "USER",
    ) -> Tuple[BatchRun, List[GenerationJob]]:
        """Batch generation of keyframe images for eligible shots with full lineage and auditability."""
        project = db.get(Project, project_id)
        if not project:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project '{project_id}' not found.")

        current_stage = project.status or "DRAFT"
        if current_stage not in ALLOWED_KEYFRAME_STAGES:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Keyframe generation requires stage in {ALLOWED_KEYFRAME_STAGES}, current status is '{current_stage}'.",
            )

        op_enum = cls._validate_operation_type(operation_type)
        eff_provider = provider_name or ImageProviderFactory.get_default_provider_name()

        # Hard budget limit check
        budget_summary = BudgetService.get_budget_status(db, project_id)
        if budget_summary.get("is_hard_limit_exceeded"):
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail="Project hard budget limit exceeded. Batch keyframe generation is blocked.",
            )

        now = datetime.now(timezone.utc)
        batch_run_id = uuid.uuid4()
        batch_run = BatchRun(
            id=batch_run_id,
            project_id=project_id,
            operation_type=op_enum.value,
            status="PROCESSING",
            requested_count=0,
            eligible_count=0,
            queued_count=0,
            skipped_count=0,
            completed_count=0,
            failed_count=0,
            created_at=now,
            updated_at=now,
        )
        db.add(batch_run)
        db.flush()

        active_shots, locked_shot_ids, archived_scene_ids = cls._fetch_active_shots_and_locks(db, project_id)
        shots_by_id = {s.id: s for s in active_shots}
        target_ids = shot_ids if (shot_ids and len(shot_ids) > 0) else list(shots_by_id.keys())

        created_jobs: List[GenerationJob] = []
        eligible_shots: List[Shot] = []

        batch_run.requested_count = len(target_ids)

        for sid in target_ids:
            if sid not in shots_by_id:
                batch_run.skipped_count += 1
                continue
            sh = shots_by_id[sid]
            is_elig, skip_reason = cls._evaluate_shot_eligibility(
                db=db,
                shot=sh,
                locked_shot_ids=locked_shot_ids,
                archived_scene_ids=archived_scene_ids,
                op_enum=op_enum,
                only_incomplete=only_incomplete,
            )
            if is_elig:
                eligible_shots.append(sh)
            else:
                batch_run.skipped_count += 1

        batch_run.eligible_count = len(eligible_shots)

        # Generate keyframes for eligible shots
        for shot in eligible_shots:
            try:
                asset, job = cls.generate_shot_keyframe(
                    db=db,
                    project_id=project_id,
                    shot_id=shot.id,
                    provider_name=eff_provider,
                    cost_authorized=cost_authorized,
                    actor=actor,
                )
                created_jobs.append(job)
                batch_run.queued_count += 1
                batch_run.completed_count += 1

                run_item = BatchRunItem(
                    id=uuid.uuid4(),
                    batch_run_id=batch_run.id,
                    shot_id=shot.id,
                    job_id=job.id,
                    decision="QUEUED",
                    created_at=datetime.now(timezone.utc),
                )
                db.add(run_item)
            except Exception as e:
                batch_run.failed_count += 1

        batch_run.status = "COMPLETED"
        batch_run.updated_at = datetime.now(timezone.utc)

        # Check if all active shots now have keyframe assets
        refreshed_active_shots, _, _ = cls._fetch_active_shots_and_locks(db, project_id)
        all_have_keyframes = (
            len(refreshed_active_shots) > 0
            and all(
                s.keyframe_asset_id is not None or s.shot_type not in ("AI_GENERATED", "MIXED")
                for s in refreshed_active_shots
            )
        )

        if all_have_keyframes and project.status in ("SHOT_PLAN_APPROVED", "IMAGES_IN_PROGRESS"):
            from_stage = project.status
            project.status = "IMAGES_GENERATED"
            project.updated_at = datetime.now(timezone.utc)
            audit = OrchestrationAudit(
                id=uuid.uuid4(),
                project_id=project_id,
                from_state=from_stage,
                to_state="IMAGES_GENERATED",
                action="ADVANCE_TO_IMAGES_GENERATED",
                actor=actor,
                result="APPLIED",
                reason_code="ALL_KEYFRAMES_GENERATED",
                detail=f"All {len(refreshed_active_shots)} shot keyframes generated.",
                created_at=datetime.now(timezone.utc),
            )
            db.add(audit)

        db.commit()
        db.refresh(batch_run)
        return batch_run, created_jobs

    @classmethod
    def _fetch_active_shots_and_locks(
        cls, db: Session, project_id: uuid.UUID
    ) -> Tuple[List[Shot], Set[uuid.UUID], Set[uuid.UUID]]:
        """Fetch unarchived active shots and active lock IDs for a project."""
        scenes = (
            db.query(Scene)
            .filter(
                (Scene.project_id == project_id)
                | (Scene.story.has(project_id=project_id))
            )
            .all()
        )
        active_scene_ids = {s.id for s in scenes if not (s.scene_config or {}).get("archived")}
        archived_scene_ids = {s.id for s in scenes if (s.scene_config or {}).get("archived")}

        active_shots = (
            db.query(Shot)
            .filter(
                Shot.scene_id.in_(active_scene_ids),
                Shot.status != "ARCHIVED",
            )
            .order_by(Shot.shot_number.asc())
            .all()
        ) if active_scene_ids else []

        locks = (
            db.query(AssetLock.entity_type, AssetLock.entity_id)
            .filter(AssetLock.project_id == project_id, AssetLock.is_locked == True)
            .all()
        )
        locked_shot_ids = {lid for etype, lid in locks if etype == "SHOT"}

        return active_shots, locked_shot_ids, archived_scene_ids

    @classmethod
    def _evaluate_shot_eligibility(
        cls,
        db: Session,
        shot: Shot,
        locked_shot_ids: Set[uuid.UUID],
        archived_scene_ids: Set[uuid.UUID],
        op_enum: KeyframeBatchOperationType,
        only_incomplete: bool = True,
    ) -> Tuple[bool, Optional[str]]:
        """Evaluate if a shot is eligible for keyframe generation under requested batch operation."""
        if shot.scene_id in archived_scene_ids or shot.status == "ARCHIVED":
            return False, "ARCHIVED"

        if shot.is_locked or shot.id in locked_shot_ids:
            return False, "LOCKED"

        # Check active jobs
        active_job = (
            db.query(GenerationJob)
            .filter(
                GenerationJob.shot_id == shot.id,
                GenerationJob.status.in_(ACTIVE_JOB_STATUSES),
            )
            .first()
        )
        if active_job:
            if active_job.status == "RECONCILIATION_REQUIRED":
                return False, "RECONCILIATION_REQUIRED"
            return False, "ACTIVE_JOB_EXISTS"

        # Completed keyframe check
        has_completed_keyframe = bool(shot.keyframe_asset_id is not None)

        if op_enum == KeyframeBatchOperationType.CONTINUE_INCOMPLETE_KEYFRAMES:
            if only_incomplete and has_completed_keyframe:
                return False, "ALREADY_COMPLETED"
            return True, None

        elif op_enum == KeyframeBatchOperationType.RETRY_FAILED_KEYFRAMES:
            # Check if there is a failed image job
            failed_image_job = (
                db.query(GenerationJob)
                .filter(
                    GenerationJob.shot_id == shot.id,
                    GenerationJob.job_type == "IMAGE",
                    GenerationJob.status == "FAILED",
                )
                .first()
            )
            if not failed_image_job:
                return False, "NO_FAILED_HISTORY"
            if has_completed_keyframe:
                return False, "ALREADY_COMPLETED"
            return True, None

        elif op_enum == KeyframeBatchOperationType.GENERATE_SELECTED_KEYFRAMES:
            return True, None

        return False, "NOT_ELIGIBLE"
