"""Canonical batch and resume candidate selection and execution service.

Guarantees set-based, bounded query execution (no N+1 per-shot DB loops),
hierarchical lock respect, soft-archive preservation, truthful skip audit,
and shot-level deduplication (at most ONE new generation job per shot).
"""
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple, Union

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.project import Project
from app.models.scene import Scene
from app.models.shot import Shot
from app.models.generation_job import GenerationJob
from app.models.asset_lock import AssetLock
from app.models.batch_run import BatchRun, BatchRunItem
from app.services.job_dispatch import JobDispatchService, ALLOWED_PRODUCTION_STATUSES
from app.services.pricing import ProviderPricingService, CostStatus
from app.services.budget import BudgetService
from app.providers.factory import ProviderFactory


class CandidateSkipReason(str, Enum):
    LOCKED = "LOCKED"
    ARCHIVED = "ARCHIVED"
    ALREADY_COMPLETED = "ALREADY_COMPLETED"
    ACTIVE_JOB_EXISTS = "ACTIVE_JOB_EXISTS"
    NOT_GENERATABLE = "NOT_GENERATABLE"
    NOT_FOUND = "NOT_FOUND"
    NO_FAILED_HISTORY = "NO_FAILED_HISTORY"


class BatchOperationType(str, Enum):
    CONTINUE_INCOMPLETE = "CONTINUE_INCOMPLETE"
    RETRY_FAILED = "RETRY_FAILED"
    GENERATE_SELECTED = "GENERATE_SELECTED"


ACTIVE_JOB_STATUSES = {"PENDING", "CLAIMED", "SUBMITTING", "SUBMITTED", "POLLING", "QUEUED", "PROCESSING"}
CHUNK_SIZE = 100
EXECUTE_CHUNK_SIZE = 50


@dataclass
class CandidateEvaluation:
    shot: Shot
    is_eligible: bool
    skip_reason: Optional[CandidateSkipReason] = None


@dataclass
class BatchEvaluationResult:
    project: Project
    total_evaluated: int
    eligible_shots: List[Shot]
    skipped_items: List[Tuple[Shot, CandidateSkipReason]]
    evaluations_by_shot_id: Dict[uuid.UUID, CandidateEvaluation]


class BatchResumeService:
    @classmethod
    def _validate_operation_type(cls, operation_type: Union[BatchOperationType, str]) -> BatchOperationType:
        if isinstance(operation_type, str):
            try:
                return BatchOperationType(operation_type)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid batch operation_type '{operation_type}'. Supported operations: {[e.value for e in BatchOperationType]}",
                )
        elif isinstance(operation_type, BatchOperationType):
            return operation_type
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid batch operation_type '{operation_type}'. Supported operations: {[e.value for e in BatchOperationType]}",
            )

    @classmethod
    def _evaluate_single_shot(
        cls,
        shot: Shot,
        archived_scene_ids: Set[uuid.UUID],
        scene_story_map: Dict[uuid.UUID, Optional[uuid.UUID]],
        locked_shot_ids: Set[uuid.UUID],
        locked_scene_ids: Set[uuid.UUID],
        locked_story_ids: Set[uuid.UUID],
        shot_has_completed: Set[uuid.UUID],
        shot_has_active: Set[uuid.UUID],
        shot_has_failed: Set[uuid.UUID],
        op_enum: BatchOperationType,
        only_incomplete: bool,
        eligible_shots: List[Shot],
        skipped_items: List[Tuple[Shot, CandidateSkipReason]],
        evaluations_by_shot_id: Dict[uuid.UUID, CandidateEvaluation],
    ) -> None:
        # Rule A: Soft-Archived Shot or parent Scene is archived
        if shot.status == "ARCHIVED" or (shot.scene_id in archived_scene_ids):
            ev = CandidateEvaluation(shot=shot, is_eligible=False, skip_reason=CandidateSkipReason.ARCHIVED)
            skipped_items.append((shot, CandidateSkipReason.ARCHIVED))
            evaluations_by_shot_id[shot.id] = ev
            return

        # Rule B: Hierarchical Lock (Shot, parent Scene, parent Story)
        story_id = scene_story_map.get(shot.scene_id)
        is_locked = (
            shot.is_locked
            or (shot.id in locked_shot_ids)
            or (shot.scene_id in locked_scene_ids)
            or (story_id and story_id in locked_story_ids)
        )
        if is_locked:
            ev = CandidateEvaluation(shot=shot, is_eligible=False, skip_reason=CandidateSkipReason.LOCKED)
            skipped_items.append((shot, CandidateSkipReason.LOCKED))
            evaluations_by_shot_id[shot.id] = ev
            return

        # Rule C: Shot Type (Non-generatable / imported-only)
        if shot.shot_type not in ("AI_GENERATED", "MIXED"):
            ev = CandidateEvaluation(shot=shot, is_eligible=False, skip_reason=CandidateSkipReason.NOT_GENERATABLE)
            skipped_items.append((shot, CandidateSkipReason.NOT_GENERATABLE))
            evaluations_by_shot_id[shot.id] = ev
            return

        # Rule D: Active Job Exists -> Skip to prevent concurrent duplicate work
        if shot.id in shot_has_active:
            ev = CandidateEvaluation(shot=shot, is_eligible=False, skip_reason=CandidateSkipReason.ACTIVE_JOB_EXISTS)
            skipped_items.append((shot, CandidateSkipReason.ACTIVE_JOB_EXISTS))
            evaluations_by_shot_id[shot.id] = ev
            return

        # Rule E: Specific operation checks
        if op_enum == BatchOperationType.RETRY_FAILED:
            if shot.id in shot_has_completed:
                ev = CandidateEvaluation(shot=shot, is_eligible=False, skip_reason=CandidateSkipReason.ALREADY_COMPLETED)
                skipped_items.append((shot, CandidateSkipReason.ALREADY_COMPLETED))
                evaluations_by_shot_id[shot.id] = ev
                return
            if shot.id not in shot_has_failed:
                ev = CandidateEvaluation(shot=shot, is_eligible=False, skip_reason=CandidateSkipReason.NO_FAILED_HISTORY)
                skipped_items.append((shot, CandidateSkipReason.NO_FAILED_HISTORY))
                evaluations_by_shot_id[shot.id] = ev
                return
            ev = CandidateEvaluation(shot=shot, is_eligible=True)
            eligible_shots.append(shot)
            evaluations_by_shot_id[shot.id] = ev
            return

        elif op_enum in (BatchOperationType.CONTINUE_INCOMPLETE, BatchOperationType.GENERATE_SELECTED):
            if only_incomplete and (shot.id in shot_has_completed):
                ev = CandidateEvaluation(shot=shot, is_eligible=False, skip_reason=CandidateSkipReason.ALREADY_COMPLETED)
                skipped_items.append((shot, CandidateSkipReason.ALREADY_COMPLETED))
                evaluations_by_shot_id[shot.id] = ev
                return
            ev = CandidateEvaluation(shot=shot, is_eligible=True)
            eligible_shots.append(shot)
            evaluations_by_shot_id[shot.id] = ev
            return
    @classmethod
    def evaluate_project_candidates(
        cls,
        db: Session,
        project_id: uuid.UUID,
        operation_type: Union[BatchOperationType, str] = BatchOperationType.CONTINUE_INCOMPLETE,
        shot_ids: Optional[List[uuid.UUID]] = None,
        only_incomplete: bool = True,
    ) -> BatchEvaluationResult:
        """Set-based, bounded candidate selection.

        Performs bounded queries (O(1) queries per chunk of CHUNK_SIZE):
        1. Fetch project
        2. Fetch scenes for project (including archived scenes to properly account for archived shots)
        3. Fetch active locks for project
        4. Fetch shots and generation jobs in bounded chunks
        5. Report truthful skip reasons (including ARCHIVED, NOT_FOUND, NO_FAILED_HISTORY)
        """
        project = db.get(Project, project_id)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project '{project_id}' not found",
            )

        op_enum = cls._validate_operation_type(operation_type)

        # 1. Fetch scenes for the project in 1 query
        scenes = (
            db.query(Scene)
            .filter(
                (Scene.project_id == project_id)
                | (Scene.story.has(project_id=project_id))
            )
            .all()
        )

        all_scene_ids: List[uuid.UUID] = []
        archived_scene_ids: Set[uuid.UUID] = set()
        scene_story_map: Dict[uuid.UUID, Optional[uuid.UUID]] = {}
        for s in scenes:
            all_scene_ids.append(s.id)
            scene_story_map[s.id] = s.story_id
            cfg = s.scene_config or {}
            if cfg.get("archived", False):
                archived_scene_ids.add(s.id)

        # 2. Prefetch active locks for the project in 1 query
        locks = (
            db.query(AssetLock)
            .filter(
                AssetLock.project_id == project_id,
                AssetLock.is_locked == True,  # noqa: E712
            )
            .all()
        )
        locked_shot_ids: Set[uuid.UUID] = set()
        locked_scene_ids: Set[uuid.UUID] = set()
        locked_story_ids: Set[uuid.UUID] = set()
        for lock in locks:
            if lock.entity_type == "SHOT":
                locked_shot_ids.add(lock.entity_id)
            elif lock.entity_type == "SCENE":
                locked_scene_ids.add(lock.entity_id)
            elif lock.entity_type == "SCRIPT":
                locked_story_ids.add(lock.entity_id)

        eligible_shots: List[Shot] = []
        skipped_items: List[Tuple[Shot, CandidateSkipReason]] = []
        evaluations_by_shot_id: Dict[uuid.UUID, CandidateEvaluation] = {}

        # 3. Load Shots and Job Statuses in bounded chunks
        if shot_ids is not None:
            requested_ids = list(dict.fromkeys(shot_ids))  # preserve order, deduplicate
            found_shots_by_id: Dict[uuid.UUID, Shot] = {}
            if all_scene_ids:
                for i in range(0, len(requested_ids), CHUNK_SIZE):
                    chunk_req_ids = requested_ids[i:i + CHUNK_SIZE]
                    chunk_shots = (
                        db.query(Shot)
                        .filter(
                            Shot.scene_id.in_(all_scene_ids),
                            Shot.id.in_(chunk_req_ids),
                        )
                        .all()
                    )
                    for s in chunk_shots:
                        found_shots_by_id[s.id] = s

            found_shot_ids = list(found_shots_by_id.keys())
            shot_has_completed: Set[uuid.UUID] = set()
            shot_has_active: Set[uuid.UUID] = set()
            shot_has_failed: Set[uuid.UUID] = set()

            for i in range(0, len(found_shot_ids), CHUNK_SIZE):
                chunk_ids = found_shot_ids[i:i + CHUNK_SIZE]
                job_rows = (
                    db.query(GenerationJob.shot_id, GenerationJob.status)
                    .filter(GenerationJob.shot_id.in_(chunk_ids))
                    .all()
                )
                for s_id, j_status in job_rows:
                    if j_status == "COMPLETED":
                        shot_has_completed.add(s_id)
                    elif j_status in ACTIVE_JOB_STATUSES:
                        shot_has_active.add(s_id)
                    elif j_status == "FAILED":
                        shot_has_failed.add(s_id)

            # Evaluate each requested ID
            for req_id in requested_ids:
                if req_id not in found_shots_by_id:
                    dummy_shot = Shot(id=req_id, shot_number=0, shot_type="UNKNOWN")
                    ev = CandidateEvaluation(shot=dummy_shot, is_eligible=False, skip_reason=CandidateSkipReason.NOT_FOUND)
                    skipped_items.append((dummy_shot, CandidateSkipReason.NOT_FOUND))
                    evaluations_by_shot_id[req_id] = ev
                    continue

                shot = found_shots_by_id[req_id]
                cls._evaluate_single_shot(
                    shot=shot,
                    archived_scene_ids=archived_scene_ids,
                    scene_story_map=scene_story_map,
                    locked_shot_ids=locked_shot_ids,
                    locked_scene_ids=locked_scene_ids,
                    locked_story_ids=locked_story_ids,
                    shot_has_completed=shot_has_completed,
                    shot_has_active=shot_has_active,
                    shot_has_failed=shot_has_failed,
                    op_enum=op_enum,
                    only_incomplete=only_incomplete,
                    eligible_shots=eligible_shots,
                    skipped_items=skipped_items,
                    evaluations_by_shot_id=evaluations_by_shot_id,
                )

        else:
            # Whole-project evaluation: paginate shots in bounded chunks
            if not all_scene_ids:
                return BatchEvaluationResult(
                    project=project,
                    total_evaluated=0,
                    eligible_shots=[],
                    skipped_items=[],
                    evaluations_by_shot_id={},
                )

            offset = 0
            while True:
                chunk_shots = (
                    db.query(Shot)
                    .filter(Shot.scene_id.in_(all_scene_ids))
                    .order_by(Shot.scene_id.asc(), Shot.shot_number.asc())
                    .offset(offset)
                    .limit(CHUNK_SIZE)
                    .all()
                )
                if not chunk_shots:
                    break

                chunk_shot_ids = [s.id for s in chunk_shots]
                shot_has_completed: Set[uuid.UUID] = set()
                shot_has_active: Set[uuid.UUID] = set()
                shot_has_failed: Set[uuid.UUID] = set()

                job_rows = (
                    db.query(GenerationJob.shot_id, GenerationJob.status)
                    .filter(GenerationJob.shot_id.in_(chunk_shot_ids))
                    .all()
                )
                for s_id, j_status in job_rows:
                    if j_status == "COMPLETED":
                        shot_has_completed.add(s_id)
                    elif j_status in ACTIVE_JOB_STATUSES:
                        shot_has_active.add(s_id)
                    elif j_status == "FAILED":
                        shot_has_failed.add(s_id)

                for shot in chunk_shots:
                    cls._evaluate_single_shot(
                        shot=shot,
                        archived_scene_ids=archived_scene_ids,
                        scene_story_map=scene_story_map,
                        locked_shot_ids=locked_shot_ids,
                        locked_scene_ids=locked_scene_ids,
                        locked_story_ids=locked_story_ids,
                        shot_has_completed=shot_has_completed,
                        shot_has_active=shot_has_active,
                        shot_has_failed=shot_has_failed,
                        op_enum=op_enum,
                        only_incomplete=only_incomplete,
                        eligible_shots=eligible_shots,
                        skipped_items=skipped_items,
                        evaluations_by_shot_id=evaluations_by_shot_id,
                    )

                offset += CHUNK_SIZE

        total_evaluated = len(eligible_shots) + len(skipped_items)

        return BatchEvaluationResult(
            project=project,
            total_evaluated=total_evaluated,
            eligible_shots=eligible_shots,
            skipped_items=skipped_items,
            evaluations_by_shot_id=evaluations_by_shot_id,
        )

    @classmethod
    def estimate_batch(
        cls,
        db: Session,
        project_id: uuid.UUID,
        operation_type: Union[BatchOperationType, str] = BatchOperationType.CONTINUE_INCOMPLETE,
        shot_ids: Optional[List[uuid.UUID]] = None,
        provider_name: Optional[str] = None,
        only_incomplete: bool = True,
    ) -> dict:
        """Preview and estimate batch costs using the exact same candidate selection rules."""
        eval_result = cls.evaluate_project_candidates(
            db=db,
            project_id=project_id,
            operation_type=operation_type,
            shot_ids=shot_ids,
            only_incomplete=only_incomplete,
        )

        eff_provider = provider_name or ProviderFactory.get_default_provider_name()
        total_cost = 0.0
        has_unknown = False

        for shot in eval_result.eligible_shots:
            cost, curr, status_flag = ProviderPricingService.estimate_cost(
                provider=eff_provider,
                operation="VIDEO_GENERATION",
                params={"duration_seconds": shot.duration_seconds},
            )
            if status_flag == CostStatus.UNKNOWN or cost is None:
                has_unknown = True
            else:
                total_cost += cost

        warnings = []
        if has_unknown:
            warnings.append("Cost pricing is UNKNOWN for one or more candidate shots. Prices will not be fabricated.")

        project = eval_result.project
        if project.budget_limit is not None:
            summary = BudgetService.get_project_budget_summary(db, project_id)
            if summary.hard_limit_exceeded:
                warnings.append("Project is currently over hard budget limit. Dispatch will be rejected by safety gates.")
            elif summary.soft_limit_exceeded:
                warnings.append(f"Project spend has exceeded soft threshold ({project.budget_threshold_percentage}%).")

        return {
            "shot_count": len(eval_result.eligible_shots),
            "skipped_count": len(eval_result.skipped_items),
            "total_evaluated": eval_result.total_evaluated,
            "estimated_cost_total": round(total_cost, 4) if not has_unknown else None,
            "currency": "USD",
            "has_unknown_pricing": has_unknown,
            "warning_messages": warnings,
        }

    @classmethod
    def execute_batch(
        cls,
        db: Session,
        project_id: uuid.UUID,
        operation_type: Union[BatchOperationType, str] = BatchOperationType.CONTINUE_INCOMPLETE,
        shot_ids: Optional[List[uuid.UUID]] = None,
        provider_name: Optional[str] = None,
        only_incomplete: bool = True,
    ) -> Tuple[BatchRun, List[GenerationJob]]:
        """Canonical batch and resume execution.

        Enforces production stage gate, creates a BatchRun and BatchRunItems,
        deduplicates by shot, and dispatches eligible jobs safely with transactional audit.
        """
        project = db.get(Project, project_id)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project '{project_id}' not found",
            )

        if project.status not in ALLOWED_PRODUCTION_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Production generation requires 'SHOT_PLAN_APPROVED' stage, current project status is '{project.status}'.",
            )

        op_enum = cls._validate_operation_type(operation_type)

        eval_result = cls.evaluate_project_candidates(
            db=db,
            project_id=project_id,
            operation_type=op_enum,
            shot_ids=shot_ids,
            only_incomplete=only_incomplete,
        )

        eff_provider = provider_name or ProviderFactory.get_default_provider_name()
        now = datetime.now(timezone.utc)

        batch_run = BatchRun(
            id=uuid.uuid4(),
            project_id=project_id,
            operation_type=op_enum.value,
            status="DISPATCHED",
            requested_count=eval_result.total_evaluated,
            eligible_count=len(eval_result.eligible_shots),
            queued_count=0,
            skipped_count=len(eval_result.skipped_items),
            completed_count=0,
            failed_count=0,
            created_at=now,
            updated_at=now,
        )
        db.add(batch_run)

        # Record skipped items
        for shot, skip_reason in eval_result.skipped_items:
            item = BatchRunItem(
                id=uuid.uuid4(),
                batch_run_id=batch_run.id,
                shot_id=shot.id,
                job_id=None,
                decision="SKIPPED",
                skip_reason=skip_reason.value if hasattr(skip_reason, "value") else str(skip_reason),
                created_at=now,
            )
            db.add(item)
        db.commit()

        created_jobs: List[GenerationJob] = []
        has_dispatch_failure = False

        # Dispatch eligible shots in bounded chunks
        for i in range(0, len(eval_result.eligible_shots), EXECUTE_CHUNK_SIZE):
            chunk = eval_result.eligible_shots[i:i + EXECUTE_CHUNK_SIZE]
            for shot in chunk:
                try:
                    job = JobDispatchService.create_and_dispatch_job(
                        db=db,
                        shot_id=shot.id,
                        provider_name=eff_provider,
                        lock_shot=True,
                        commit=True,
                    )
                    created_jobs.append(job)

                    item = BatchRunItem(
                        id=uuid.uuid4(),
                        batch_run_id=batch_run.id,
                        shot_id=shot.id,
                        job_id=job.id,
                        decision="QUEUED",
                        skip_reason=None,
                        created_at=now,
                    )
                    db.add(item)
                except Exception as exc:
                    has_dispatch_failure = True
                    err_msg = exc.detail if hasattr(exc, "detail") else str(exc)
                    item = BatchRunItem(
                        id=uuid.uuid4(),
                        batch_run_id=batch_run.id,
                        shot_id=shot.id,
                        job_id=None,
                        decision="FAILED",
                        skip_reason=str(err_msg)[:100],
                        created_at=now,
                    )
                    db.add(item)
            db.commit()

        batch_run.queued_count = len(created_jobs)
        if has_dispatch_failure:
            batch_run.status = "PARTIAL_FAILED" if len(created_jobs) > 0 else "FAILED"
        else:
            batch_run.status = "DISPATCHED"
        batch_run.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(batch_run)

        return batch_run, created_jobs

    @classmethod
    def reconcile_batch_run_counts(cls, db: Session, batch_run: BatchRun) -> BatchRun:
        """Dynamically derive truthful completed_count and failed_count from linked generation jobs."""
        job_ids = [item.job_id for item in batch_run.items if item.job_id is not None]
        if not job_ids:
            return batch_run

        stats = (
            db.query(
                func.count().filter(GenerationJob.status == "COMPLETED").label("completed_count"),
                func.count().filter(GenerationJob.status.in_(["FAILED", "RECONCILIATION_REQUIRED"])).label("failed_count"),
            )
            .filter(GenerationJob.id.in_(job_ids))
            .one()
        )
        batch_run.completed_count = stats.completed_count or 0
        batch_run.failed_count = stats.failed_count or 0
        return batch_run

    @classmethod
    def list_project_batch_runs(
        cls,
        db: Session,
        project_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> List[BatchRun]:
        runs = (
            db.query(BatchRun)
            .filter(BatchRun.project_id == project_id)
            .order_by(BatchRun.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        for r in runs:
            cls.reconcile_batch_run_counts(db, r)
        return runs

    @classmethod
    def get_batch_run_details(
        cls,
        db: Session,
        project_id: uuid.UUID,
        run_id: uuid.UUID,
    ) -> BatchRun:
        run = (
            db.query(BatchRun)
            .filter(BatchRun.id == run_id, BatchRun.project_id == project_id)
            .first()
        )
        if not run:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"BatchRun '{run_id}' not found for project '{project_id}'",
            )
        return cls.reconcile_batch_run_counts(db, run)
