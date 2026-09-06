"""Canonical batch and resume candidate selection and execution service.

Guarantees set-based, bounded query execution (no N+1 per-shot DB loops),
hierarchical lock respect, soft-archive preservation, truthful skip audit,
and shot-level deduplication (at most ONE new generation job per shot).
"""
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple

from fastapi import HTTPException, status
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


ACTIVE_JOB_STATUSES = {"PENDING", "CLAIMED", "SUBMITTING", "SUBMITTED", "POLLING", "QUEUED", "PROCESSING"}


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
    def evaluate_project_candidates(
        cls,
        db: Session,
        project_id: uuid.UUID,
        operation_type: str = "CONTINUE_INCOMPLETE",
        shot_ids: Optional[List[uuid.UUID]] = None,
        only_incomplete: bool = True,
    ) -> BatchEvaluationResult:
        """Set-based candidate selection.

        Performs a fixed, small number of DB queries (O(1) queries regardless of shot count):
        1. Fetch project
        2. Fetch unarchived scenes for project (via project_id or story.project_id)
        3. Fetch shots for those scenes (optionally filtered by shot_ids)
        4. Fetch active locks for project
        5. Fetch job statuses grouped by shot_id
        """
        project = db.get(Project, project_id)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project '{project_id}' not found",
            )

        # 1. Fetch scenes for the project in 1 query
        scenes = (
            db.query(Scene)
            .filter(
                (Scene.project_id == project_id)
                | (Scene.story.has(project_id=project_id))
            )
            .all()
        )

        unarchived_scene_ids: List[uuid.UUID] = []
        scene_story_map: Dict[uuid.UUID, Optional[uuid.UUID]] = {}
        for s in scenes:
            cfg = s.scene_config or {}
            if not cfg.get("archived", False):
                unarchived_scene_ids.append(s.id)
                scene_story_map[s.id] = s.story_id

        if not unarchived_scene_ids:
            return BatchEvaluationResult(
                project=project,
                total_evaluated=0,
                eligible_shots=[],
                skipped_items=[],
                evaluations_by_shot_id={},
            )

        # 2. Fetch shots in 1 query
        shot_query = db.query(Shot).filter(Shot.scene_id.in_(unarchived_scene_ids))
        if shot_ids is not None:
            shot_query = shot_query.filter(Shot.id.in_(shot_ids))
        shots = shot_query.order_by(Shot.shot_number.asc()).all()

        if not shots:
            return BatchEvaluationResult(
                project=project,
                total_evaluated=0,
                eligible_shots=[],
                skipped_items=[],
                evaluations_by_shot_id={},
            )

        shot_id_list = [s.id for s in shots]

        # 3. Prefetch active locks for the project in 1 query
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

        # 4. Prefetch generation job statuses in 1 query
        job_rows = (
            db.query(GenerationJob.shot_id, GenerationJob.status)
            .filter(GenerationJob.shot_id.in_(shot_id_list))
            .all()
        )

        shot_has_completed: Set[uuid.UUID] = set()
        shot_has_active: Set[uuid.UUID] = set()
        shot_has_failed: Set[uuid.UUID] = set()

        for s_id, j_status in job_rows:
            if j_status == "COMPLETED":
                shot_has_completed.add(s_id)
            elif j_status in ACTIVE_JOB_STATUSES:
                shot_has_active.add(s_id)
            elif j_status == "FAILED":
                shot_has_failed.add(s_id)

        # 5. Evaluate each shot in-memory
        eligible_shots: List[Shot] = []
        skipped_items: List[Tuple[Shot, CandidateSkipReason]] = []
        evaluations_by_shot_id: Dict[uuid.UUID, CandidateEvaluation] = {}

        for shot in shots:
            # Rule A: Soft-Archived Shot
            if shot.status == "ARCHIVED":
                ev = CandidateEvaluation(shot=shot, is_eligible=False, skip_reason=CandidateSkipReason.ARCHIVED)
                skipped_items.append((shot, CandidateSkipReason.ARCHIVED))
                evaluations_by_shot_id[shot.id] = ev
                continue

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
                continue

            # Rule C: Shot Type (Non-generatable / imported-only)
            if shot.shot_type not in ("AI_GENERATED", "MIXED"):
                ev = CandidateEvaluation(shot=shot, is_eligible=False, skip_reason=CandidateSkipReason.NOT_GENERATABLE)
                skipped_items.append((shot, CandidateSkipReason.NOT_GENERATABLE))
                evaluations_by_shot_id[shot.id] = ev
                continue

            # Rule D: Active Job Exists -> Skip to prevent concurrent duplicate work
            if shot.id in shot_has_active:
                ev = CandidateEvaluation(shot=shot, is_eligible=False, skip_reason=CandidateSkipReason.ACTIVE_JOB_EXISTS)
                skipped_items.append((shot, CandidateSkipReason.ACTIVE_JOB_EXISTS))
                evaluations_by_shot_id[shot.id] = ev
                continue

            # Rule E: Specific operation checks
            if operation_type == "RETRY_FAILED":
                # Must have a failed job, but no completed job and no active job
                if shot.id in shot_has_completed:
                    ev = CandidateEvaluation(shot=shot, is_eligible=False, skip_reason=CandidateSkipReason.ALREADY_COMPLETED)
                    skipped_items.append((shot, CandidateSkipReason.ALREADY_COMPLETED))
                    evaluations_by_shot_id[shot.id] = ev
                    continue
                if shot.id not in shot_has_failed:
                    # No failed job to retry
                    ev = CandidateEvaluation(shot=shot, is_eligible=False, skip_reason=CandidateSkipReason.ALREADY_COMPLETED)
                    skipped_items.append((shot, CandidateSkipReason.ALREADY_COMPLETED))
                    evaluations_by_shot_id[shot.id] = ev
                    continue
                # Eligible for retry
                ev = CandidateEvaluation(shot=shot, is_eligible=True)
                eligible_shots.append(shot)
                evaluations_by_shot_id[shot.id] = ev

            elif operation_type == "CONTINUE_INCOMPLETE":
                if only_incomplete and (shot.id in shot_has_completed):
                    ev = CandidateEvaluation(shot=shot, is_eligible=False, skip_reason=CandidateSkipReason.ALREADY_COMPLETED)
                    skipped_items.append((shot, CandidateSkipReason.ALREADY_COMPLETED))
                    evaluations_by_shot_id[shot.id] = ev
                    continue
                ev = CandidateEvaluation(shot=shot, is_eligible=True)
                eligible_shots.append(shot)
                evaluations_by_shot_id[shot.id] = ev

            elif operation_type == "GENERATE_SELECTED":
                if only_incomplete and (shot.id in shot_has_completed):
                    ev = CandidateEvaluation(shot=shot, is_eligible=False, skip_reason=CandidateSkipReason.ALREADY_COMPLETED)
                    skipped_items.append((shot, CandidateSkipReason.ALREADY_COMPLETED))
                    evaluations_by_shot_id[shot.id] = ev
                    continue
                ev = CandidateEvaluation(shot=shot, is_eligible=True)
                eligible_shots.append(shot)
                evaluations_by_shot_id[shot.id] = ev

            else:
                # Default behavior
                if only_incomplete and (shot.id in shot_has_completed):
                    ev = CandidateEvaluation(shot=shot, is_eligible=False, skip_reason=CandidateSkipReason.ALREADY_COMPLETED)
                    skipped_items.append((shot, CandidateSkipReason.ALREADY_COMPLETED))
                    evaluations_by_shot_id[shot.id] = ev
                    continue
                ev = CandidateEvaluation(shot=shot, is_eligible=True)
                eligible_shots.append(shot)
                evaluations_by_shot_id[shot.id] = ev

        return BatchEvaluationResult(
            project=project,
            total_evaluated=len(shots),
            eligible_shots=eligible_shots,
            skipped_items=skipped_items,
            evaluations_by_shot_id=evaluations_by_shot_id,
        )

    @classmethod
    def estimate_batch(
        cls,
        db: Session,
        project_id: uuid.UUID,
        operation_type: str = "CONTINUE_INCOMPLETE",
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
        operation_type: str = "CONTINUE_INCOMPLETE",
        shot_ids: Optional[List[uuid.UUID]] = None,
        provider_name: Optional[str] = None,
        only_incomplete: bool = True,
    ) -> Tuple[BatchRun, List[GenerationJob]]:
        """Canonical batch and resume execution.

        Enforces production stage gate, creates a BatchRun and BatchRunItems,
        deduplicates by shot, and dispatches eligible jobs safely.
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

        eval_result = cls.evaluate_project_candidates(
            db=db,
            project_id=project_id,
            operation_type=operation_type,
            shot_ids=shot_ids,
            only_incomplete=only_incomplete,
        )

        eff_provider = provider_name or ProviderFactory.get_default_provider_name()
        now = datetime.now(timezone.utc)

        batch_run = BatchRun(
            id=uuid.uuid4(),
            project_id=project_id,
            operation_type=operation_type,
            status="COMPLETED",
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

        created_jobs: List[GenerationJob] = []

        # Dispatch eligible shots (deduplicated by shot)
        for shot in eval_result.eligible_shots:
            job = JobDispatchService.create_and_dispatch_job(
                db=db,
                shot_id=shot.id,
                provider_name=eff_provider,
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

        batch_run.queued_count = len(created_jobs)
        db.commit()
        db.refresh(batch_run)

        return batch_run, created_jobs
