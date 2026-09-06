import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from fastapi import HTTPException, status

from app.models.project import Project
from app.models.story import Story
from app.models.scene import Scene
from app.models.shot import Shot
from app.models.generation_job import GenerationJob
from app.models.batch_run import BatchRun, BatchRunItem
from app.models.orchestration_audit import OrchestrationAudit
from app.schemas.orchestrator import (
    AutomationMode,
    OrchestrationActionType,
    OrchestrationActionResult,
    OrchestrationActionModel,
    OrchestrationStateResponse,
    ExecuteActionResponse,
    ApproveStageResponse,
)
from app.services.job_dispatch import ALLOWED_PRODUCTION_STATUSES
from app.services.budget import BudgetService
from app.services.creative_generation.base import (
    CreativeGenerationProvider,
    CreativeGenerationError,
    GenerationRequestOptions,
)
from app.services.creative_generation.factory import get_creative_provider
from app.services.creative_generation.service import StoryGenerationService
from app.services.batch_resume import BatchResumeService

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

STAGE_DISPLAY_NAMES = {
    "DRAFT": "Draft & Setup",
    "STORY_GENERATED": "Story Outline Generated",
    "STORY_APPROVED": "Story Outline Approved",
    "STORYBOARD_GENERATED": "Storyboard Scenes Generated",
    "STORYBOARD_APPROVED": "Storyboard Approved",
    "SHOT_PLAN_GENERATED": "Shot Plan & Prompts Generated",
    "SHOT_PLAN_APPROVED": "Shot Plan Approved",
    "IMAGES_GENERATED": "Keyframe Images Generated",
    "VIDEO_IN_PROGRESS": "Video Generation In Progress",
    "FINAL_REVIEW": "Final Cut Review",
    "READY_FOR_REVIEW": "Final Cut Review",
    "APPROVED": "Production Approved",
    "COMPLETED": "Production Completed",
    "NEEDS_ATTENTION": "Needs Attention",
    "ARCHIVED": "Archived",
}

STAGE_DESCRIPTIONS = {
    "DRAFT": "Initial creative concept and project configuration.",
    "STORY_GENERATED": "Narrative outline and character brief generated. Requires editorial review.",
    "STORY_APPROVED": "Story outline is locked and approved. Ready to create storyboard scenes.",
    "STORYBOARD_GENERATED": "Storyboard scenes and narrative pacing generated. Requires review.",
    "STORYBOARD_APPROVED": "Storyboard structure is approved. Ready to plan detailed visual shots.",
    "SHOT_PLAN_GENERATED": "Detailed visual shot plans and AI prompts generated. Requires final review.",
    "SHOT_PLAN_APPROVED": "Shot plan is approved. Ready to dispatch video generation jobs.",
    "IMAGES_GENERATED": "Keyframe reference images generated and verified.",
    "VIDEO_IN_PROGRESS": "AI video generation jobs are actively processing in the provider queue.",
    "FINAL_REVIEW": "All video shots have completed generation. Inspect assembly for final approval.",
    "READY_FOR_REVIEW": "Ready for final production quality review.",
    "APPROVED": "Final video production cut has been approved.",
    "COMPLETED": "Project production is complete and ready for export.",
    "NEEDS_ATTENTION": "One or more generation jobs failed or require reconciliation.",
    "ARCHIVED": "Project is archived and read-only.",
}


def _resolve_creative_provider(
    provider: Optional[CreativeGenerationProvider] = None,
) -> CreativeGenerationProvider:
    if provider is not None:
        return provider
    return get_creative_provider()


class ProductionOrchestrator:
    """Canonical backend orchestrator owning production workflow state evaluation,
    allowed stage transitions, human approval gates, automation modes, and transition audits.
    """

    @classmethod
    def record_audit(
        cls,
        db: Session,
        project_id: uuid.UUID,
        from_state: str,
        to_state: Optional[str],
        action: str,
        actor: str = "USER",
        result: OrchestrationActionResult = OrchestrationActionResult.APPLIED,
        reason_code: Optional[str] = None,
        detail: Optional[str] = None,
    ) -> OrchestrationAudit:
        audit = OrchestrationAudit(
            id=uuid.uuid4(),
            project_id=project_id,
            from_state=from_state,
            to_state=to_state,
            action=action,
            actor=actor,
            result=result.value,
            reason_code=reason_code,
            detail=detail,
            created_at=datetime.now(timezone.utc),
        )
        db.add(audit)
        db.flush()
        return audit

    @classmethod
    def evaluate_state(cls, db: Session, project_id: uuid.UUID) -> OrchestrationStateResponse:
        project = db.get(Project, project_id)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project '{project_id}' not found",
            )

        video_mode = (project.video_mode or "STORY").upper()
        current_stage = project.status or "DRAFT"
        try:
            automation_mode = AutomationMode(getattr(project, "automation_mode", "MANUAL"))
        except ValueError:
            automation_mode = AutomationMode.MANUAL

        # 1. Bounded set-based aggregation queries (Zero per-shot N+1)
        story = db.query(Story).filter(Story.project_id == project_id).first()
        has_story = story is not None and bool(story.logline or story.synopsis or story.title)

        scene_count = (
            db.query(func.count(Scene.id))
            .filter(Scene.project_id == project_id)
            .scalar()
            or 0
        )
        if scene_count == 0 and story:
            scene_count = (
                db.query(func.count(Scene.id))
                .filter(Scene.story_id == story.id)
                .scalar()
                or 0
            )

        shot_count = (
            db.query(func.count(Shot.id))
            .join(Scene, Shot.scene_id == Scene.id)
            .filter(
                (Scene.project_id == project_id)
                | (Scene.story_id == (story.id if story else uuid.uuid4()))
            )
            .scalar()
            or 0
        )

        locked_shot_count = (
            db.query(func.count(Shot.id))
            .join(Scene, Shot.scene_id == Scene.id)
            .filter(
                (
                    (Scene.project_id == project_id)
                    | (Scene.story_id == (story.id if story else uuid.uuid4()))
                ),
                Shot.is_locked == True,
            )
            .scalar()
            or 0
        )

        job_counts_query = (
            db.query(GenerationJob.status, func.count(GenerationJob.id))
            .join(Shot, GenerationJob.shot_id == Shot.id)
            .join(Scene, Shot.scene_id == Scene.id)
            .filter(
                (Scene.project_id == project_id)
                | (Scene.story_id == (story.id if story else uuid.uuid4()))
            )
            .group_by(GenerationJob.status)
            .all()
        )
        job_counts: Dict[str, int] = {s: cnt for s, cnt in job_counts_query}

        active_jobs = sum(job_counts.get(s, 0) for s in ACTIVE_JOB_STATUSES)
        completed_jobs = job_counts.get("COMPLETED", 0)
        failed_jobs = job_counts.get("FAILED", 0)
        recon_jobs = job_counts.get("RECONCILIATION_REQUIRED", 0)

        # Check budget summary
        budget_summary = BudgetService.get_budget_status(db, project_id)
        hard_limit_exceeded = budget_summary.get("is_hard_limit_exceeded", False)
        threshold_exceeded = budget_summary.get("is_soft_limit_exceeded", False)

        blocked_reasons: List[str] = []
        is_blocked = False

        if hard_limit_exceeded:
            is_blocked = True
            blocked_reasons.append("Project hard budget limit exceeded. Generation dispatch is blocked.")

        if recon_jobs > 0:
            is_blocked = True
            blocked_reasons.append(f"{recon_jobs} job(s) require reconciliation before automatic workflow continuation.")

        if active_jobs > 0:
            is_blocked = True
            blocked_reasons.append(f"{active_jobs} active job(s) currently processing in queue.")

        if (
            current_stage == "SHOT_PLAN_APPROVED"
            and shot_count > 0
            and locked_shot_count == shot_count
            and completed_jobs < shot_count
        ):
            is_blocked = True
            blocked_reasons.append(f"All {shot_count} candidate shots are locked against generation.")

        # Stage truth: Never spoof effective_stage as FINAL_REVIEW when persisted status is still VIDEO_IN_PROGRESS!
        effective_stage = current_stage
        if current_stage not in ("COMPLETED", "APPROVED", "ARCHIVED"):
            if active_jobs > 0 and current_stage != "VIDEO_IN_PROGRESS":
                effective_stage = "VIDEO_IN_PROGRESS"
            elif recon_jobs > 0 and current_stage not in ALLOWED_PRODUCTION_STATUSES:
                effective_stage = "NEEDS_ATTENTION"

        is_approval_required = effective_stage in (
            "STORY_GENERATED",
            "STORYBOARD_GENERATED",
            "SHOT_PLAN_GENERATED",
            "FINAL_REVIEW",
            "READY_FOR_REVIEW",
        )

        # Compute Recommended Action and Available Actions
        recommended_action, available_actions = cls._compute_actions(
            video_mode=video_mode,
            current_stage=effective_stage,
            has_story=has_story,
            scene_count=scene_count,
            shot_count=shot_count,
            locked_shot_count=locked_shot_count,
            active_jobs=active_jobs,
            completed_jobs=completed_jobs,
            failed_jobs=failed_jobs,
            recon_jobs=recon_jobs,
            hard_limit_exceeded=hard_limit_exceeded,
        )

        stage_name = STAGE_DISPLAY_NAMES.get(effective_stage, effective_stage.replace("_", " ").title())
        stage_desc = STAGE_DESCRIPTIONS.get(effective_stage, "Production stage.")

        summary = {
            "has_story": has_story,
            "scene_count": scene_count,
            "shot_count": shot_count,
            "locked_shots": locked_shot_count,
            "active_jobs": active_jobs,
            "completed_jobs": completed_jobs,
            "failed_jobs": failed_jobs,
            "recon_jobs": recon_jobs,
            "hard_limit_exceeded": hard_limit_exceeded,
            "threshold_exceeded": threshold_exceeded,
            "budget_spent": budget_summary.get("total_committed_cost", 0.0),
            "budget_limit": budget_summary.get("budget_limit"),
        }

        return OrchestrationStateResponse(
            project_id=project_id,
            current_stage=effective_stage,
            video_mode=video_mode,
            automation_mode=automation_mode,
            stage_display_name=stage_name,
            stage_description=stage_desc,
            is_approval_required=is_approval_required,
            is_blocked=is_blocked,
            blocked_reasons=blocked_reasons,
            recommended_action=recommended_action,
            available_actions=available_actions,
            summary=summary,
        )

    @classmethod
    def _compute_actions(
        cls,
        video_mode: str,
        current_stage: str,
        has_story: bool,
        scene_count: int,
        shot_count: int,
        locked_shot_count: int,
        active_jobs: int,
        completed_jobs: int,
        failed_jobs: int,
        recon_jobs: int,
        hard_limit_exceeded: bool,
    ) -> Tuple[Optional[OrchestrationActionModel], List[OrchestrationActionModel]]:
        recommended: Optional[OrchestrationActionModel] = None
        available: List[OrchestrationActionModel] = []

        if current_stage == "ARCHIVED":
            return None, []

        if recon_jobs > 0:
            recommended = OrchestrationActionModel(
                action="RESOLVE_RECONCILIATION",
                display_name="Resolve Reconciliation Required Jobs",
                description="Investigate and reconcile in-flight jobs that lost provider synchronization.",
                action_type=OrchestrationActionType.RECOVERY,
                is_chargeable=False,
            )
            return recommended, available

        if current_stage in ("COMPLETED", "APPROVED"):
            recommended = OrchestrationActionModel(
                action="VIEW_SUMMARY",
                display_name="Production Complete",
                description="All production stages have been successfully approved and completed.",
                action_type=OrchestrationActionType.NAVIGATION,
                is_chargeable=False,
            )
            return recommended, available

        # ----------------- Mode: STORY -----------------
        if video_mode == "STORY":
            if current_stage == "DRAFT":
                if not has_story:
                    recommended = OrchestrationActionModel(
                        action="GENERATE_STORY",
                        display_name="Generate Story Outline",
                        description="Create initial narrative arc, character profiles, and scene outline.",
                        action_type=OrchestrationActionType.GENERATION,
                        is_chargeable=False,
                    )
                else:
                    # Story already exists; transition was not finalized or needs re-approval
                    recommended = OrchestrationActionModel(
                        action="APPROVE_STORY",
                        display_name="Approve Story Outline & Proceed",
                        description="Lock story narrative outline and proceed to storyboard generation.",
                        action_type=OrchestrationActionType.APPROVAL,
                        is_chargeable=False,
                        parameters={"stage": "STORY_GENERATED"},
                    )
                    available.append(OrchestrationActionModel(
                        action="REVISE_STORY",
                        display_name="Revise Story Outline",
                        description="Edit narrative prompt and regenerate outline.",
                        action_type=OrchestrationActionType.REVISION,
                    ))

            elif current_stage == "STORY_GENERATED":
                recommended = OrchestrationActionModel(
                    action="APPROVE_STORY",
                    display_name="Approve Story Outline & Proceed",
                    description="Lock story narrative outline and proceed to storyboard generation.",
                    action_type=OrchestrationActionType.APPROVAL,
                    is_chargeable=False,
                    parameters={"stage": "STORY_GENERATED"},
                )
                available.append(OrchestrationActionModel(
                    action="REVISE_STORY",
                    display_name="Revise Story Outline",
                    description="Edit narrative prompt and regenerate outline.",
                    action_type=OrchestrationActionType.REVISION,
                ))

            elif current_stage == "STORY_APPROVED":
                if scene_count == 0:
                    recommended = OrchestrationActionModel(
                        action="GENERATE_STORYBOARD",
                        display_name="Generate Storyboard Scenes",
                        description="Generate storyboard scenes from the approved story outline.",
                        action_type=OrchestrationActionType.GENERATION,
                        is_chargeable=False,
                    )
                else:
                    recommended = OrchestrationActionModel(
                        action="APPROVE_STORYBOARD",
                        display_name="Approve Storyboard & Proceed",
                        description="Lock storyboard scenes and proceed to detailed shot planning.",
                        action_type=OrchestrationActionType.APPROVAL,
                        is_chargeable=False,
                        parameters={"stage": "STORYBOARD_GENERATED"},
                    )
                    available.append(OrchestrationActionModel(
                        action="REVISE_STORYBOARD",
                        display_name="Revise Storyboard",
                        description="Modify scene headings and descriptions.",
                        action_type=OrchestrationActionType.REVISION,
                    ))

            elif current_stage == "STORYBOARD_GENERATED":
                recommended = OrchestrationActionModel(
                    action="APPROVE_STORYBOARD",
                    display_name="Approve Storyboard & Proceed",
                    description="Lock storyboard scenes and proceed to detailed shot planning.",
                    action_type=OrchestrationActionType.APPROVAL,
                    is_chargeable=False,
                    parameters={"stage": "STORYBOARD_GENERATED"},
                )
                available.append(OrchestrationActionModel(
                    action="REVISE_STORYBOARD",
                    display_name="Revise Storyboard",
                    description="Modify scene headings and descriptions.",
                    action_type=OrchestrationActionType.REVISION,
                ))

            elif current_stage == "STORYBOARD_APPROVED":
                if shot_count == 0:
                    recommended = OrchestrationActionModel(
                        action="GENERATE_SHOT_PLAN",
                        display_name="Generate Shot Plan & Prompts",
                        description="Generate camera shots, durations, and AI visual prompts.",
                        action_type=OrchestrationActionType.GENERATION,
                        is_chargeable=False,
                    )
                else:
                    recommended = OrchestrationActionModel(
                        action="APPROVE_SHOT_PLAN",
                        display_name="Approve Shot Plan & Proceed",
                        description="Lock visual shot plans and AI prompts for production video generation.",
                        action_type=OrchestrationActionType.APPROVAL,
                        is_chargeable=False,
                        parameters={"stage": "SHOT_PLAN_GENERATED"},
                    )
                    available.append(OrchestrationActionModel(
                        action="REVISE_SHOT_PLAN",
                        display_name="Revise Shot Plan",
                        description="Edit shot prompts, camera angles, or durations.",
                        action_type=OrchestrationActionType.REVISION,
                    ))

            elif current_stage == "SHOT_PLAN_GENERATED":
                recommended = OrchestrationActionModel(
                    action="APPROVE_SHOT_PLAN",
                    display_name="Approve Shot Plan & Proceed",
                    description="Lock visual shot plans and AI prompts for production video generation.",
                    action_type=OrchestrationActionType.APPROVAL,
                    is_chargeable=False,
                    parameters={"stage": "SHOT_PLAN_GENERATED"},
                )
                available.append(OrchestrationActionModel(
                    action="REVISE_SHOT_PLAN",
                    display_name="Revise Shot Plan",
                    description="Edit shot prompts, camera angles, or durations.",
                    action_type=OrchestrationActionType.REVISION,
                ))

        # ----------------- Modes: SHORT & SCENE (No Story outline) -----------------
        elif video_mode in ("SHORT", "SCENE"):
            if current_stage == "DRAFT":
                if scene_count == 0:
                    recommended = OrchestrationActionModel(
                        action="GENERATE_STORYBOARD",
                        display_name="Create Storyboard Scenes",
                        description="Initialize scene structure for short-form production.",
                        action_type=OrchestrationActionType.GENERATION,
                        is_chargeable=False,
                    )
                else:
                    recommended = OrchestrationActionModel(
                        action="APPROVE_STORYBOARD",
                        display_name="Approve Storyboard & Proceed",
                        description="Approve scenes and proceed to shot planning.",
                        action_type=OrchestrationActionType.APPROVAL,
                        is_chargeable=False,
                        parameters={"stage": "STORYBOARD_GENERATED"},
                    )
            elif current_stage == "STORYBOARD_GENERATED":
                recommended = OrchestrationActionModel(
                    action="APPROVE_STORYBOARD",
                    display_name="Approve Storyboard & Proceed",
                    description="Approve scenes and proceed to shot planning.",
                    action_type=OrchestrationActionType.APPROVAL,
                    is_chargeable=False,
                    parameters={"stage": "STORYBOARD_GENERATED"},
                )
            elif current_stage == "STORYBOARD_APPROVED":
                if shot_count == 0:
                    recommended = OrchestrationActionModel(
                        action="GENERATE_SHOT_PLAN",
                        display_name="Generate Shot Plan & Prompts",
                        description="Generate camera shots and AI prompts for scenes.",
                        action_type=OrchestrationActionType.GENERATION,
                        is_chargeable=False,
                    )
                else:
                    recommended = OrchestrationActionModel(
                        action="APPROVE_SHOT_PLAN",
                        display_name="Approve Shot Plan & Proceed",
                        description="Approve shot plan and proceed to video generation.",
                        action_type=OrchestrationActionType.APPROVAL,
                        is_chargeable=False,
                        parameters={"stage": "SHOT_PLAN_GENERATED"},
                    )
            elif current_stage == "SHOT_PLAN_GENERATED":
                recommended = OrchestrationActionModel(
                    action="APPROVE_SHOT_PLAN",
                    display_name="Approve Shot Plan & Proceed",
                    description="Approve shot plan and proceed to video generation.",
                    action_type=OrchestrationActionType.APPROVAL,
                    is_chargeable=False,
                    parameters={"stage": "SHOT_PLAN_GENERATED"},
                )

        # ----------------- Mode: LOOP (No Story or Scene outline) -----------------
        elif video_mode == "LOOP":
            if current_stage == "DRAFT":
                recommended = OrchestrationActionModel(
                    action="GENERATE_SHOT_PLAN",
                    display_name="Configure Loop Shot Plan",
                    description="Set up loop shot duration and seamless visual prompt.",
                    action_type=OrchestrationActionType.GENERATION,
                    is_chargeable=False,
                )
            elif current_stage == "SHOT_PLAN_GENERATED":
                recommended = OrchestrationActionModel(
                    action="APPROVE_SHOT_PLAN",
                    display_name="Approve Loop Shot Plan & Proceed",
                    description="Approve loop parameters and proceed to generation.",
                    action_type=OrchestrationActionType.APPROVAL,
                    is_chargeable=False,
                    parameters={"stage": "SHOT_PLAN_GENERATED"},
                )

        # ----------------- Downstream Stages (All modes) -----------------
        if current_stage == "SHOT_PLAN_APPROVED":
            all_locked = shot_count > 0 and locked_shot_count == shot_count
            is_gen_blocked = hard_limit_exceeded or all_locked
            blocked_msg = "Hard budget limit exceeded" if hard_limit_exceeded else (
                "All candidate shots are locked" if all_locked else None
            )

            recommended = OrchestrationActionModel(
                action="START_VIDEO_GENERATION",
                display_name="Start Video Generation",
                description="Dispatch eligible AI video generation jobs to the provider queue.",
                action_type=OrchestrationActionType.GENERATION,
                is_chargeable=True,
                is_blocked=is_gen_blocked,
                blocked_reason=blocked_msg,
            )
            available.append(OrchestrationActionModel(
                action="GENERATE_SELECTED_SHOTS",
                display_name="Generate Selected Shots",
                description="Dispatch selected shots only.",
                action_type=OrchestrationActionType.GENERATION,
                is_chargeable=True,
                is_blocked=is_gen_blocked,
            ))
            available.append(OrchestrationActionModel(
                action="REVISE_SHOT_PLAN",
                display_name="Revise Shot Plan",
                description="Make adjustments to shot prompts or camera instructions.",
                action_type=OrchestrationActionType.REVISION,
            ))

        elif current_stage == "VIDEO_IN_PROGRESS":
            if active_jobs > 0:
                recommended = OrchestrationActionModel(
                    action="POLL_STATUS",
                    display_name="Monitor Active Generation Jobs",
                    description=f"{active_jobs} job(s) actively processing in queue.",
                    action_type=OrchestrationActionType.NAVIGATION,
                    is_chargeable=False,
                )
            elif shot_count > 0 and completed_jobs >= shot_count:
                recommended = OrchestrationActionModel(
                    action="TRANSITION_TO_FINAL_REVIEW",
                    display_name="Proceed to Final Review",
                    description="All shots generated successfully. Inspect final cut assembly.",
                    action_type=OrchestrationActionType.APPROVAL,
                    is_chargeable=False,
                )
            elif failed_jobs > 0:
                recommended = OrchestrationActionModel(
                    action="RETRY_FAILED",
                    display_name="Retry Failed Jobs",
                    description=f"Retry {failed_jobs} failed generation job(s).",
                    action_type=OrchestrationActionType.RECOVERY,
                    is_chargeable=True,
                    is_blocked=hard_limit_exceeded,
                )
            elif completed_jobs < shot_count:
                recommended = OrchestrationActionModel(
                    action="CONTINUE_INCOMPLETE",
                    display_name="Continue Incomplete Generation",
                    description="Dispatch remaining ungenerated shots.",
                    action_type=OrchestrationActionType.GENERATION,
                    is_chargeable=True,
                    is_blocked=hard_limit_exceeded,
                )

        elif current_stage in ("FINAL_REVIEW", "READY_FOR_REVIEW"):
            recommended = OrchestrationActionModel(
                action="APPROVE_FINAL",
                display_name="Approve Final Cut & Complete Project",
                description="Approve assembly and mark project completed.",
                action_type=OrchestrationActionType.APPROVAL,
                is_chargeable=False,
                parameters={"stage": "FINAL_REVIEW"},
            )
            if failed_jobs > 0:
                available.append(OrchestrationActionModel(
                    action="RETRY_FAILED",
                    display_name="Retry Failed Jobs",
                    description="Retry failed shots.",
                    action_type=OrchestrationActionType.RECOVERY,
                    is_chargeable=True,
                ))
            if completed_jobs < shot_count:
                available.append(OrchestrationActionModel(
                    action="CONTINUE_INCOMPLETE",
                    display_name="Generate Incomplete Shots",
                    description="Complete remaining shots.",
                    action_type=OrchestrationActionType.GENERATION,
                    is_chargeable=True,
                ))

        return recommended, available

    @classmethod
    def approve_stage(
        cls,
        db: Session,
        project_id: uuid.UUID,
        stage: Optional[str] = None,
        notes: Optional[str] = None,
        actor: str = "USER",
        provider: Optional[CreativeGenerationProvider] = None,
    ) -> ApproveStageResponse:
        project = db.get(Project, project_id)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project '{project_id}' not found",
            )

        video_mode = (project.video_mode or "STORY").upper()
        current = project.status or "DRAFT"

        # Canonical mapping of current gate awaiting human approval -> target approved stage
        approval_map = {
            "STORY_GENERATED": "STORY_APPROVED",
            "STORYBOARD_GENERATED": "STORYBOARD_APPROVED",
            "SHOT_PLAN_GENERATED": "SHOT_PLAN_APPROVED",
            "FINAL_REVIEW": "COMPLETED",
            "READY_FOR_REVIEW": "COMPLETED",
        }

        # Strict fail-closed check: No approving from DRAFT or non-approval stages!
        target_stage = approval_map.get(current)

        # Idempotency check: if current stage is already the approved target stage
        if stage:
            resolved_target = approval_map.get(stage, stage)
            if current == resolved_target:
                cls.record_audit(
                    db=db,
                    project_id=project_id,
                    from_state=current,
                    to_state=current,
                    action=f"APPROVE_{stage}",
                    actor=actor,
                    result=OrchestrationActionResult.NO_OP,
                    reason_code="ALREADY_IN_TARGET_STAGE",
                    detail=notes,
                )
                db.commit()
                updated_state = cls.evaluate_state(db, project_id)
                return ApproveStageResponse(
                    success=True,
                    from_stage=current,
                    to_stage=current,
                    result=OrchestrationActionResult.NO_OP,
                    message=f"Stage '{current}' is already approved.",
                    orchestration_state=updated_state,
                )

        if not target_stage:
            cls.record_audit(
                db=db,
                project_id=project_id,
                from_state=current,
                to_state=current,
                action="APPROVE_STAGE",
                actor=actor,
                result=OrchestrationActionResult.BLOCKED,
                reason_code="INVALID_STAGE_APPROVAL",
                detail=f"Stage '{current}' cannot be approved directly.",
            )
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Current stage '{current}' is not awaiting human approval. Expected approval states: {list(approval_map.keys())}",
            )

        # Ensure requested stage strictly matches current waiting gate
        if stage and stage != target_stage and stage != current:
            cls.record_audit(
                db=db,
                project_id=project_id,
                from_state=current,
                to_state=current,
                action=f"APPROVE_{stage}",
                actor=actor,
                result=OrchestrationActionResult.BLOCKED,
                reason_code="OUT_OF_ORDER_APPROVAL",
                detail=f"Requested stage '{stage}' does not match next valid approved stage '{target_stage}'.",
            )
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Out of order approval: cannot transition from '{current}' to '{stage}'. Next valid approval target is '{target_stage}'.",
            )

        # Apply approval
        project.status = target_stage
        cls.record_audit(
            db=db,
            project_id=project_id,
            from_state=current,
            to_state=target_stage,
            action=f"APPROVE_{target_stage}",
            actor=actor,
            result=OrchestrationActionResult.APPLIED,
            reason_code="APPROVAL_GRANTED",
            detail=notes,
        )
        db.commit()

        # Real AUTO mode behavior:
        # Automatically cascade safe, non-chargeable creative planning steps,
        # but ALWAYS STOP at mandatory human review gates, budget limits, or chargeable video generation gates.
        auto_mode = getattr(project, "automation_mode", "MANUAL")
        if auto_mode == "AUTO":
            if target_stage == "STORY_APPROVED":
                # Safe auto-cascade to GENERATE_STORYBOARD
                cls.execute_action(
                    db=db,
                    project_id=project_id,
                    action="GENERATE_STORYBOARD",
                    actor="AUTO",
                    provider=provider,
                )
            elif target_stage == "STORYBOARD_APPROVED":
                # Safe auto-cascade to GENERATE_SHOT_PLAN
                cls.execute_action(
                    db=db,
                    project_id=project_id,
                    action="GENERATE_SHOT_PLAN",
                    actor="AUTO",
                    provider=provider,
                )
            elif target_stage == "SHOT_PLAN_APPROVED":
                # Mandatory STOP: Chargeable video generation gate requires human confirmation!
                pass

        updated_state = cls.evaluate_state(db, project_id)
        return ApproveStageResponse(
            success=True,
            from_stage=current,
            to_stage=project.status,
            result=OrchestrationActionResult.APPLIED,
            message=f"Stage successfully approved: transitioned to '{project.status}'.",
            orchestration_state=updated_state,
        )

    @classmethod
    def execute_action(
        cls,
        db: Session,
        project_id: uuid.UUID,
        action: str,
        parameters: Optional[Dict[str, Any]] = None,
        actor: str = "USER",
        provider: Optional[CreativeGenerationProvider] = None,
    ) -> ExecuteActionResponse:
        project = db.get(Project, project_id)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project '{project_id}' not found",
            )

        current = project.status or "DRAFT"
        video_mode = (project.video_mode or "STORY").upper()
        params = parameters or {}
        action_upper = action.upper()

        creative_prov = _resolve_creative_provider(provider)

        # ----------------- Canonical Approval Actions -----------------
        if action_upper in ("APPROVE_STORY", "APPROVE_STORYBOARD", "APPROVE_SHOT_PLAN", "APPROVE_FINAL"):
            # Enforce gate matching for approval actions
            expected_current = {
                "APPROVE_STORY": ("STORY_GENERATED", "STORY_APPROVED"),
                "APPROVE_STORYBOARD": ("STORYBOARD_GENERATED", "STORYBOARD_APPROVED"),
                "APPROVE_SHOT_PLAN": ("SHOT_PLAN_GENERATED", "SHOT_PLAN_APPROVED"),
                "APPROVE_FINAL": ("FINAL_REVIEW", "READY_FOR_REVIEW", "COMPLETED"),
            }
            allowed_stages = expected_current[action_upper]
            if current not in allowed_stages:
                cls.record_audit(
                    db=db,
                    project_id=project_id,
                    from_state=current,
                    to_state=current,
                    action=action_upper,
                    actor=actor,
                    result=OrchestrationActionResult.BLOCKED,
                    reason_code="INVALID_STAGE_APPROVAL",
                    detail=f"Action '{action_upper}' is not valid at stage '{current}'.",
                )
                db.commit()
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Action '{action_upper}' is not valid at stage '{current}'. Expected stage: {allowed_stages[0]}.",
                )

            # Route to approve_stage
            target_stage_for_action = {
                "APPROVE_STORY": "STORY_APPROVED",
                "APPROVE_STORYBOARD": "STORYBOARD_APPROVED",
                "APPROVE_SHOT_PLAN": "SHOT_PLAN_APPROVED",
                "APPROVE_FINAL": "COMPLETED",
            }[action_upper]

            approval_res = cls.approve_stage(
                db=db,
                project_id=project_id,
                stage=target_stage_for_action,
                notes=params.get("notes"),
                actor=actor,
                provider=creative_prov,
            )
            return ExecuteActionResponse(
                success=approval_res.success,
                action=action_upper,
                from_stage=approval_res.from_stage,
                to_stage=approval_res.to_stage,
                result=approval_res.result,
                message=approval_res.message,
                orchestration_state=approval_res.orchestration_state,
            )

        # ----------------- 1. Action: GENERATE_STORY -----------------
        if action_upper == "GENERATE_STORY":
            if video_mode != "STORY":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Story generation is only available in STORY mode, current mode is '{video_mode}'.",
                )
            if current not in ("DRAFT", "STORY_GENERATED"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cannot generate story at stage '{current}'.",
                )

            # Real generation service dispatch
            story_svc = StoryGenerationService(db=db, provider=creative_prov)
            try:
                story = story_svc.generate_project_story(
                    project_id=project_id,
                    target_duration_seconds=params.get("target_duration_seconds", project.target_duration_seconds or 60.0),
                    tone=params.get("tone", "cinematic"),
                    language=params.get("language", "th"),
                    custom_instructions=params.get("custom_instructions"),
                    generate_scenes=False,
                )
            except CreativeGenerationError as e:
                cls.record_audit(
                    db=db,
                    project_id=project_id,
                    from_state=current,
                    to_state=current,
                    action=action_upper,
                    actor=actor,
                    result=OrchestrationActionResult.BLOCKED,
                    reason_code=e.code,
                    detail=e.message,
                )
                db.commit()
                status_code = (
                    status.HTTP_400_BAD_REQUEST
                    if e.code in ("NO_SOURCE_CONTEXT", "SOURCE_EXTRACTION_NOT_READY")
                    else status.HTTP_409_CONFLICT
                )
                raise HTTPException(status_code=status_code, detail=e.message)

            # Verify artifact was created successfully
            if not story or not story.id:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Story generation service did not create a valid Story entity.",
                )

            project.status = "STORY_GENERATED"
            cls.record_audit(
                db=db,
                project_id=project_id,
                from_state=current,
                to_state="STORY_GENERATED",
                action="GENERATE_STORY",
                actor=actor,
                result=OrchestrationActionResult.APPLIED,
                detail=f"Story {story.id} generated successfully.",
            )
            db.commit()

        # ----------------- 2. Action: GENERATE_STORYBOARD -----------------
        elif action_upper == "GENERATE_STORYBOARD":
            story_svc = StoryGenerationService(db=db, provider=creative_prov)
            created_scenes: List[Scene] = []

            if video_mode == "STORY":
                if current not in ("STORY_APPROVED", "STORYBOARD_GENERATED"):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Story outline must be approved before generating storyboard. Current stage is '{current}'.",
                    )
                story = db.query(Story).filter(Story.project_id == project_id).first()
                if not story:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="No Story entity found for project in STORY mode. Generate and approve Story first.",
                    )
                try:
                    created_scenes = story_svc.generate_story_scenes(
                        story_id=story.id,
                        custom_instructions=params.get("custom_instructions"),
                        generate_shots=False,
                    )
                except CreativeGenerationError as e:
                    cls.record_audit(
                        db=db,
                        project_id=project_id,
                        from_state=current,
                        to_state=current,
                        action=action_upper,
                        actor=actor,
                        result=OrchestrationActionResult.BLOCKED,
                        reason_code=e.code,
                        detail=e.message,
                    )
                    db.commit()
                    raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=e.message)

            elif video_mode in ("SHORT", "SCENE"):
                if current not in ("DRAFT", "STORYBOARD_GENERATED"):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Cannot generate storyboard at stage '{current}'.",
                    )
                try:
                    created_scenes = story_svc.generate_project_storyboard(
                        project_id=project_id,
                        custom_instructions=params.get("custom_instructions"),
                        generate_shots=False,
                    )
                except CreativeGenerationError as e:
                    cls.record_audit(
                        db=db,
                        project_id=project_id,
                        from_state=current,
                        to_state=current,
                        action=action_upper,
                        actor=actor,
                        result=OrchestrationActionResult.BLOCKED,
                        reason_code=e.code,
                        detail=e.message,
                    )
                    db.commit()
                    raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=e.message)

            elif video_mode == "LOOP":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Storyboard generation is not applicable in LOOP mode. Use GENERATE_SHOT_PLAN.",
                )

            # Verify artifact was created successfully
            if not created_scenes:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Storyboard generation did not create any Scene entities.",
                )

            project.status = "STORYBOARD_GENERATED"
            cls.record_audit(
                db=db,
                project_id=project_id,
                from_state=current,
                to_state="STORYBOARD_GENERATED",
                action="GENERATE_STORYBOARD",
                actor=actor,
                result=OrchestrationActionResult.APPLIED,
                detail=f"Generated {len(created_scenes)} storyboard scene(s).",
            )
            db.commit()

        # ----------------- 3. Action: GENERATE_SHOT_PLAN -----------------
        elif action_upper == "GENERATE_SHOT_PLAN":
            story_svc = StoryGenerationService(db=db, provider=creative_prov)
            created_shots: List[Shot] = []

            if video_mode in ("STORY", "SHORT", "SCENE"):
                if current not in ("STORYBOARD_APPROVED", "SHOT_PLAN_GENERATED"):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Storyboard must be approved before generating shot plans. Current stage is '{current}'.",
                    )
                # Find active scenes for project
                story = db.query(Story).filter(Story.project_id == project_id).first()
                active_scenes = (
                    db.query(Scene)
                    .filter(
                        (Scene.project_id == project_id)
                        | (Scene.story_id == (story.id if story else uuid.uuid4()))
                    )
                    .all()
                )
                active_scenes = [
                    s for s in active_scenes if not (s.scene_config or {}).get("archived")
                ]
                if not active_scenes:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="No active storyboard scenes found to generate shot plans from.",
                    )
                try:
                    for scene in active_scenes:
                        s_shots = story_svc.generate_scene_shots(
                            scene_id=scene.id,
                            custom_instructions=params.get("custom_instructions"),
                        )
                        created_shots.extend(s_shots)
                except CreativeGenerationError as e:
                    cls.record_audit(
                        db=db,
                        project_id=project_id,
                        from_state=current,
                        to_state=current,
                        action=action_upper,
                        actor=actor,
                        result=OrchestrationActionResult.BLOCKED,
                        reason_code=e.code,
                        detail=e.message,
                    )
                    db.commit()
                    raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=e.message)

            elif video_mode == "LOOP":
                if current not in ("DRAFT", "SHOT_PLAN_GENERATED"):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Cannot generate loop shot plan from stage '{current}'.",
                    )
                # In LOOP mode, create default loop scene if none exists
                loop_scene = (
                    db.query(Scene)
                    .filter(Scene.project_id == project_id)
                    .first()
                )
                if not loop_scene:
                    loop_scene = Scene(
                        id=uuid.uuid4(),
                        project_id=project_id,
                        scene_number=1,
                        heading="Seamless Loop",
                        purpose="LOOP",
                        setting=project.description or "Seamless loop setting",
                        duration_seconds=project.target_duration_seconds or 4.0,
                    )
                    db.add(loop_scene)
                    db.flush()
                try:
                    created_shots = story_svc.generate_scene_shots(
                        scene_id=loop_scene.id,
                        custom_instructions=params.get("custom_instructions"),
                    )
                except CreativeGenerationError as e:
                    cls.record_audit(
                        db=db,
                        project_id=project_id,
                        from_state=current,
                        to_state=current,
                        action=action_upper,
                        actor=actor,
                        result=OrchestrationActionResult.BLOCKED,
                        reason_code=e.code,
                        detail=e.message,
                    )
                    db.commit()
                    raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=e.message)

            # Verify artifact was created successfully
            if not created_shots:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Shot plan generation did not create any Shot entities.",
                )

            project.status = "SHOT_PLAN_GENERATED"
            cls.record_audit(
                db=db,
                project_id=project_id,
                from_state=current,
                to_state="SHOT_PLAN_GENERATED",
                action="GENERATE_SHOT_PLAN",
                actor=actor,
                result=OrchestrationActionResult.APPLIED,
                detail=f"Generated {len(created_shots)} shot plan(s).",
            )
            db.commit()

        # ----------------- 4. Action: START_VIDEO_GENERATION / CONTINUE_INCOMPLETE -----------------
        elif action_upper in ("START_VIDEO_GENERATION", "CONTINUE_INCOMPLETE"):
            if current not in ALLOWED_PRODUCTION_STATUSES:
                cls.record_audit(
                    db=db,
                    project_id=project_id,
                    from_state=current,
                    to_state=current,
                    action=action_upper,
                    actor=actor,
                    result=OrchestrationActionResult.BLOCKED,
                    reason_code="STAGE_NOT_APPROVED",
                    detail=f"Video generation requires 'SHOT_PLAN_APPROVED' stage, current status is '{current}'.",
                )
                db.commit()
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Production generation requires 'SHOT_PLAN_APPROVED' stage, current project status is '{current}'.",
                )

            # Check budget hard limit
            b_summary = BudgetService.get_budget_status(db, project_id)
            if b_summary.get("is_hard_limit_exceeded"):
                cls.record_audit(
                    db=db,
                    project_id=project_id,
                    from_state=current,
                    to_state=current,
                    action=action_upper,
                    actor=actor,
                    result=OrchestrationActionResult.BLOCKED,
                    reason_code="HARD_BUDGET_LIMIT_EXCEEDED",
                )
                db.commit()
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Project hard budget limit exceeded. Generation dispatch is blocked.",
                )

            batch_run, _ = BatchResumeService.execute_batch(
                db=db,
                project_id=project_id,
                operation_type="CONTINUE_INCOMPLETE",
                max_queued_jobs=None,
                accumulate_jobs=False,
            )

            if batch_run.queued_count == 0:
                # Truthful locked / blocked / no-op handling
                skipped_items = (
                    db.query(BatchRunItem.skip_reason, func.count(BatchRunItem.id))
                    .filter(BatchRunItem.batch_run_id == batch_run.id)
                    .group_by(BatchRunItem.skip_reason)
                    .all()
                )
                skip_summary = {reason: count for reason, count in skipped_items}
                has_locked = skip_summary.get("LOCKED", 0) > 0
                reason_code = "ALL_CANDIDATES_LOCKED" if has_locked else "ALL_CANDIDATES_SKIPPED"
                result_status = (
                    OrchestrationActionResult.BLOCKED if has_locked else OrchestrationActionResult.NO_OP
                )

                cls.record_audit(
                    db=db,
                    project_id=project_id,
                    from_state=current,
                    to_state=current,
                    action=action_upper,
                    actor=actor,
                    result=result_status,
                    reason_code=reason_code,
                    detail=f"BatchRun {batch_run.id} queued 0 jobs; skipped={batch_run.skipped_count} (skip details: {skip_summary})",
                )
                db.commit()
                updated_state = cls.evaluate_state(db, project_id)
                return ExecuteActionResponse(
                    success=True,
                    action=action_upper,
                    from_stage=current,
                    to_stage=current,
                    result=result_status,
                    message=f"No jobs dispatched: {batch_run.skipped_count} shot(s) skipped (details: {skip_summary}).",
                    orchestration_state=updated_state,
                )

            project.status = "VIDEO_IN_PROGRESS"
            cls.record_audit(
                db=db,
                project_id=project_id,
                from_state=current,
                to_state="VIDEO_IN_PROGRESS",
                action=action_upper,
                actor=actor,
                result=OrchestrationActionResult.APPLIED,
                detail=f"Dispatched BatchRun {batch_run.id} with queued_count={batch_run.queued_count}",
            )
            db.commit()

        # ----------------- 5. Action: GENERATE_SELECTED_SHOTS -----------------
        elif action_upper == "GENERATE_SELECTED_SHOTS":
            if current not in ALLOWED_PRODUCTION_STATUSES:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Production generation requires 'SHOT_PLAN_APPROVED' stage, current status is '{current}'.",
                )
            shot_ids = params.get("shot_ids")
            if not shot_ids:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Parameter 'shot_ids' is required for GENERATE_SELECTED_SHOTS.",
                )
            parsed_ids = [uuid.UUID(str(s)) for s in shot_ids]
            batch_run, _ = BatchResumeService.execute_batch(
                db=db,
                project_id=project_id,
                operation_type="GENERATE_SELECTED",
                shot_ids=parsed_ids,
                max_queued_jobs=None,
                accumulate_jobs=False,
            )

            if batch_run.queued_count == 0:
                skipped_items = (
                    db.query(BatchRunItem.skip_reason, func.count(BatchRunItem.id))
                    .filter(BatchRunItem.batch_run_id == batch_run.id)
                    .group_by(BatchRunItem.skip_reason)
                    .all()
                )
                skip_summary = {reason: count for reason, count in skipped_items}
                has_locked = skip_summary.get("LOCKED", 0) > 0
                reason_code = "ALL_CANDIDATES_LOCKED" if has_locked else "ALL_CANDIDATES_SKIPPED"
                result_status = (
                    OrchestrationActionResult.BLOCKED if has_locked else OrchestrationActionResult.NO_OP
                )

                cls.record_audit(
                    db=db,
                    project_id=project_id,
                    from_state=current,
                    to_state=current,
                    action=action_upper,
                    actor=actor,
                    result=result_status,
                    reason_code=reason_code,
                    detail=f"BatchRun {batch_run.id} queued 0 jobs; skipped={batch_run.skipped_count} (skip details: {skip_summary})",
                )
                db.commit()
                updated_state = cls.evaluate_state(db, project_id)
                return ExecuteActionResponse(
                    success=True,
                    action=action_upper,
                    from_stage=current,
                    to_stage=current,
                    result=result_status,
                    message=f"No jobs dispatched: {batch_run.skipped_count} selected shot(s) skipped (details: {skip_summary}).",
                    orchestration_state=updated_state,
                )

            project.status = "VIDEO_IN_PROGRESS"
            cls.record_audit(
                db=db,
                project_id=project_id,
                from_state=current,
                to_state="VIDEO_IN_PROGRESS",
                action=action_upper,
                actor=actor,
                result=OrchestrationActionResult.APPLIED,
                detail=f"Dispatched BatchRun {batch_run.id} for selected shots with queued_count={batch_run.queued_count}",
            )
            db.commit()

        # ----------------- 6. Action: RETRY_FAILED -----------------
        elif action_upper == "RETRY_FAILED":
            batch_run, _ = BatchResumeService.execute_batch(
                db=db,
                project_id=project_id,
                operation_type="RETRY_FAILED",
                max_queued_jobs=None,
                accumulate_jobs=False,
            )

            if batch_run.queued_count == 0:
                cls.record_audit(
                    db=db,
                    project_id=project_id,
                    from_state=current,
                    to_state=current,
                    action=action_upper,
                    actor=actor,
                    result=OrchestrationActionResult.NO_OP,
                    reason_code="NO_FAILED_JOBS_TO_RETRY",
                    detail=f"BatchRun {batch_run.id} queued 0 retry jobs.",
                )
                db.commit()
                updated_state = cls.evaluate_state(db, project_id)
                return ExecuteActionResponse(
                    success=True,
                    action=action_upper,
                    from_stage=current,
                    to_stage=current,
                    result=OrchestrationActionResult.NO_OP,
                    message="No failed jobs found eligible for retry.",
                    orchestration_state=updated_state,
                )

            project.status = "VIDEO_IN_PROGRESS"
            cls.record_audit(
                db=db,
                project_id=project_id,
                from_state=current,
                to_state="VIDEO_IN_PROGRESS",
                action=action_upper,
                actor=actor,
                result=OrchestrationActionResult.APPLIED,
                detail=f"Dispatched BatchRun {batch_run.id} retrying failed jobs with queued_count={batch_run.queued_count}",
            )
            db.commit()

        # ----------------- 7. Action: TRANSITION_TO_FINAL_REVIEW -----------------
        elif action_upper == "TRANSITION_TO_FINAL_REVIEW":
            if current not in ("VIDEO_IN_PROGRESS", "READY_FOR_REVIEW"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cannot transition to final review from stage '{current}'.",
                )

            # Verify active jobs and shot counts
            story = db.query(Story).filter(Story.project_id == project_id).first()
            shot_count = (
                db.query(func.count(Shot.id))
                .join(Scene, Shot.scene_id == Scene.id)
                .filter(
                    (Scene.project_id == project_id)
                    | (Scene.story_id == (story.id if story else uuid.uuid4()))
                )
                .scalar()
                or 0
            )

            job_counts_query = (
                db.query(GenerationJob.status, func.count(GenerationJob.id))
                .join(Shot, GenerationJob.shot_id == Shot.id)
                .join(Scene, Shot.scene_id == Scene.id)
                .filter(
                    (Scene.project_id == project_id)
                    | (Scene.story_id == (story.id if story else uuid.uuid4()))
                )
                .group_by(GenerationJob.status)
                .all()
            )
            job_counts = {s: cnt for s, cnt in job_counts_query}
            active_jobs = sum(job_counts.get(s, 0) for s in ACTIVE_JOB_STATUSES)
            completed_jobs = job_counts.get("COMPLETED", 0)
            recon_jobs = job_counts.get("RECONCILIATION_REQUIRED", 0)

            if active_jobs > 0:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Cannot proceed to final review: {active_jobs} active generation job(s) are still processing.",
                )
            if recon_jobs > 0:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Cannot proceed to final review: {recon_jobs} job(s) require reconciliation.",
                )
            if shot_count == 0 or completed_jobs < shot_count:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cannot proceed to final review: only {completed_jobs}/{shot_count} shots are completed.",
                )

            project.status = "FINAL_REVIEW"
            cls.record_audit(
                db=db,
                project_id=project_id,
                from_state=current,
                to_state="FINAL_REVIEW",
                action=action_upper,
                actor=actor,
                result=OrchestrationActionResult.APPLIED,
                detail="All shots verified completed. Transitioned to FINAL_REVIEW.",
            )
            db.commit()

        # ----------------- 8. Action: RESOLVE_RECONCILIATION -----------------
        elif action_upper == "RESOLVE_RECONCILIATION":
            story = db.query(Story).filter(Story.project_id == project_id).first()
            recon_jobs_list = (
                db.query(GenerationJob)
                .join(Shot, GenerationJob.shot_id == Shot.id)
                .join(Scene, Shot.scene_id == Scene.id)
                .filter(
                    (Scene.project_id == project_id)
                    | (Scene.story_id == (story.id if story else uuid.uuid4())),
                    GenerationJob.status == "RECONCILIATION_REQUIRED",
                )
                .all()
            )
            resolved_count = len(recon_jobs_list)
            for r_job in recon_jobs_list:
                r_job.status = "FAILED"
                r_job.error_message = (
                    (r_job.error_message or "")
                    + " [Reconciled to FAILED via Orchestration for safe retry]"
                ).strip()

            cls.record_audit(
                db=db,
                project_id=project_id,
                from_state=current,
                to_state=current,
                action=action_upper,
                actor=actor,
                result=OrchestrationActionResult.APPLIED,
                detail=f"Reconciled {resolved_count} job(s) from RECONCILIATION_REQUIRED to FAILED for safe retry.",
            )
            db.commit()

        # ----------------- 9. Navigation / Non-charging Actions: POLL_STATUS & VIEW_SUMMARY -----------------
        elif action_upper == "POLL_STATUS":
            updated_state = cls.evaluate_state(db, project_id)
            return ExecuteActionResponse(
                success=True,
                action=action_upper,
                from_stage=current,
                to_stage=current,
                result=OrchestrationActionResult.NO_OP,
                message="Polling status completed.",
                orchestration_state=updated_state,
            )

        elif action_upper == "VIEW_SUMMARY":
            updated_state = cls.evaluate_state(db, project_id)
            return ExecuteActionResponse(
                success=True,
                action=action_upper,
                from_stage=current,
                to_stage=current,
                result=OrchestrationActionResult.NO_OP,
                message="Production completed. Summary ready.",
                orchestration_state=updated_state,
            )

        # ----------------- 10. Action: REVISE_STORY / REVISE_STORYBOARD / REVISE_SHOT_PLAN -----------------
        elif action_upper in ("REVISE_STORY", "REVISE_STORYBOARD", "REVISE_SHOT_PLAN"):
            # Fail closed: reject from terminal / in-progress states
            if current in ("COMPLETED", "APPROVED", "ARCHIVED", "VIDEO_IN_PROGRESS", "FINAL_REVIEW"):
                cls.record_audit(
                    db=db,
                    project_id=project_id,
                    from_state=current,
                    to_state=current,
                    action=action_upper,
                    actor=actor,
                    result=OrchestrationActionResult.BLOCKED,
                    reason_code="INVALID_REVISION_STAGE",
                    detail=f"Cannot revise at stage '{current}'.",
                )
                db.commit()
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cannot revise production plan at stage '{current}'.",
                )

            if action_upper == "REVISE_STORY":
                if video_mode != "STORY" or current not in ("STORY_GENERATED", "STORY_APPROVED"):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Cannot revise story from stage '{current}' in {video_mode} mode.",
                    )
                new_stage = "DRAFT"

            elif action_upper == "REVISE_STORYBOARD":
                if current not in ("STORYBOARD_GENERATED", "STORYBOARD_APPROVED"):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Cannot revise storyboard from stage '{current}'.",
                    )
                new_stage = "STORY_APPROVED" if video_mode == "STORY" else "DRAFT"

            elif action_upper == "REVISE_SHOT_PLAN":
                if current not in ("SHOT_PLAN_GENERATED", "SHOT_PLAN_APPROVED"):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Cannot revise shot plan from stage '{current}'.",
                    )
                new_stage = "STORYBOARD_APPROVED" if video_mode != "LOOP" else "DRAFT"

            project.status = new_stage
            cls.record_audit(
                db=db,
                project_id=project_id,
                from_state=current,
                to_state=new_stage,
                action=action_upper,
                actor=actor,
                result=OrchestrationActionResult.APPLIED,
                detail=f"Reverted to '{new_stage}' for revision.",
            )
            db.commit()

        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown orchestration action '{action}'.",
            )

        updated_state = cls.evaluate_state(db, project_id)
        return ExecuteActionResponse(
            success=True,
            action=action_upper,
            from_stage=current,
            to_stage=project.status,
            result=OrchestrationActionResult.APPLIED,
            message=f"Action '{action_upper}' executed successfully.",
            orchestration_state=updated_state,
        )

    @classmethod
    def update_settings(
        cls,
        db: Session,
        project_id: uuid.UUID,
        automation_mode: Optional[AutomationMode] = None,
        actor: str = "USER",
    ) -> OrchestrationStateResponse:
        project = db.get(Project, project_id)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project '{project_id}' not found",
            )

        current = project.status or "DRAFT"
        if automation_mode is not None:
            old_mode = getattr(project, "automation_mode", "MANUAL")
            project.automation_mode = automation_mode.value
            cls.record_audit(
                db=db,
                project_id=project_id,
                from_state=current,
                to_state=current,
                action="UPDATE_AUTOMATION_MODE",
                actor=actor,
                result=OrchestrationActionResult.APPLIED,
                detail=f"Changed automation mode from {old_mode} to {automation_mode.value}",
            )
            db.commit()

        return cls.evaluate_state(db, project_id)

    @classmethod
    def get_history(
        cls,
        db: Session,
        project_id: uuid.UUID,
        limit: int = 20,
        offset: int = 0,
    ) -> Tuple[List[OrchestrationAudit], int]:
        query = (
            db.query(OrchestrationAudit)
            .filter(OrchestrationAudit.project_id == project_id)
            .order_by(OrchestrationAudit.created_at.desc(), OrchestrationAudit.id.desc())
        )
        total = query.count()
        eff_limit = min(max(limit, 1), 100)
        items = query.offset(offset).limit(eff_limit).all()
        return items, total
