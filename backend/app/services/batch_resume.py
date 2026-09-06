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
from sqlalchemy.exc import IntegrityError
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
from app.schemas.generation_job import BatchRunDetailResponse, BatchRunItemResponse


class CandidateSkipReason(str, Enum):
    LOCKED = "LOCKED"
    ARCHIVED = "ARCHIVED"
    ALREADY_COMPLETED = "ALREADY_COMPLETED"
    ACTIVE_JOB_EXISTS = "ACTIVE_JOB_EXISTS"
    CANCELLATION_IN_PROGRESS = "CANCELLATION_IN_PROGRESS"
    RECONCILIATION_REQUIRED = "RECONCILIATION_REQUIRED"
    NOT_GENERATABLE = "NOT_GENERATABLE"
    NOT_FOUND = "NOT_FOUND"
    NO_FAILED_HISTORY = "NO_FAILED_HISTORY"


class BatchOperationType(str, Enum):
    CONTINUE_INCOMPLETE = "CONTINUE_INCOMPLETE"
    RETRY_FAILED = "RETRY_FAILED"
    GENERATE_SELECTED = "GENERATE_SELECTED"


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
    def _categorize_job_rows(
        cls, job_rows: List[Tuple[uuid.UUID, str]]
    ) -> Tuple[Set[uuid.UUID], Set[uuid.UUID], Set[uuid.UUID], Set[uuid.UUID], Set[uuid.UUID]]:
        shot_has_completed: Set[uuid.UUID] = set()
        shot_has_cancelling: Set[uuid.UUID] = set()
        shot_has_reconciliation: Set[uuid.UUID] = set()
        shot_has_active: Set[uuid.UUID] = set()
        shot_has_failed: Set[uuid.UUID] = set()

        for s_id, j_status in job_rows:
            if j_status == "COMPLETED":
                shot_has_completed.add(s_id)
            elif j_status == "RECONCILIATION_REQUIRED":
                shot_has_reconciliation.add(s_id)
            elif j_status == "CANCELLING":
                shot_has_cancelling.add(s_id)
            elif j_status in ACTIVE_JOB_STATUSES:
                shot_has_active.add(s_id)
            elif j_status == "FAILED":
                shot_has_failed.add(s_id)

        return shot_has_completed, shot_has_cancelling, shot_has_reconciliation, shot_has_active, shot_has_failed

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
        shot_has_cancelling: Set[uuid.UUID],
        shot_has_reconciliation: Set[uuid.UUID],
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

        # Rule D1: Ambiguous provider state -> explicit reconciliation required first
        if shot.id in shot_has_reconciliation:
            ev = CandidateEvaluation(shot=shot, is_eligible=False, skip_reason=CandidateSkipReason.RECONCILIATION_REQUIRED)
            skipped_items.append((shot, CandidateSkipReason.RECONCILIATION_REQUIRED))
            evaluations_by_shot_id[shot.id] = ev
            return

        # Rule D2: Cancellation in-flight -> automatic regeneration blocked
        if shot.id in shot_has_cancelling:
            ev = CandidateEvaluation(shot=shot, is_eligible=False, skip_reason=CandidateSkipReason.CANCELLATION_IN_PROGRESS)
            skipped_items.append((shot, CandidateSkipReason.CANCELLATION_IN_PROGRESS))
            evaluations_by_shot_id[shot.id] = ev
            return

        # Rule D3: Active Job Exists -> Skip to prevent concurrent duplicate work
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
    def _evaluate_shot_decision(
        cls,
        shot: Shot,
        archived_scene_ids: Set[uuid.UUID],
        scene_story_map: Dict[uuid.UUID, Optional[uuid.UUID]],
        locked_shot_ids: Set[uuid.UUID],
        locked_scene_ids: Set[uuid.UUID],
        locked_story_ids: Set[uuid.UUID],
        shot_has_completed: Set[uuid.UUID],
        shot_has_cancelling: Set[uuid.UUID],
        shot_has_reconciliation: Set[uuid.UUID],
        shot_has_active: Set[uuid.UUID],
        shot_has_failed: Set[uuid.UUID],
        op_enum: BatchOperationType,
        only_incomplete: bool,
    ) -> Tuple[bool, Optional[CandidateSkipReason]]:
        """Streaming candidate evaluation returning (is_eligible, skip_reason)."""
        if shot.status == "ARCHIVED" or (shot.scene_id in archived_scene_ids):
            return False, CandidateSkipReason.ARCHIVED

        story_id = scene_story_map.get(shot.scene_id)
        is_locked = (
            shot.is_locked
            or (shot.id in locked_shot_ids)
            or (shot.scene_id in locked_scene_ids)
            or (story_id and story_id in locked_story_ids)
        )
        if is_locked:
            return False, CandidateSkipReason.LOCKED

        if shot.shot_type not in ("AI_GENERATED", "MIXED"):
            return False, CandidateSkipReason.NOT_GENERATABLE

        if shot.id in shot_has_reconciliation:
            return False, CandidateSkipReason.RECONCILIATION_REQUIRED

        if shot.id in shot_has_cancelling:
            return False, CandidateSkipReason.CANCELLATION_IN_PROGRESS

        if shot.id in shot_has_active:
            return False, CandidateSkipReason.ACTIVE_JOB_EXISTS

        if op_enum == BatchOperationType.RETRY_FAILED:
            if shot.id in shot_has_completed:
                return False, CandidateSkipReason.ALREADY_COMPLETED
            if shot.id not in shot_has_failed:
                return False, CandidateSkipReason.NO_FAILED_HISTORY
            return True, None

        elif op_enum in (BatchOperationType.CONTINUE_INCOMPLETE, BatchOperationType.GENERATE_SELECTED):
            if only_incomplete and (shot.id in shot_has_completed):
                return False, CandidateSkipReason.ALREADY_COMPLETED
            return True, None

        return True, None

    @classmethod
    def evaluate_project_candidates(
        cls,
        db: Session,
        project_id: uuid.UUID,
        operation_type: Union[BatchOperationType, str] = BatchOperationType.CONTINUE_INCOMPLETE,
        shot_ids: Optional[List[uuid.UUID]] = None,
        only_incomplete: bool = True,
    ) -> BatchEvaluationResult:
        """Set-based candidate selection for inspection and tests."""
        project = db.get(Project, project_id)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project '{project_id}' not found",
            )

        op_enum = cls._validate_operation_type(operation_type)

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

        if shot_ids is not None:
            requested_ids = list(dict.fromkeys(shot_ids))
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
            job_rows: List[Tuple[uuid.UUID, str]] = []
            for i in range(0, len(found_shot_ids), CHUNK_SIZE):
                chunk_ids = found_shot_ids[i:i + CHUNK_SIZE]
                rows = (
                    db.query(GenerationJob.shot_id, GenerationJob.status)
                    .filter(GenerationJob.shot_id.in_(chunk_ids))
                    .all()
                )
                job_rows.extend(rows)

            (
                shot_has_completed,
                shot_has_cancelling,
                shot_has_reconciliation,
                shot_has_active,
                shot_has_failed,
            ) = cls._categorize_job_rows(job_rows)

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
                    shot_has_cancelling=shot_has_cancelling,
                    shot_has_reconciliation=shot_has_reconciliation,
                    shot_has_active=shot_has_active,
                    shot_has_failed=shot_has_failed,
                    op_enum=op_enum,
                    only_incomplete=only_incomplete,
                    eligible_shots=eligible_shots,
                    skipped_items=skipped_items,
                    evaluations_by_shot_id=evaluations_by_shot_id,
                )

        else:
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
                    .join(Scene, Shot.scene_id == Scene.id)
                    .filter(Scene.id.in_(all_scene_ids))
                    .order_by(Scene.scene_number.asc(), Shot.shot_number.asc(), Shot.id.asc())
                    .offset(offset)
                    .limit(CHUNK_SIZE)
                    .all()
                )
                if not chunk_shots:
                    break

                chunk_shot_ids = [s.id for s in chunk_shots]
                job_rows = (
                    db.query(GenerationJob.shot_id, GenerationJob.status)
                    .filter(GenerationJob.shot_id.in_(chunk_shot_ids))
                    .all()
                )
                (
                    shot_has_completed,
                    shot_has_cancelling,
                    shot_has_reconciliation,
                    shot_has_active,
                    shot_has_failed,
                ) = cls._categorize_job_rows(job_rows)

                for shot in chunk_shots:
                    cls._evaluate_single_shot(
                        shot=shot,
                        archived_scene_ids=archived_scene_ids,
                        scene_story_map=scene_story_map,
                        locked_shot_ids=locked_shot_ids,
                        locked_scene_ids=locked_scene_ids,
                        locked_story_ids=locked_story_ids,
                        shot_has_completed=shot_has_completed,
                        shot_has_cancelling=shot_has_cancelling,
                        shot_has_reconciliation=shot_has_reconciliation,
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
        """Bounded streaming estimation of batch costs without accumulating full project lists."""
        project = db.get(Project, project_id)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project '{project_id}' not found",
            )

        op_enum = cls._validate_operation_type(operation_type)
        eff_provider = provider_name or ProviderFactory.get_default_provider_name()

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

        locks = (
            db.query(AssetLock)
            .filter(
                AssetLock.project_id == project_id,
                AssetLock.is_locked == True,  # noqa: E712
            )
            .all()
        )
        locked_shot_ids = {l.entity_id for l in locks if l.entity_type == "SHOT"}
        locked_scene_ids = {l.entity_id for l in locks if l.entity_type == "SCENE"}
        locked_story_ids = {l.entity_id for l in locks if l.entity_type == "SCRIPT"}

        eligible_count = 0
        skipped_count = 0
        total_evaluated = 0
        total_cost = 0.0
        has_unknown = False

        if shot_ids is not None:
            candidate_shot_ids = list(dict.fromkeys(shot_ids))
        else:
            if all_scene_ids:
                candidate_shot_ids = [
                    row[0]
                    for row in (
                        db.query(Shot.id)
                        .join(Scene, Shot.scene_id == Scene.id)
                        .filter(Scene.id.in_(all_scene_ids))
                        .order_by(Scene.scene_number.asc(), Shot.shot_number.asc(), Shot.id.asc())
                        .all()
                    )
                ]
            else:
                candidate_shot_ids = []

        for i in range(0, len(candidate_shot_ids), EXECUTE_CHUNK_SIZE):
            chunk_req_ids = candidate_shot_ids[i:i + EXECUTE_CHUNK_SIZE]
            chunk_shots = (
                db.query(Shot)
                .filter(
                    Shot.scene_id.in_(all_scene_ids),
                    Shot.id.in_(chunk_req_ids),
                )
                .all()
            ) if all_scene_ids else []
            shots_by_id = {s.id: s for s in chunk_shots}

            job_rows = (
                db.query(GenerationJob.shot_id, GenerationJob.status)
                .filter(GenerationJob.shot_id.in_(chunk_req_ids))
                .all()
            )
            (
                shot_has_completed,
                shot_has_cancelling,
                shot_has_reconciliation,
                shot_has_active,
                shot_has_failed,
            ) = cls._categorize_job_rows(job_rows)

            for req_id in chunk_req_ids:
                total_evaluated += 1
                if req_id not in shots_by_id:
                    skipped_count += 1
                    continue

                shot = shots_by_id[req_id]
                is_eligible, _ = cls._evaluate_shot_decision(
                    shot=shot,
                    archived_scene_ids=archived_scene_ids,
                    scene_story_map=scene_story_map,
                    locked_shot_ids=locked_shot_ids,
                    locked_scene_ids=locked_scene_ids,
                    locked_story_ids=locked_story_ids,
                    shot_has_completed=shot_has_completed,
                    shot_has_cancelling=shot_has_cancelling,
                    shot_has_reconciliation=shot_has_reconciliation,
                    shot_has_active=shot_has_active,
                    shot_has_failed=shot_has_failed,
                    op_enum=op_enum,
                    only_incomplete=only_incomplete,
                )
                if is_eligible:
                    eligible_count += 1
                    cost, curr, status_flag = ProviderPricingService.estimate_cost(
                        provider=eff_provider,
                        operation="VIDEO_GENERATION",
                        params={"duration_seconds": shot.duration_seconds},
                    )
                    if status_flag == CostStatus.UNKNOWN or cost is None:
                        has_unknown = True
                    else:
                        total_cost += cost
                else:
                    skipped_count += 1

        warnings = []
        if has_unknown:
            warnings.append("Cost pricing is UNKNOWN for one or more candidate shots. Prices will not be fabricated.")

        if project.budget_limit is not None:
            summary = BudgetService.get_project_budget_summary(db, project_id)
            if summary.hard_limit_exceeded:
                warnings.append("Project is currently over hard budget limit. Dispatch will be rejected by safety gates.")
            elif summary.soft_limit_exceeded:
                warnings.append(f"Project spend has exceeded soft threshold ({project.budget_threshold_percentage}%).")

        return {
            "shot_count": eligible_count,
            "skipped_count": skipped_count,
            "total_evaluated": total_evaluated,
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
        """Genuinely bounded, streaming batch execution with atomic savepoints and truthful audits.

        Evaluates -> persists BatchRunItems -> dispatches per bounded chunk.
        Does not accumulate full-project candidate lists in memory.
        Enforces atomic GenerationJob + UsageLedger + BatchRunItem persistence.
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
        eff_provider = provider_name or ProviderFactory.get_default_provider_name()
        now = datetime.now(timezone.utc)

        # 1. Prefetch scenes and active locks
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

        locks = (
            db.query(AssetLock)
            .filter(
                AssetLock.project_id == project_id,
                AssetLock.is_locked == True,  # noqa: E712
            )
            .all()
        )
        locked_shot_ids = {l.entity_id for l in locks if l.entity_type == "SHOT"}
        locked_scene_ids = {l.entity_id for l in locks if l.entity_type == "SCENE"}
        locked_story_ids = {l.entity_id for l in locks if l.entity_type == "SCRIPT"}

        # 2. Create BatchRun record immediately so items can link cleanly
        batch_run = BatchRun(
            id=uuid.uuid4(),
            project_id=project_id,
            operation_type=op_enum.value,
            status="DISPATCHED",
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
        db.commit()

        total_evaluated = 0
        eligible_count = 0
        queued_count = 0
        skipped_count = 0
        dispatch_failed_count = 0
        has_dispatch_failure = False
        created_jobs: List[GenerationJob] = []

        # 3. Stream processing in chunks using immutable candidate shot ID snapshot
        if shot_ids is not None:
            candidate_shot_ids = list(dict.fromkeys(shot_ids))
        else:
            if all_scene_ids:
                candidate_shot_ids = [
                    row[0]
                    for row in (
                        db.query(Shot.id)
                        .join(Scene, Shot.scene_id == Scene.id)
                        .filter(Scene.id.in_(all_scene_ids))
                        .order_by(Scene.scene_number.asc(), Shot.shot_number.asc(), Shot.id.asc())
                        .all()
                    )
                ]
            else:
                candidate_shot_ids = []

        for i in range(0, len(candidate_shot_ids), EXECUTE_CHUNK_SIZE):
            chunk_req_ids = candidate_shot_ids[i:i + EXECUTE_CHUNK_SIZE]
            chunk_shots = (
                db.query(Shot)
                .filter(
                    Shot.scene_id.in_(all_scene_ids),
                    Shot.id.in_(chunk_req_ids),
                )
                .all()
            ) if all_scene_ids else []
            shots_by_id = {s.id: s for s in chunk_shots}

            job_rows = (
                db.query(GenerationJob.shot_id, GenerationJob.status)
                .filter(GenerationJob.shot_id.in_(chunk_req_ids))
                .all()
            )
            (
                shot_has_completed,
                shot_has_cancelling,
                shot_has_reconciliation,
                shot_has_active,
                shot_has_failed,
            ) = cls._categorize_job_rows(job_rows)

            for req_id in chunk_req_ids:
                total_evaluated += 1
                if req_id not in shots_by_id:
                    skipped_count += 1
                    db.add(BatchRunItem(
                        id=uuid.uuid4(),
                        batch_run_id=batch_run.id,
                        shot_id=req_id,
                        job_id=None,
                        decision="SKIPPED",
                        skip_reason=CandidateSkipReason.NOT_FOUND.value,
                        created_at=now,
                    ))
                    continue

                shot = shots_by_id[req_id]
                is_eligible, skip_reason = cls._evaluate_shot_decision(
                    shot=shot,
                    archived_scene_ids=archived_scene_ids,
                    scene_story_map=scene_story_map,
                    locked_shot_ids=locked_shot_ids,
                    locked_scene_ids=locked_scene_ids,
                    locked_story_ids=locked_story_ids,
                    shot_has_completed=shot_has_completed,
                    shot_has_cancelling=shot_has_cancelling,
                    shot_has_reconciliation=shot_has_reconciliation,
                    shot_has_active=shot_has_active,
                    shot_has_failed=shot_has_failed,
                    op_enum=op_enum,
                    only_incomplete=only_incomplete,
                )
                if not is_eligible:
                    skipped_count += 1
                    db.add(BatchRunItem(
                        id=uuid.uuid4(),
                        batch_run_id=batch_run.id,
                        shot_id=shot.id,
                        job_id=None,
                        decision="SKIPPED",
                        skip_reason=skip_reason.value if skip_reason else None,
                        created_at=now,
                    ))
                else:
                    eligible_count += 1
                    try:
                        with db.begin_nested():
                            job = JobDispatchService.create_and_dispatch_job(
                                db=db,
                                shot_id=shot.id,
                                provider_name=eff_provider,
                                lock_shot=True,
                                commit=False,
                            )
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
                            db.flush()
                        if len(created_jobs) < 100:
                            created_jobs.append(job)
                        queued_count += 1
                    except HTTPException as http_exc:
                        if http_exc.status_code == 409 and "Active generation job" in str(http_exc.detail):
                            skipped_count += 1
                            eligible_count -= 1
                            db.add(BatchRunItem(
                                id=uuid.uuid4(),
                                batch_run_id=batch_run.id,
                                shot_id=shot.id,
                                job_id=None,
                                decision="SKIPPED",
                                skip_reason=CandidateSkipReason.ACTIVE_JOB_EXISTS.value,
                                created_at=now,
                            ))
                        elif http_exc.status_code == 409 and "RECONCILIATION_REQUIRED" in str(http_exc.detail):
                            skipped_count += 1
                            eligible_count -= 1
                            db.add(BatchRunItem(
                                id=uuid.uuid4(),
                                batch_run_id=batch_run.id,
                                shot_id=shot.id,
                                job_id=None,
                                decision="SKIPPED",
                                skip_reason=CandidateSkipReason.RECONCILIATION_REQUIRED.value,
                                created_at=now,
                            ))
                        elif http_exc.status_code == 409 and "CANCELLING" in str(http_exc.detail):
                            skipped_count += 1
                            eligible_count -= 1
                            db.add(BatchRunItem(
                                id=uuid.uuid4(),
                                batch_run_id=batch_run.id,
                                shot_id=shot.id,
                                job_id=None,
                                decision="SKIPPED",
                                skip_reason=CandidateSkipReason.CANCELLATION_IN_PROGRESS.value,
                                created_at=now,
                            ))
                        else:
                            has_dispatch_failure = True
                            dispatch_failed_count += 1
                            err_msg = http_exc.detail if hasattr(http_exc, "detail") else str(http_exc)
                            db.add(BatchRunItem(
                                id=uuid.uuid4(),
                                batch_run_id=batch_run.id,
                                shot_id=shot.id,
                                job_id=None,
                                decision="FAILED",
                                skip_reason=str(err_msg)[:100],
                                created_at=now,
                            ))
                    except IntegrityError:
                        skipped_count += 1
                        eligible_count -= 1
                        db.add(BatchRunItem(
                            id=uuid.uuid4(),
                            batch_run_id=batch_run.id,
                            shot_id=shot.id,
                            job_id=None,
                            decision="SKIPPED",
                            skip_reason=CandidateSkipReason.ACTIVE_JOB_EXISTS.value,
                            created_at=now,
                        ))
                    except Exception as exc:
                        has_dispatch_failure = True
                        dispatch_failed_count += 1
                        db.add(BatchRunItem(
                            id=uuid.uuid4(),
                            batch_run_id=batch_run.id,
                            shot_id=shot.id,
                            job_id=None,
                            decision="FAILED",
                            skip_reason=str(exc)[:100],
                            created_at=now,
                        ))

            # Persist batch_run counters at every committed chunk boundary
            batch_run.requested_count = total_evaluated
            batch_run.eligible_count = eligible_count
            batch_run.queued_count = queued_count
            batch_run.skipped_count = skipped_count
            batch_run.failed_count = dispatch_failed_count
            batch_run.updated_at = datetime.now(timezone.utc)
            if has_dispatch_failure:
                batch_run.status = "PARTIAL_FAILED" if queued_count > 0 else "FAILED"
            else:
                batch_run.status = "DISPATCHED"
            db.commit()

        # 4. Finalize BatchRun totals and truthful status
        batch_run.requested_count = total_evaluated
        batch_run.eligible_count = eligible_count
        batch_run.queued_count = queued_count
        batch_run.skipped_count = skipped_count
        batch_run.failed_count = dispatch_failed_count
        if has_dispatch_failure:
            batch_run.status = "PARTIAL_FAILED" if queued_count > 0 else "FAILED"
        else:
            batch_run.status = "DISPATCHED"
        batch_run.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(batch_run)

        return batch_run, created_jobs

    @classmethod
    def reconcile_batch_run_counts(cls, db: Session, batch_run: BatchRun) -> BatchRun:
        """Dynamically derive truthful counters and lifecycle status from linked items and generation jobs."""
        stats = (
            db.query(
                func.count(BatchRunItem.id).label("total_items"),
                func.count().filter(BatchRunItem.decision == "QUEUED").label("queued_items"),
                func.count().filter(BatchRunItem.decision == "SKIPPED").label("skipped_items"),
                func.count().filter(BatchRunItem.decision == "FAILED").label("dispatch_failures"),
                func.count().filter(GenerationJob.status == "COMPLETED").label("completed_jobs"),
                func.count().filter(GenerationJob.status.in_(["FAILED", "RECONCILIATION_REQUIRED"])).label("failed_jobs"),
                func.count().filter(GenerationJob.status.in_(ACTIVE_JOB_STATUSES)).label("running_jobs"),
            )
            .outerjoin(GenerationJob, BatchRunItem.job_id == GenerationJob.id)
            .filter(BatchRunItem.batch_run_id == batch_run.id)
            .one()
        )
        total_items = stats.total_items or 0
        queued_items = stats.queued_items or 0
        skipped_items = stats.skipped_items or 0
        dispatch_failures = stats.dispatch_failures or 0
        completed_jobs = stats.completed_jobs or 0
        failed_jobs = stats.failed_jobs or 0
        running_jobs = stats.running_jobs or 0

        if total_items > 0:
            batch_run.requested_count = total_items
            batch_run.eligible_count = queued_items + dispatch_failures
            batch_run.queued_count = queued_items
            batch_run.skipped_count = skipped_items
            batch_run.completed_count = completed_jobs
            batch_run.failed_count = failed_jobs + dispatch_failures

            if queued_items == 0:
                batch_run.status = "FAILED" if dispatch_failures > 0 else "DISPATCHED"
            else:
                total_terminal = completed_jobs + failed_jobs
                has_failures = (failed_jobs + dispatch_failures) > 0
                if running_jobs > 0:
                    batch_run.status = "PARTIAL_FAILED" if has_failures else "RUNNING"
                elif total_terminal >= queued_items:
                    if completed_jobs == queued_items and not has_failures:
                        batch_run.status = "COMPLETED"
                    elif completed_jobs > 0 and has_failures:
                        batch_run.status = "PARTIAL_FAILED"
                    elif completed_jobs == 0 and has_failures:
                        batch_run.status = "FAILED"
                    else:
                        batch_run.status = "COMPLETED"
                else:
                    batch_run.status = "PARTIAL_FAILED" if has_failures else "DISPATCHED"

        return batch_run

    @classmethod
    def list_project_batch_runs(
        cls,
        db: Session,
        project_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> List[BatchRun]:
        """List batch runs with zero N+1 queries. Exactly 2 set-based queries executed."""
        runs = (
            db.query(BatchRun)
            .filter(BatchRun.project_id == project_id)
            .order_by(BatchRun.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        if not runs:
            return []

        run_ids = [r.id for r in runs]
        stats_rows = (
            db.query(
                BatchRunItem.batch_run_id,
                func.count(BatchRunItem.id).label("total_items"),
                func.count().filter(BatchRunItem.decision == "QUEUED").label("queued_items"),
                func.count().filter(BatchRunItem.decision == "SKIPPED").label("skipped_items"),
                func.count().filter(BatchRunItem.decision == "FAILED").label("dispatch_failures"),
                func.count().filter(GenerationJob.status == "COMPLETED").label("completed_jobs"),
                func.count().filter(GenerationJob.status.in_(["FAILED", "RECONCILIATION_REQUIRED"])).label("failed_jobs"),
                func.count().filter(GenerationJob.status.in_(ACTIVE_JOB_STATUSES)).label("running_jobs"),
            )
            .outerjoin(GenerationJob, BatchRunItem.job_id == GenerationJob.id)
            .filter(BatchRunItem.batch_run_id.in_(run_ids))
            .group_by(BatchRunItem.batch_run_id)
            .all()
        )
        stats_by_run = {
            row.batch_run_id: row
            for row in stats_rows
        }
        for r in runs:
            stats = stats_by_run.get(r.id)
            if stats and (stats.total_items or 0) > 0:
                total_items = stats.total_items or 0
                queued_items = stats.queued_items or 0
                skipped_items = stats.skipped_items or 0
                dispatch_failures = stats.dispatch_failures or 0
                completed_jobs = stats.completed_jobs or 0
                failed_jobs = stats.failed_jobs or 0
                running_jobs = stats.running_jobs or 0

                r.requested_count = total_items
                r.eligible_count = queued_items + dispatch_failures
                r.queued_count = queued_items
                r.skipped_count = skipped_items
                r.completed_count = completed_jobs
                r.failed_count = failed_jobs + dispatch_failures

                if queued_items == 0:
                    r.status = "FAILED" if dispatch_failures > 0 else "DISPATCHED"
                else:
                    total_terminal = completed_jobs + failed_jobs
                    has_failures = (failed_jobs + dispatch_failures) > 0
                    if running_jobs > 0:
                        r.status = "PARTIAL_FAILED" if has_failures else "RUNNING"
                    elif total_terminal >= queued_items:
                        if completed_jobs == queued_items and not has_failures:
                            r.status = "COMPLETED"
                        elif completed_jobs > 0 and has_failures:
                            r.status = "PARTIAL_FAILED"
                        elif completed_jobs == 0 and has_failures:
                            r.status = "FAILED"
                        else:
                            r.status = "COMPLETED"
                    else:
                        r.status = "PARTIAL_FAILED" if has_failures else "DISPATCHED"
        return runs

    @classmethod
    def get_batch_run_details(
        cls,
        db: Session,
        project_id: uuid.UUID,
        run_id: uuid.UUID,
        item_limit: int = 100,
        item_offset: int = 0,
    ) -> BatchRunDetailResponse:
        """Get single batch run with bounded item pagination without ORM collection mutation."""
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
        cls.reconcile_batch_run_counts(db, run)

        items_total = (
            db.query(func.count(BatchRunItem.id))
            .filter(BatchRunItem.batch_run_id == run_id)
            .scalar() or 0
        )
        bounded_items = (
            db.query(BatchRunItem)
            .filter(BatchRunItem.batch_run_id == run_id)
            .order_by(BatchRunItem.created_at.asc(), BatchRunItem.id.asc())
            .offset(item_offset)
            .limit(item_limit)
            .all()
        )
        return BatchRunDetailResponse(
            id=run.id,
            project_id=run.project_id,
            operation_type=run.operation_type,
            status=run.status,
            requested_count=run.requested_count,
            eligible_count=run.eligible_count,
            queued_count=run.queued_count,
            skipped_count=run.skipped_count,
            completed_count=run.completed_count,
            failed_count=run.failed_count,
            created_at=run.created_at,
            updated_at=run.updated_at,
            items=[BatchRunItemResponse.model_validate(it) for it in bounded_items],
            items_total=items_total,
            item_limit=item_limit,
            item_offset=item_offset,
        )
