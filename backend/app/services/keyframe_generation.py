"""Service for storyboard image and keyframe generation, persistence, batch operations, and state transitions."""
import asyncio
import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple, Union, Any

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.project import Project
from app.models.scene import Scene
from app.models.story import Story
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
from app.services.cost_ledger import CostLedgerService
from app.services.storage.factory import get_storage_provider


EXECUTE_CHUNK_SIZE = 50
MAX_COMPATIBILITY_RETURNED_JOBS = 50


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


def resolve_shot_project(db: Session, shot: Shot) -> Optional[Project]:
    """Resolve Project associated with a Shot via Scene -> Story / Project."""
    if not shot or not shot.scene_id:
        return None
    scene = db.get(Scene, shot.scene_id)
    if not scene:
        return None
    if scene.project_id:
        return db.get(Project, scene.project_id)
    if scene.story_id:
        story = db.get(Story, scene.story_id)
        if story and story.project_id:
            return db.get(Project, story.project_id)
    return None


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
    def _iter_shot_chunks(
        cls,
        db: Session,
        all_scene_ids: List[uuid.UUID],
        shot_ids: Optional[List[uuid.UUID]],
        snapshot_cutoff: datetime,
        chunk_size: int = EXECUTE_CHUNK_SIZE,
    ):
        """Yield bounded chunks of shots without unbounded materialization or OFFSET."""
        if shot_ids is not None:
            requested_ids = list(dict.fromkeys(shot_ids))
            for i in range(0, len(requested_ids), chunk_size):
                chunk_req_ids = requested_ids[i:i + chunk_size]
                chunk_shots = (
                    db.query(Shot)
                    .filter(
                        Shot.scene_id.in_(all_scene_ids),
                        Shot.id.in_(chunk_req_ids),
                        Shot.status != "ARCHIVED",
                    )
                    .all()
                ) if all_scene_ids else []
                shots_by_id = {s.id: s for s in chunk_shots}
                yield shots_by_id, chunk_req_ids
        else:
            if not all_scene_ids:
                return

            last_created_at: Optional[datetime] = None
            last_id: Optional[uuid.UUID] = None

            while True:
                q = (
                    db.query(Shot)
                    .filter(
                        Shot.scene_id.in_(all_scene_ids),
                        Shot.status != "ARCHIVED",
                        Shot.created_at <= snapshot_cutoff,
                    )
                )
                if last_created_at is not None and last_id is not None:
                    q = q.filter(
                        (Shot.created_at > last_created_at)
                        | ((Shot.created_at == last_created_at) & (Shot.id > last_id))
                    )
                q = q.order_by(Shot.created_at.asc(), Shot.id.asc()).limit(chunk_size)
                page_shots = q.all()
                if not page_shots:
                    break

                shots_by_id = {s.id: s for s in page_shots}
                chunk_ids = [s.id for s in page_shots]
                last_created_at = page_shots[-1].created_at
                last_id = page_shots[-1].id

                yield shots_by_id, chunk_ids

    @classmethod
    def _categorize_job_rows(
        cls, job_rows: List[Tuple[uuid.UUID, str, Optional[str]]]
    ) -> Tuple[Set[uuid.UUID], Set[uuid.UUID], Set[uuid.UUID]]:
        shot_has_active: Set[uuid.UUID] = set()
        shot_has_reconciliation: Set[uuid.UUID] = set()
        shot_has_failed_image: Set[uuid.UUID] = set()

        for sid, jstatus, jtype in job_rows:
            if jstatus == "RECONCILIATION_REQUIRED":
                shot_has_reconciliation.add(sid)
                shot_has_active.add(sid)
            elif jstatus in ACTIVE_JOB_STATUSES:
                shot_has_active.add(sid)
            if jtype == "IMAGE" and jstatus == "FAILED":
                shot_has_failed_image.add(sid)

        return shot_has_active, shot_has_reconciliation, shot_has_failed_image

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
    ) -> Tuple[Optional[Asset], GenerationJob]:
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

        return cls._submit_shot_keyframe(
            db=db,
            project=project,
            shot=shot,
            provider_name=provider_name,
            cost_authorized=cost_authorized,
            actor=actor,
            provider_specific_params=provider_specific_params,
        )

    @classmethod
    def _submit_shot_keyframe(
        cls,
        db: Session,
        project: Project,
        shot: Shot,
        provider_name: Optional[str] = None,
        cost_authorized: bool = False,
        actor: str = "USER",
        provider_specific_params: Optional[Dict[str, Any]] = None,
        refresh: bool = True,
    ) -> Tuple[Optional[Asset], GenerationJob]:
        """Internal already-validated submission primitive for single and batch keyframe generation."""
        project_id = project.id
        eff_provider_name = provider_name or ImageProviderFactory.get_default_provider_name()

        # 1. Project lock for atomic budget check & reservation
        project = db.query(Project).filter(Project.id == project_id).with_for_update().first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        # In SQLite, touch row to acquire immediate write lock so concurrent budget checks serialize
        if db.bind and db.bind.dialect.name == "sqlite":
            project.updated_at = datetime.now(timezone.utc)
            db.flush()

        # Hard Budget Check (accounting for current committed + in-flight + estimated cost)
        est_cost, _, _ = ProviderPricingService.estimate_cost(
            provider=eff_provider_name,
            operation="IMAGE_GENERATION",
        )
        estimated_cost = est_cost if est_cost is not None else 0.04

        budget_summary = BudgetService.get_budget_status(db, project_id)
        committed_cost = budget_summary.get("total_committed_cost", 0.0)
        limit = project.budget_limit
        if budget_summary.get("is_hard_limit_exceeded") or (
            limit is not None and round(committed_cost + estimated_cost, 4) > limit
        ):
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=f"Project hard budget limit exceeded or will be exceeded by keyframe generation (committed: {committed_cost:.2f}, estimated: {estimated_cost:.2f}, limit: {limit:.2f}).",
            )

        # 2. Check Cost Authorization in AUTO mode
        default_cfg = getattr(project, "default_config", None) or {}
        mode_cfg = getattr(project, "mode_config", None) or {}
        has_persisted = False
        if isinstance(default_cfg, dict):
            has_persisted = bool(default_cfg.get("auto_cost_authorized") or default_cfg.get("cost_authorized"))
        if not has_persisted and isinstance(mode_cfg, dict):
            has_persisted = bool(mode_cfg.get("auto_cost_authorized") or mode_cfg.get("cost_authorized"))
        effective_cost_auth = cost_authorized or has_persisted

        if actor == "AUTO" and not effective_cost_auth:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail="Keyframe generation is chargeable. Explicit cost authorization required in AUTO mode.",
            )

        # 3. Map Shot to ImageGenerationParams
        params = ContinuityMapper.map_shot_to_image_params(
            db=db,
            project_id=project_id,
            shot=shot,
            provider_specific_params=provider_specific_params,
        )

        now = datetime.now(timezone.utc)
        job_id = uuid.uuid4()

        # 4. ATOMIC PRE-PROVIDER CLAIM & COST RESERVATION
        # Create and commit GenerationJob in active SUBMITTING state BEFORE invoking provider.
        # This protects against duplicate paid external calls via uq_generation_jobs_active_shot.
        job = GenerationJob(
            id=job_id,
            shot_id=shot.id,
            job_type="IMAGE",
            provider_name=eff_provider_name,
            status="SUBMITTING",
            cost_usd=estimated_cost,
            payload=params.model_dump(),
            output_asset_id=None,
            next_poll_at=None,
            poll_count=0,
            max_polls=60,
            created_at=now,
            updated_at=now,
        )
        try:
            with db.begin_nested():
                db.add(job)
                db.flush()

            CostLedgerService.record_entry(
                db,
                project_id=project_id,
                shot_id=shot.id,
                job_id=job.id,
                provider=eff_provider_name,
                operation="IMAGE_GENERATION",
                model=None,
                usage_units={"aspect_ratio": params.aspect_ratio},
                estimated_cost=estimated_cost,
                currency="USD",
                cost_status=CostStatus.ESTIMATED,
                idempotency_key=f"image_job_{job.id}",
                description=f"Keyframe generation for Shot {shot.shot_number}",
                commit=False,
            )
            db.commit()
        except IntegrityError:
            db.rollback()
            # Active job already exists or concurrent claim won race
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
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"Shot '{shot.id}' has a job requiring reconciliation. Resolve ambiguous outcome first.",
                    )
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Shot '{shot.id}' already has an active generation job ('{active_job.id}', status: {active_job.status}).",
                )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Shot '{shot.id}' already has an active generation job.",
            )

        # 5. EXECUTE GENERATION VIA PROVIDER (Only the winning claimer reaches here!)
        provider = ImageProviderFactory.get_provider(eff_provider_name)
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    result: ImageJobResult = executor.submit(asyncio.run, provider.generate_image(params)).result()
            else:
                result = loop.run_until_complete(provider.generate_image(params))
        except RuntimeError:
            try:
                result = asyncio.run(provider.generate_image(params))
            except Exception as exc:
                now_err = datetime.now(timezone.utc)
                job.status = "FAILED"
                job.error_message = f"Local failure before provider acceptance: {str(exc)}"
                job.updated_at = now_err
                CostLedgerService.confirm_job_cost(db, job_id=job.id, actual_cost=0.0)
                db.commit()
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Image generation failed: {str(exc)}",
                )
        except Exception as exc:
            now_err = datetime.now(timezone.utc)
            job.status = "FAILED"
            job.error_message = f"Local failure before provider acceptance: {str(exc)}"
            job.updated_at = now_err
            CostLedgerService.confirm_job_cost(db, job_id=job.id, actual_cost=0.0)
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Image generation failed: {str(exc)}",
            )

        now = datetime.now(timezone.utc)

        # 6. PROVIDER RESULT TRANSITIONS (Update the SAME GenerationJob claim)
        # 6a. Ambiguous submission
        if result.submission_uncertain:
            cost = result.cost_usd if result.cost_usd is not None else estimated_cost
            job.status = "RECONCILIATION_REQUIRED"
            job.provider_job_id = result.provider_job_id
            job.error_message = result.error_message or "Ambiguous provider submission"
            job.cost_usd = cost
            job.result = result.raw_response
            job.updated_at = now
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Provider response was ambiguous. Job placed in RECONCILIATION_REQUIRED.",
            )

        # 6b. Provider failure
        if result.status == "FAILED":
            cost = result.cost_usd or 0.0
            job.status = "FAILED"
            job.provider_job_id = result.provider_job_id
            job.error_message = result.error_message or "Image generation failed"
            job.cost_usd = cost
            job.result = result.raw_response
            job.updated_at = now
            CostLedgerService.confirm_job_cost(
                db,
                job_id=job.id,
                actual_cost=cost,
                provider_event_id=result.provider_job_id,
            )
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Image generation failed: {result.error_message}",
            )

        # 6c. Asynchronous pending statuses (QUEUED, PROCESSING, SUBMITTED, PENDING)
        if result.status in ("QUEUED", "PROCESSING", "SUBMITTED", "PENDING"):
            cost = result.cost_usd if result.cost_usd is not None else estimated_cost
            job.status = result.status
            job.provider_job_id = result.provider_job_id
            job.cost_usd = cost
            job.result = result.raw_response
            job.updated_at = now
            if project.status == "SHOT_PLAN_APPROVED":
                project.status = "IMAGES_IN_PROGRESS"
                project.updated_at = now
            db.commit()
            if refresh:
                db.refresh(job)
            return None, job

        # 6d. Completed result: verified completed asset creation
        image_bytes = result.image_data or b""
        if not image_bytes and result.image_url:
            try:
                import httpx
                resp = httpx.get(result.image_url, timeout=30.0)
                if resp.status_code == 200:
                    image_bytes = resp.content
            except Exception:
                pass

        if not image_bytes:
            job.status = "FAILED"
            job.provider_job_id = result.provider_job_id
            job.error_message = "Provider completed result missing image content"
            job.cost_usd = result.cost_usd or 0.0
            job.result = result.raw_response
            job.updated_at = now
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Provider completed result missing image content.",
            )

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

        cost = result.cost_usd if result.cost_usd is not None else estimated_cost

        # Update the SAME GenerationJob
        job.status = "COMPLETED"
        job.provider_job_id = result.provider_job_id
        job.cost_usd = cost
        job.result = result.raw_response
        job.output_asset_id = asset.id
        job.updated_at = now

        shot.keyframe_asset_id = asset.id
        shot.updated_at = now

        CostLedgerService.confirm_job_cost(
            db,
            job_id=job.id,
            actual_cost=cost,
            provider_event_id=result.provider_job_id,
        )

        db.commit()
        if refresh:
            db.refresh(asset)
            db.refresh(job)
        return asset, job

    @classmethod
    def complete_async_keyframe_job(
        cls,
        db: Session,
        job_id: uuid.UUID,
        result: ImageJobResult,
    ) -> Optional[Asset]:
        """Complete an asynchronous keyframe generation job after verified provider COMPLETED status."""
        job = db.get(GenerationJob, job_id)
        if not job or job.output_asset_id:
            return None

        shot = db.get(Shot, job.shot_id)
        if not shot:
            return None

        project = resolve_shot_project(db, shot)
        project_id = project.id if project else None

        image_bytes = result.image_data or b""
        if not image_bytes and result.image_url:
            try:
                import httpx
                resp = httpx.get(result.image_url, timeout=30.0)
                if resp.status_code == 200:
                    image_bytes = resp.content
            except Exception:
                pass

        if not image_bytes:
            job.status = "FAILED"
            job.error_message = "Completed provider response missing image payload"
            db.commit()
            return None

        now = datetime.now(timezone.utc)
        storage = get_storage_provider()
        asset_id = uuid.uuid4()
        storage_bucket = settings.OBJECT_STORAGE_BUCKET
        ext = "svg" if result.content_type == "image/svg+xml" else "png"
        p_id_str = str(project_id) if project_id else "unknown"
        storage_key = f"projects/{p_id_str}/keyframes/{shot.id}_{asset_id.hex[:8]}.{ext}"

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

        shot.keyframe_asset_id = asset.id
        shot.updated_at = now

        job.output_asset_id = asset.id
        job.status = "COMPLETED"
        job.updated_at = now
        db.flush()

        cost = result.cost_usd if result.cost_usd is not None else 0.04
        if project_id:
            confirmed_entry = CostLedgerService.confirm_job_cost(
                db,
                job_id=job.id,
                actual_cost=cost,
                provider_event_id=result.provider_job_id,
            )
            if not confirmed_entry:
                aspect = None
                if isinstance(job.payload, dict):
                    aspect = job.payload.get("aspect_ratio")
                CostLedgerService.record_entry(
                    db,
                    project_id=project_id,
                    shot_id=shot.id,
                    job_id=job.id,
                    provider=job.provider_name,
                    operation="IMAGE_GENERATION",
                    model=None,
                    usage_units={"aspect_ratio": aspect},
                    estimated_cost=cost,
                    actual_cost=cost,
                    currency="USD",
                    cost_status=CostStatus.CONFIRMED,
                    idempotency_key=f"image_job_{job.id}",
                    description=f"Keyframe generation for Shot {shot.shot_number}",
                    commit=False,
                )
            cls._check_and_advance_stage_if_all_keyframes_ready(db, project_id)

        db.commit()
        db.refresh(asset)
        return asset

    @classmethod
    def _check_and_advance_stage_if_all_keyframes_ready(
        cls, db: Session, project_id: uuid.UUID, actor: str = "SYSTEM"
    ) -> bool:
        """Check if all unarchived shots have keyframe assets and advance stage to IMAGES_GENERATED."""
        project = db.get(Project, project_id)
        if not project or project.status not in ("SHOT_PLAN_APPROVED", "IMAGES_IN_PROGRESS"):
            return False

        scenes = (
            db.query(Scene)
            .filter(
                (Scene.project_id == project_id)
                | (Scene.story.has(project_id=project_id))
            )
            .all()
        )
        active_scene_ids = [s.id for s in scenes if not (s.scene_config or {}).get("archived")]
        if not active_scene_ids:
            return False

        total_active_shots = (
            db.query(func.count(Shot.id))
            .filter(
                Shot.scene_id.in_(active_scene_ids),
                Shot.status != "ARCHIVED",
            )
            .scalar()
        ) or 0

        unready_count = (
            db.query(func.count(Shot.id))
            .filter(
                Shot.scene_id.in_(active_scene_ids),
                Shot.status != "ARCHIVED",
                Shot.shot_type.in_(("AI_GENERATED", "MIXED")),
                Shot.keyframe_asset_id.is_(None),
            )
            .scalar()
        ) or 0

        if total_active_shots > 0 and unready_count == 0:
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
                detail=f"All {total_active_shots} shot keyframes generated.",
                created_at=datetime.now(timezone.utc),
            )
            db.add(audit)
            db.commit()
            return True
        return False

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
        """Estimate costs and shot count for batch keyframe generation using bounded set-based queries."""
        project = db.get(Project, project_id)
        if not project:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project '{project_id}' not found.")

        op_enum = cls._validate_operation_type(operation_type)
        eff_provider = provider_name or ImageProviderFactory.get_default_provider_name()
        snapshot_cutoff = datetime.now(timezone.utc)

        scenes = (
            db.query(Scene)
            .filter(
                (Scene.project_id == project_id)
                | (Scene.story.has(project_id=project_id))
            )
            .all()
        )
        all_scene_ids = [s.id for s in scenes]
        archived_scene_ids = {s.id for s in scenes if (s.scene_config or {}).get("archived")}

        locks = (
            db.query(AssetLock.entity_type, AssetLock.entity_id)
            .filter(AssetLock.project_id == project_id, AssetLock.is_locked == True)
            .all()
        )
        locked_shot_ids = {lid for etype, lid in locks if etype == "SHOT"}
        locked_scene_ids = {lid for etype, lid in locks if etype == "SCENE"}

        eligible_count = 0
        skipped_count = 0
        total_evaluated = 0

        for shots_by_id, chunk_ids in cls._iter_shot_chunks(
            db=db,
            all_scene_ids=all_scene_ids,
            shot_ids=shot_ids,
            snapshot_cutoff=snapshot_cutoff,
            chunk_size=EXECUTE_CHUNK_SIZE,
        ):
            found_ids = list(shots_by_id.keys())
            job_rows = (
                db.query(GenerationJob.shot_id, GenerationJob.status, GenerationJob.job_type)
                .filter(GenerationJob.shot_id.in_(found_ids))
                .all()
            ) if found_ids else []

            shot_has_active, shot_has_recon, shot_has_failed_image = cls._categorize_job_rows(job_rows)

            for sid in chunk_ids:
                total_evaluated += 1
                if sid not in shots_by_id:
                    skipped_count += 1
                    continue
                sh = shots_by_id[sid]
                if sh.scene_id in archived_scene_ids or sh.status == "ARCHIVED":
                    skipped_count += 1
                    continue
                if sh.is_locked or sh.id in locked_shot_ids or sh.scene_id in locked_scene_ids:
                    skipped_count += 1
                    continue
                if sh.id in shot_has_recon or sh.id in shot_has_active:
                    skipped_count += 1
                    continue

                has_completed_kf = sh.keyframe_asset_id is not None
                if op_enum == KeyframeBatchOperationType.CONTINUE_INCOMPLETE_KEYFRAMES:
                    if only_incomplete and has_completed_kf:
                        skipped_count += 1
                        continue
                    eligible_count += 1
                elif op_enum == KeyframeBatchOperationType.RETRY_FAILED_KEYFRAMES:
                    if sh.id not in shot_has_failed_image or has_completed_kf:
                        skipped_count += 1
                        continue
                    eligible_count += 1
                elif op_enum == KeyframeBatchOperationType.GENERATE_SELECTED_KEYFRAMES:
                    eligible_count += 1

        cost_per_gen, curr, status_flag = ProviderPricingService.estimate_cost(
            provider=eff_provider,
            operation="IMAGE_GENERATION",
        )
        default_cost = 0.04
        unit_cost = cost_per_gen if (cost_per_gen is not None and status_flag != CostStatus.UNKNOWN) else default_cost
        total_cost = eligible_count * unit_cost

        warnings = []
        budget_summary = BudgetService.get_budget_status(db, project_id)
        if budget_summary.get("is_hard_limit_exceeded"):
            warnings.append("Project hard budget limit exceeded. Generation dispatch will be rejected.")
        elif budget_summary.get("is_soft_limit_exceeded"):
            warnings.append("Project spend has exceeded soft budget threshold.")

        return {
            "shot_count": eligible_count,
            "skipped_count": skipped_count,
            "total_evaluated": total_evaluated,
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
        """Batch generation of keyframe images with bounded chunking and set-based queries."""
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

        # Check Cost Authorization in AUTO mode
        default_cfg = getattr(project, "default_config", None) or {}
        mode_cfg = getattr(project, "mode_config", None) or {}
        has_persisted = False
        if isinstance(default_cfg, dict):
            has_persisted = bool(default_cfg.get("auto_cost_authorized") or default_cfg.get("cost_authorized"))
        if not has_persisted and isinstance(mode_cfg, dict):
            has_persisted = bool(mode_cfg.get("auto_cost_authorized") or mode_cfg.get("cost_authorized"))
        effective_cost_auth = cost_authorized or has_persisted

        if actor == "AUTO" and not effective_cost_auth:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail="Keyframe generation is chargeable. Explicit cost authorization required in AUTO mode.",
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

        snapshot_cutoff = datetime.now(timezone.utc)
        scenes = (
            db.query(Scene)
            .filter(
                (Scene.project_id == project_id)
                | (Scene.story.has(project_id=project_id))
            )
            .all()
        )
        all_scene_ids = [s.id for s in scenes]
        archived_scene_ids = {s.id for s in scenes if (s.scene_config or {}).get("archived")}

        locks = (
            db.query(AssetLock.entity_type, AssetLock.entity_id)
            .filter(AssetLock.project_id == project_id, AssetLock.is_locked == True)
            .all()
        )
        locked_shot_ids = {lid for etype, lid in locks if etype == "SHOT"}
        locked_scene_ids = {lid for etype, lid in locks if etype == "SCENE"}

        created_jobs: List[GenerationJob] = []

        # Iterate bounded chunks
        for shots_by_id, chunk_ids in cls._iter_shot_chunks(
            db=db,
            all_scene_ids=all_scene_ids,
            shot_ids=shot_ids,
            snapshot_cutoff=snapshot_cutoff,
            chunk_size=EXECUTE_CHUNK_SIZE,
        ):
            batch_run.requested_count += len(chunk_ids)
            found_ids = list(shots_by_id.keys())
            job_rows = (
                db.query(GenerationJob.shot_id, GenerationJob.status, GenerationJob.job_type)
                .filter(GenerationJob.shot_id.in_(found_ids))
                .all()
            ) if found_ids else []

            shot_has_active, shot_has_recon, shot_has_failed_image = cls._categorize_job_rows(job_rows)

            for sid in chunk_ids:
                if sid not in shots_by_id:
                    batch_run.skipped_count += 1
                    continue
                sh = shots_by_id[sid]
                if sh.scene_id in archived_scene_ids or sh.status == "ARCHIVED":
                    batch_run.skipped_count += 1
                    continue
                if sh.is_locked or sh.id in locked_shot_ids or sh.scene_id in locked_scene_ids:
                    batch_run.skipped_count += 1
                    continue
                if sh.id in shot_has_recon or sh.id in shot_has_active:
                    batch_run.skipped_count += 1
                    continue

                has_completed_kf = sh.keyframe_asset_id is not None
                if op_enum == KeyframeBatchOperationType.CONTINUE_INCOMPLETE_KEYFRAMES:
                    if only_incomplete and has_completed_kf:
                        batch_run.skipped_count += 1
                        continue
                elif op_enum == KeyframeBatchOperationType.RETRY_FAILED_KEYFRAMES:
                    if sh.id not in shot_has_failed_image or has_completed_kf:
                        batch_run.skipped_count += 1
                        continue
                elif op_enum == KeyframeBatchOperationType.GENERATE_SELECTED_KEYFRAMES:
                    pass

                batch_run.eligible_count += 1

                # Generate shot keyframe via internal validated primitive (no redundant GenerationJob query)
                try:
                    asset, job = cls._submit_shot_keyframe(
                        db=db,
                        project=project,
                        shot=sh,
                        provider_name=eff_provider,
                        cost_authorized=effective_cost_auth,
                        actor=actor,
                        refresh=False,
                    )
                    if len(created_jobs) < MAX_COMPATIBILITY_RETURNED_JOBS:
                        created_jobs.append(job)

                    batch_run.queued_count += 1
                    if asset is not None and job.status == "COMPLETED":
                        batch_run.completed_count += 1

                    run_item = BatchRunItem(
                        id=uuid.uuid4(),
                        batch_run_id=batch_run.id,
                        shot_id=sh.id,
                        job_id=job.id,
                        decision="QUEUED",
                        created_at=datetime.now(timezone.utc),
                    )
                    db.add(run_item)
                except HTTPException as he:
                    if he.status_code == status.HTTP_402_PAYMENT_REQUIRED:
                        batch_run.status = "FAILED"
                        batch_run.error_message = he.detail
                        break
                    batch_run.failed_count += 1
                except Exception:
                    batch_run.failed_count += 1

        batch_run.status = "COMPLETED"
        batch_run.updated_at = datetime.now(timezone.utc)

        # Stage progression check using SQL count
        cls._check_and_advance_stage_if_all_keyframes_ready(db, project_id, actor=actor)

        db.commit()
        db.refresh(batch_run)
        return batch_run, created_jobs
