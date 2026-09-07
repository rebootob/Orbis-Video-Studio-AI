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
from app.models.asset_lock import AssetLock
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
from app.services.keyframe_generation import KeyframeGenerationService

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
    "IMAGES_IN_PROGRESS": "Keyframe Images In Progress",
    "IMAGES_GENERATED": "Keyframe Images Generated",
    "IMAGES_APPROVED": "Keyframe Images Approved",
    "VIDEO_IN_PROGRESS": "Video Generation In Progress",
    "FINAL_REVIEW": "Final Cut Review",
    "READY_FOR_REVIEW": "Final Cut Review",
    "AUDIO_PLAN_GENERATED": "Audio Plan Generated",
    "AUDIO_PLAN_APPROVED": "Audio Plan Approved",
    "AUDIO_IN_PROGRESS": "Audio Generation In Progress",
    "AUDIO_MIX_READY": "Audio Mix Ready",
    "AUDIO_APPROVED": "Audio Production Approved",
    "READY_FOR_ASSEMBLY": "Ready for Timeline Assembly",
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
    "SHOT_PLAN_APPROVED": "Shot plan is approved. Ready to dispatch keyframe image or video generation jobs.",
    "IMAGES_IN_PROGRESS": "Keyframe reference image generation jobs are actively processing.",
    "IMAGES_GENERATED": "Keyframe reference images generated and verified. Ready for approval.",
    "IMAGES_APPROVED": "Keyframe reference images approved. Ready to dispatch video generation jobs.",
    "VIDEO_IN_PROGRESS": "AI video generation jobs are actively processing in the provider queue.",
    "FINAL_REVIEW": "All video shots have completed generation. Inspect assembly for final approval.",
    "READY_FOR_REVIEW": "Ready for final production quality review.",
    "AUDIO_PLAN_GENERATED": "Audio production plan generated. Review VO, dialogue, BGM, SFX, and Ambience tracks.",
    "AUDIO_PLAN_APPROVED": "Audio production plan approved. Ready to generate audio clips.",
    "AUDIO_IN_PROGRESS": "Audio generation jobs are actively processing.",
    "AUDIO_MIX_READY": "Audio tracks generated and mixed with auto-ducking metadata. Inspect audio mix.",
    "AUDIO_APPROVED": "Audio production cut has been approved.",
    "READY_FOR_ASSEMBLY": "Video and audio assets approved. Ready for timeline assembly.",
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

        story = db.query(Story).filter(Story.project_id == project_id).first()
        has_story = story is not None and bool(story.logline or story.synopsis or story.title)

        # 1. Active Scenes (exclude soft-archived scenes)
        scenes_query = (
            db.query(Scene)
            .filter(
                (Scene.project_id == project_id)
                | (Scene.story_id == (story.id if story else uuid.uuid4()))
            )
            .all()
        )
        active_scenes = [s for s in scenes_query if not (s.scene_config or {}).get("archived")]
        active_scene_ids = {s.id for s in active_scenes}
        scene_count = len(active_scenes)

        # 2. Active Shots (belong to active scenes and not archived)
        active_shots = (
            db.query(Shot)
            .filter(
                Shot.scene_id.in_(active_scene_ids),
                Shot.status != "ARCHIVED",
            )
            .all()
        ) if active_scene_ids else []
        shot_count = len(active_shots)

        # 3. Hierarchical Locks (Project, Story/Script, Scene, Shot)
        active_locks = (
            db.query(AssetLock.entity_type, AssetLock.entity_id)
            .filter(AssetLock.project_id == project_id, AssetLock.is_locked == True)
            .all()
        )
        locked_shot_ids_table = {lid for etype, lid in active_locks if etype == "SHOT"}
        locked_scene_ids_table = {lid for etype, lid in active_locks if etype == "SCENE"}
        locked_script_ids_table = {lid for etype, lid in active_locks if etype == "SCRIPT"}

        is_project_locked = bool(getattr(project, "is_locked", False))
        is_story_locked = is_project_locked or bool(story and (story.is_locked or (story.id in locked_script_ids_table)))

        scene_map = {s.id: s for s in active_scenes}

        def is_shot_locked(sh: Shot) -> bool:
            if is_project_locked or is_story_locked:
                return True
            if sh.is_locked or (sh.id in locked_shot_ids_table):
                return True
            parent_scene = scene_map.get(sh.scene_id)
            if parent_scene and (parent_scene.is_locked or (parent_scene.id in locked_scene_ids_table)):
                return True
            return False

        locked_shot_count = sum(1 for s in active_shots if is_shot_locked(s))

        # 4. Job Counts and Distinct Production-Ready Calculation
        active_shot_ids = [s.id for s in active_shots]
        if active_shot_ids:
            job_rows = (
                db.query(GenerationJob.job_type, GenerationJob.status, func.count(GenerationJob.id))
                .filter(GenerationJob.shot_id.in_(active_shot_ids))
                .group_by(GenerationJob.job_type, GenerationJob.status)
                .all()
            )
            job_counts: Dict[str, int] = {}
            image_job_counts: Dict[str, int] = {}
            video_job_counts: Dict[str, int] = {}
            for jtype, status_val, cnt in job_rows:
                jt = (jtype or "VIDEO").upper()
                job_counts[status_val] = job_counts.get(status_val, 0) + cnt
                if jt == "IMAGE":
                    image_job_counts[status_val] = image_job_counts.get(status_val, 0) + cnt
                else:
                    video_job_counts[status_val] = video_job_counts.get(status_val, 0) + cnt

            completed_job_shot_ids = set(
                s_id for (s_id,) in (
                    db.query(GenerationJob.shot_id)
                    .filter(
                        GenerationJob.shot_id.in_(active_shot_ids),
                        func.coalesce(GenerationJob.job_type, "VIDEO") == "VIDEO",
                        GenerationJob.status == "COMPLETED",
                    )
                    .distinct()
                    .all()
                )
            )
        else:
            job_counts = {}
            image_job_counts = {}
            video_job_counts = {}
            completed_job_shot_ids = set()

        active_jobs = sum(job_counts.get(s, 0) for s in ACTIVE_JOB_STATUSES)
        active_image_jobs = sum(image_job_counts.get(s, 0) for s in ACTIVE_JOB_STATUSES)
        active_video_jobs = sum(video_job_counts.get(s, 0) for s in ACTIVE_JOB_STATUSES)
        completed_jobs = job_counts.get("COMPLETED", 0)
        failed_jobs = job_counts.get("FAILED", 0)
        failed_image_jobs = image_job_counts.get("FAILED", 0)
        failed_video_jobs = video_job_counts.get("FAILED", 0)
        recon_jobs = job_counts.get("RECONCILIATION_REQUIRED", 0)

        # Distinct production-ready shots:
        production_ready_shot_ids = {
            s.id for s in active_shots
            if (s.id in completed_job_shot_ids) or (
                s.shot_type not in ("AI_GENERATED", "MIXED")
                and (s.source_asset_id is not None or s.status == "COMPLETED")
            )
        }
        production_ready_count = len(production_ready_shot_ids)

        # Distinct keyframe-ready shots:
        keyframe_ready_shot_ids = {s.id for s in active_shots if s.keyframe_asset_id is not None}
        keyframe_ready_count = len(keyframe_ready_shot_ids)

        # Candidate ungenerated shots (for video locking checks)
        candidate_shots = [
            s for s in active_shots
            if s.id not in production_ready_shot_ids
            and s.shot_type in ("AI_GENERATED", "MIXED")
        ]
        all_candidates_locked = len(candidate_shots) > 0 and all(is_shot_locked(s) for s in candidate_shots)

        # Candidate keyframe shots (for image locking checks)
        candidate_keyframe_shots = [
            s for s in active_shots
            if s.id not in keyframe_ready_shot_ids
            and s.shot_type in ("AI_GENERATED", "MIXED")
        ]
        all_keyframe_candidates_locked = len(candidate_keyframe_shots) > 0 and all(is_shot_locked(s) for s in candidate_keyframe_shots)

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
            blocked_reasons.append(
                f"{recon_jobs} job(s) require reconciliation: provider outcome is ambiguous. "
                "Explicit verification/evidence is required before workflow continuation."
            )

        if active_jobs > 0:
            is_blocked = True
            blocked_reasons.append(f"{active_jobs} active job(s) currently processing in queue.")

        if current_stage in ("SHOT_PLAN_APPROVED", "VIDEO_IN_PROGRESS") and all_candidates_locked:
            is_blocked = True
            blocked_reasons.append(
                f"All {len(candidate_shots)} ungenerated candidate shot(s) are locked against generation."
            )

        # Stage truth: Never spoof effective_stage as FINAL_REVIEW when persisted status is still VIDEO_IN_PROGRESS!
        effective_stage = current_stage
        if current_stage not in ("COMPLETED", "APPROVED", "ARCHIVED"):
            if active_video_jobs > 0 and current_stage != "VIDEO_IN_PROGRESS":
                effective_stage = "VIDEO_IN_PROGRESS"
            elif active_image_jobs > 0 and current_stage not in ("IMAGES_IN_PROGRESS", "VIDEO_IN_PROGRESS"):
                effective_stage = "IMAGES_IN_PROGRESS"
            elif recon_jobs > 0 and current_stage not in ALLOWED_PRODUCTION_STATUSES:
                effective_stage = "NEEDS_ATTENTION"

        is_approval_required = effective_stage in (
            "STORY_GENERATED",
            "STORYBOARD_GENERATED",
            "SHOT_PLAN_GENERATED",
            "IMAGES_GENERATED",
            "AUDIO_PLAN_GENERATED",
            "AUDIO_MIX_READY",
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
            production_ready_count=production_ready_count,
            failed_jobs=failed_jobs,
            recon_jobs=recon_jobs,
            hard_limit_exceeded=hard_limit_exceeded,
            all_candidates_locked=all_candidates_locked,
            candidate_count=len(candidate_shots),
            keyframe_ready_count=keyframe_ready_count,
            active_image_jobs=active_image_jobs,
            failed_image_jobs=failed_image_jobs,
            all_keyframe_candidates_locked=all_keyframe_candidates_locked,
        )

        stage_name = STAGE_DISPLAY_NAMES.get(effective_stage, effective_stage.replace("_", " ").title())
        stage_desc = STAGE_DESCRIPTIONS.get(effective_stage, "Production stage.")

        summary = {
            "has_story": has_story,
            "scene_count": scene_count,
            "shot_count": shot_count,
            "locked_shots": locked_shot_count,
            "production_ready_shots": production_ready_count,
            "keyframe_ready_shots": keyframe_ready_count,
            "candidate_shots": len(candidate_shots),
            "candidate_keyframe_shots": len(candidate_keyframe_shots),
            "all_candidates_locked": all_candidates_locked,
            "all_keyframe_candidates_locked": all_keyframe_candidates_locked,
            "active_jobs": active_jobs,
            "active_image_jobs": active_image_jobs,
            "active_video_jobs": active_video_jobs,
            "completed_jobs": completed_jobs,
            "distinct_completed_shots": len(completed_job_shot_ids),
            "failed_jobs": failed_jobs,
            "failed_image_jobs": failed_image_jobs,
            "failed_video_jobs": failed_video_jobs,
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
        production_ready_count: int,
        failed_jobs: int,
        recon_jobs: int,
        hard_limit_exceeded: bool,
        all_candidates_locked: bool = False,
        candidate_count: int = 0,
        keyframe_ready_count: int = 0,
        active_image_jobs: int = 0,
        failed_image_jobs: int = 0,
        all_keyframe_candidates_locked: bool = False,
    ) -> Tuple[Optional[OrchestrationActionModel], List[OrchestrationActionModel]]:
        recommended: Optional[OrchestrationActionModel] = None
        available: List[OrchestrationActionModel] = []

        if current_stage == "ARCHIVED":
            return None, []

        if recon_jobs > 0:
            recommended = OrchestrationActionModel(
                action="RESOLVE_RECONCILIATION",
                display_name="Review & Reconcile Jobs",
                description="Investigate and reconcile in-flight jobs that lost provider synchronization.",
                action_type=OrchestrationActionType.NAVIGATION,
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
                # In DRAFT, next action is ALWAYS GENERATE_STORY (never APPROVE_STORY from DRAFT!)
                recommended = OrchestrationActionModel(
                    action="GENERATE_STORY",
                    display_name="Generate Story Outline",
                    description="Create initial narrative arc, character profiles, and scene outline." if not has_story else "Regenerate story outline.",
                    action_type=OrchestrationActionType.GENERATION,
                    is_chargeable=True,
                    is_blocked=hard_limit_exceeded,
                    blocked_reason="Hard budget limit exceeded" if hard_limit_exceeded else None,
                )

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
                    description="Revert to draft to edit narrative prompt and regenerate outline.",
                    action_type=OrchestrationActionType.REVISION,
                ))
                available.append(OrchestrationActionModel(
                    action="GENERATE_STORY",
                    display_name="Regenerate Story Outline",
                    description="Regenerate outline with updated instructions.",
                    action_type=OrchestrationActionType.GENERATION,
                    is_chargeable=True,
                    is_blocked=hard_limit_exceeded,
                    blocked_reason="Hard budget limit exceeded" if hard_limit_exceeded else None,
                ))

            elif current_stage == "STORY_APPROVED":
                # In STORY_APPROVED, next action is ALWAYS GENERATE_STORYBOARD (never APPROVE_STORYBOARD from STORY_APPROVED!)
                recommended = OrchestrationActionModel(
                    action="GENERATE_STORYBOARD",
                    display_name="Generate Storyboard Scenes",
                    description="Generate storyboard scenes from the approved story outline.",
                    action_type=OrchestrationActionType.GENERATION,
                    is_chargeable=True,
                    is_blocked=hard_limit_exceeded,
                    blocked_reason="Hard budget limit exceeded" if hard_limit_exceeded else None,
                )
                available.append(OrchestrationActionModel(
                    action="REVISE_STORY",
                    display_name="Revise Story Outline",
                    description="Revert to draft to modify story outline.",
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
                    description="Revert to approved story stage to regenerate scenes.",
                    action_type=OrchestrationActionType.REVISION,
                ))
                available.append(OrchestrationActionModel(
                    action="GENERATE_STORYBOARD",
                    display_name="Regenerate Storyboard Scenes",
                    description="Regenerate scenes with updated instructions.",
                    action_type=OrchestrationActionType.GENERATION,
                    is_chargeable=True,
                    is_blocked=hard_limit_exceeded,
                    blocked_reason="Hard budget limit exceeded" if hard_limit_exceeded else None,
                ))

            elif current_stage == "STORYBOARD_APPROVED":
                # In STORYBOARD_APPROVED, next action is ALWAYS GENERATE_SHOT_PLAN (never APPROVE_SHOT_PLAN from STORYBOARD_APPROVED!)
                recommended = OrchestrationActionModel(
                    action="GENERATE_SHOT_PLAN",
                    display_name="Generate Shot Plan & Prompts",
                    description="Generate camera shots, durations, and AI visual prompts.",
                    action_type=OrchestrationActionType.GENERATION,
                    is_chargeable=True,
                    is_blocked=hard_limit_exceeded,
                    blocked_reason="Hard budget limit exceeded" if hard_limit_exceeded else None,
                )
                available.append(OrchestrationActionModel(
                    action="REVISE_STORYBOARD",
                    display_name="Revise Storyboard",
                    description="Revert to modify storyboard scenes.",
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
                    description="Revert to approved storyboard to regenerate shot plans.",
                    action_type=OrchestrationActionType.REVISION,
                ))
                available.append(OrchestrationActionModel(
                    action="GENERATE_SHOT_PLAN",
                    display_name="Regenerate Shot Plan",
                    description="Regenerate shot plan and prompts.",
                    action_type=OrchestrationActionType.GENERATION,
                    is_chargeable=True,
                    is_blocked=hard_limit_exceeded,
                    blocked_reason="Hard budget limit exceeded" if hard_limit_exceeded else None,
                ))

        # ----------------- Modes: SHORT & SCENE (No Story outline) -----------------
        elif video_mode in ("SHORT", "SCENE"):
            if current_stage == "DRAFT":
                recommended = OrchestrationActionModel(
                    action="GENERATE_STORYBOARD",
                    display_name="Create Storyboard Scenes",
                    description="Initialize scene structure for short-form production.",
                    action_type=OrchestrationActionType.GENERATION,
                    is_chargeable=True,
                    is_blocked=hard_limit_exceeded,
                    blocked_reason="Hard budget limit exceeded" if hard_limit_exceeded else None,
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
                available.append(OrchestrationActionModel(
                    action="REVISE_STORYBOARD",
                    display_name="Revise Storyboard",
                    description="Revert to draft to adjust storyboard.",
                    action_type=OrchestrationActionType.REVISION,
                ))
            elif current_stage == "STORYBOARD_APPROVED":
                recommended = OrchestrationActionModel(
                    action="GENERATE_SHOT_PLAN",
                    display_name="Generate Shot Plan & Prompts",
                    description="Generate camera shots and AI prompts for scenes.",
                    action_type=OrchestrationActionType.GENERATION,
                    is_chargeable=True,
                    is_blocked=hard_limit_exceeded,
                    blocked_reason="Hard budget limit exceeded" if hard_limit_exceeded else None,
                )
                available.append(OrchestrationActionModel(
                    action="REVISE_STORYBOARD",
                    display_name="Revise Storyboard",
                    description="Revert to modify storyboard scenes.",
                    action_type=OrchestrationActionType.REVISION,
                ))
            elif current_stage == "SHOT_PLAN_GENERATED":
                recommended = OrchestrationActionModel(
                    action="APPROVE_SHOT_PLAN",
                    display_name="Approve Shot Plan & Proceed",
                    description="Approve shot plan and proceed to video generation.",
                    action_type=OrchestrationActionType.APPROVAL,
                    is_chargeable=False,
                    parameters={"stage": "SHOT_PLAN_GENERATED"},
                )
                available.append(OrchestrationActionModel(
                    action="REVISE_SHOT_PLAN",
                    display_name="Revise Shot Plan",
                    description="Revert to storyboard approved to regenerate shots.",
                    action_type=OrchestrationActionType.REVISION,
                ))

        # ----------------- Mode: LOOP (No Story or Scene outline) -----------------
        elif video_mode == "LOOP":
            if current_stage == "DRAFT":
                recommended = OrchestrationActionModel(
                    action="GENERATE_SHOT_PLAN",
                    display_name="Configure Loop Shot Plan",
                    description="Set up loop shot duration and seamless visual prompt.",
                    action_type=OrchestrationActionType.GENERATION,
                    is_chargeable=True,
                    is_blocked=hard_limit_exceeded,
                    blocked_reason="Hard budget limit exceeded" if hard_limit_exceeded else None,
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
                available.append(OrchestrationActionModel(
                    action="REVISE_SHOT_PLAN",
                    display_name="Revise Shot Plan",
                    description="Revert to draft to adjust loop settings.",
                    action_type=OrchestrationActionType.REVISION,
                ))

        # ----------------- Downstream Stages (All modes) -----------------
        if current_stage == "SHOT_PLAN_APPROVED":
            is_keyframe_blocked = hard_limit_exceeded or all_keyframe_candidates_locked
            keyframe_blocked_msg = "Hard budget limit exceeded" if hard_limit_exceeded else (
                "All candidate keyframe shots are locked" if all_keyframe_candidates_locked else None
            )

            is_video_blocked = hard_limit_exceeded or all_candidates_locked
            video_blocked_msg = "Hard budget limit exceeded" if hard_limit_exceeded else (
                f"All {candidate_count} candidate shots are locked" if all_candidates_locked else None
            )

            if shot_count > 0 and keyframe_ready_count >= shot_count:
                recommended = OrchestrationActionModel(
                    action="APPROVE_IMAGES",
                    display_name="Approve Keyframe Images & Proceed",
                    description="All keyframe images are generated. Approve to proceed to video generation.",
                    action_type=OrchestrationActionType.APPROVAL,
                    is_chargeable=False,
                    parameters={"stage": "IMAGES_GENERATED"},
                )
                available.append(OrchestrationActionModel(
                    action="START_VIDEO_GENERATION",
                    display_name="Start Video Generation",
                    description="Dispatch eligible AI video generation jobs to the provider queue.",
                    action_type=OrchestrationActionType.GENERATION,
                    is_chargeable=True,
                    is_blocked=is_video_blocked,
                    blocked_reason=video_blocked_msg,
                ))
            else:
                recommended = OrchestrationActionModel(
                    action="START_KEYFRAME_GENERATION",
                    display_name="Generate Keyframe Images",
                    description="Generate visual keyframe reference images for storyboard shots.",
                    action_type=OrchestrationActionType.GENERATION,
                    is_chargeable=True,
                    is_blocked=is_keyframe_blocked,
                    blocked_reason=keyframe_blocked_msg,
                )
                available.append(OrchestrationActionModel(
                    action="START_VIDEO_GENERATION",
                    display_name="Start Video Generation",
                    description="Dispatch AI video generation jobs directly.",
                    action_type=OrchestrationActionType.GENERATION,
                    is_chargeable=True,
                    is_blocked=is_video_blocked,
                    blocked_reason=video_blocked_msg,
                ))
            available.append(OrchestrationActionModel(
                action="GENERATE_SELECTED_KEYFRAMES",
                display_name="Generate Selected Keyframes",
                description="Generate keyframe images for selected shots only.",
                action_type=OrchestrationActionType.GENERATION,
                is_chargeable=True,
                is_blocked=is_keyframe_blocked,
                blocked_reason=keyframe_blocked_msg,
            ))
            available.append(OrchestrationActionModel(
                action="REVISE_SHOT_PLAN",
                display_name="Revise Shot Plan",
                description="Make adjustments to shot prompts or camera instructions.",
                action_type=OrchestrationActionType.REVISION,
            ))

        elif current_stage == "IMAGES_IN_PROGRESS":
            if active_image_jobs > 0:
                recommended = OrchestrationActionModel(
                    action="POLL_STATUS",
                    display_name="Monitor Active Keyframe Jobs",
                    description=f"{active_image_jobs} keyframe job(s) actively processing.",
                    action_type=OrchestrationActionType.NAVIGATION,
                    is_chargeable=False,
                )
            elif failed_image_jobs > 0:
                recommended = OrchestrationActionModel(
                    action="RETRY_FAILED_KEYFRAMES",
                    display_name="Retry Failed Keyframes",
                    description=f"Retry {failed_image_jobs} failed keyframe image job(s).",
                    action_type=OrchestrationActionType.RECOVERY,
                    is_chargeable=True,
                    is_blocked=hard_limit_exceeded,
                    blocked_reason="Hard budget limit exceeded" if hard_limit_exceeded else None,
                )
            elif shot_count > 0 and keyframe_ready_count >= shot_count:
                recommended = OrchestrationActionModel(
                    action="APPROVE_IMAGES",
                    display_name="Approve Keyframe Images & Proceed",
                    description="All keyframes generated. Approve keyframes for video generation.",
                    action_type=OrchestrationActionType.APPROVAL,
                    is_chargeable=False,
                    parameters={"stage": "IMAGES_GENERATED"},
                )
            else:
                recommended = OrchestrationActionModel(
                    action="CONTINUE_INCOMPLETE_KEYFRAMES",
                    display_name="Continue Incomplete Keyframes",
                    description="Dispatch remaining ungenerated keyframe images.",
                    action_type=OrchestrationActionType.GENERATION,
                    is_chargeable=True,
                    is_blocked=hard_limit_exceeded,
                    blocked_reason="Hard budget limit exceeded" if hard_limit_exceeded else None,
                )
            available.append(OrchestrationActionModel(
                action="START_VIDEO_GENERATION",
                display_name="Start Video Generation",
                description="Dispatch video generation jobs directly.",
                action_type=OrchestrationActionType.GENERATION,
                is_chargeable=True,
            ))
            available.append(OrchestrationActionModel(
                action="REVISE_SHOT_PLAN",
                display_name="Revise Shot Plan",
                description="Return to storyboard to regenerate shots.",
                action_type=OrchestrationActionType.REVISION,
            ))

        elif current_stage == "IMAGES_GENERATED":
            recommended = OrchestrationActionModel(
                action="APPROVE_IMAGES",
                display_name="Approve Keyframe Images & Proceed",
                description="Lock keyframe reference images and proceed to video generation.",
                action_type=OrchestrationActionType.APPROVAL,
                is_chargeable=False,
                parameters={"stage": "IMAGES_GENERATED"},
            )
            available.append(OrchestrationActionModel(
                action="START_VIDEO_GENERATION",
                display_name="Start Video Generation",
                description="Dispatch video generation jobs directly.",
                action_type=OrchestrationActionType.GENERATION,
                is_chargeable=True,
            ))
            available.append(OrchestrationActionModel(
                action="GENERATE_SELECTED_KEYFRAMES",
                display_name="Regenerate Selected Keyframes",
                description="Regenerate keyframe images for selected shots.",
                action_type=OrchestrationActionType.GENERATION,
                is_chargeable=True,
            ))
            if failed_image_jobs > 0:
                available.append(OrchestrationActionModel(
                    action="RETRY_FAILED_KEYFRAMES",
                    display_name="Retry Failed Keyframes",
                    description="Retry failed keyframe jobs.",
                    action_type=OrchestrationActionType.RECOVERY,
                    is_chargeable=True,
                ))
            if shot_count > 0 and keyframe_ready_count < shot_count:
                available.append(OrchestrationActionModel(
                    action="CONTINUE_INCOMPLETE_KEYFRAMES",
                    display_name="Continue Incomplete Keyframes",
                    description="Generate missing keyframes.",
                    action_type=OrchestrationActionType.GENERATION,
                    is_chargeable=True,
                ))
            available.append(OrchestrationActionModel(
                action="REVISE_SHOT_PLAN",
                display_name="Revise Shot Plan",
                description="Return to modify shot plan.",
                action_type=OrchestrationActionType.REVISION,
            ))

        elif current_stage == "IMAGES_APPROVED":
            is_video_blocked = hard_limit_exceeded or all_candidates_locked
            video_blocked_msg = "Hard budget limit exceeded" if hard_limit_exceeded else (
                f"All {candidate_count} candidate shots are locked" if all_candidates_locked else None
            )
            recommended = OrchestrationActionModel(
                action="START_VIDEO_GENERATION",
                display_name="Start Video Generation",
                description="Dispatch eligible AI video generation jobs using approved keyframe references.",
                action_type=OrchestrationActionType.GENERATION,
                is_chargeable=True,
                is_blocked=is_video_blocked,
                blocked_reason=video_blocked_msg,
            )
            available.append(OrchestrationActionModel(
                action="GENERATE_SELECTED_SHOTS",
                display_name="Generate Selected Shots",
                description="Dispatch selected shots only.",
                action_type=OrchestrationActionType.GENERATION,
                is_chargeable=True,
                is_blocked=is_video_blocked,
                blocked_reason=video_blocked_msg,
            ))
            available.append(OrchestrationActionModel(
                action="GENERATE_SELECTED_KEYFRAMES",
                display_name="Regenerate Selected Keyframes",
                description="Regenerate keyframe images for selected shots.",
                action_type=OrchestrationActionType.GENERATION,
                is_chargeable=True,
            ))
            available.append(OrchestrationActionModel(
                action="REVISE_SHOT_PLAN",
                display_name="Revise Shot Plan",
                description="Return to modify shot plan.",
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
            elif shot_count > 0 and production_ready_count >= shot_count:
                recommended = OrchestrationActionModel(
                    action="TRANSITION_TO_FINAL_REVIEW",
                    display_name="Proceed to Final Review",
                    description="All shots generated/ready. Inspect final cut assembly.",
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
                    blocked_reason="Hard budget limit exceeded" if hard_limit_exceeded else None,
                )
            elif production_ready_count < shot_count:
                is_cont_blocked = hard_limit_exceeded or all_candidates_locked
                cont_msg = "Hard budget limit exceeded" if hard_limit_exceeded else (
                    f"All {candidate_count} candidate shots are locked" if all_candidates_locked else None
                )
                recommended = OrchestrationActionModel(
                    action="CONTINUE_INCOMPLETE",
                    display_name="Continue Incomplete Generation",
                    description="Dispatch remaining ungenerated shots.",
                    action_type=OrchestrationActionType.GENERATION,
                    is_chargeable=True,
                    is_blocked=is_cont_blocked,
                    blocked_reason=cont_msg,
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
            available.append(OrchestrationActionModel(
                action="GENERATE_AUDIO_PLAN",
                display_name="Proceed to Audio Production",
                description="Initialize audio plan for narrator, voiceover, BGM, and effects.",
                action_type=OrchestrationActionType.GENERATION,
                is_chargeable=False,
            ))

        elif current_stage == "AUDIO_PLAN_GENERATED":
            recommended = OrchestrationActionModel(
                action="APPROVE_AUDIO_PLAN",
                display_name="Approve Audio Plan & Proceed",
                description="Approve audio tracks and proceed to clip generation.",
                action_type=OrchestrationActionType.APPROVAL,
                is_chargeable=False,
                parameters={"stage": "AUDIO_PLAN_GENERATED"},
            )
            available.append(OrchestrationActionModel(
                action="GENERATE_AUDIO_PLAN",
                display_name="Regenerate Audio Plan",
                description="Re-analyze scenes and regenerate audio plan.",
                action_type=OrchestrationActionType.GENERATION,
                is_chargeable=False,
            ))

        elif current_stage == "AUDIO_PLAN_APPROVED":
            recommended = OrchestrationActionModel(
                action="START_AUDIO_GENERATION",
                display_name="Generate Audio Clips",
                description="Dispatch voiceover, dialogue, BGM, SFX, and ambience generation.",
                action_type=OrchestrationActionType.GENERATION,
                is_chargeable=True,
                is_blocked=hard_limit_exceeded,
                blocked_reason="Hard budget limit exceeded" if hard_limit_exceeded else None,
            )
            available.append(OrchestrationActionModel(
                action="GENERATE_ALL_VO",
                display_name="Generate All Voiceover",
                description="Generate voiceover and dialogue audio clips.",
                action_type=OrchestrationActionType.GENERATION,
                is_chargeable=True,
            ))
            available.append(OrchestrationActionModel(
                action="ASSIGN_BGM",
                display_name="Generate Background Music",
                description="Generate project background music track.",
                action_type=OrchestrationActionType.GENERATION,
                is_chargeable=True,
            ))

        elif current_stage == "AUDIO_IN_PROGRESS":
            recommended = OrchestrationActionModel(
                action="AUTO_MIX_AUDIO",
                display_name="Compute Auto-Mix & Ducking",
                description="Mix generated audio tracks with speech-over-music auto-ducking.",
                action_type=OrchestrationActionType.GENERATION,
                is_chargeable=False,
            )
            available.append(OrchestrationActionModel(
                action="CONTINUE_INCOMPLETE_AUDIO",
                display_name="Continue Incomplete Audio",
                description="Generate remaining pending audio clips.",
                action_type=OrchestrationActionType.GENERATION,
                is_chargeable=True,
            ))
            available.append(OrchestrationActionModel(
                action="RETRY_FAILED_AUDIO",
                display_name="Retry Failed Audio",
                description="Retry failed audio clip generation.",
                action_type=OrchestrationActionType.RECOVERY,
                is_chargeable=True,
            ))

        elif current_stage == "AUDIO_MIX_READY":
            recommended = OrchestrationActionModel(
                action="APPROVE_AUDIO_MIX",
                display_name="Approve Audio Mix & Proceed",
                description="Approve audio mix and proceed to final assembly.",
                action_type=OrchestrationActionType.APPROVAL,
                is_chargeable=False,
                parameters={"stage": "AUDIO_MIX_READY"},
            )
            available.append(OrchestrationActionModel(
                action="AUTO_MIX_AUDIO",
                display_name="Recompute Auto-Mix",
                description="Re-calculate ducking and volume balance.",
                action_type=OrchestrationActionType.GENERATION,
                is_chargeable=False,
            ))

        elif current_stage == "AUDIO_APPROVED":
            recommended = OrchestrationActionModel(
                action="PROCEED_TO_ASSEMBLY",
                display_name="Proceed to Assembly",
                description="Advance project to timeline assembly.",
                action_type=OrchestrationActionType.APPROVAL,
                is_chargeable=False,
            )

        elif current_stage == "READY_FOR_ASSEMBLY":
            recommended = OrchestrationActionModel(
                action="APPROVE_FINAL",
                display_name="Approve Final Assembly",
                description="Mark production completed.",
                action_type=OrchestrationActionType.APPROVAL,
                is_chargeable=False,
            )

        return recommended, available

    @classmethod
    def approve_stage(
        cls,
        db: Session,
        project_id: uuid.UUID,
        stage: Optional[str] = None,
        notes: Optional[str] = None,
        cost_authorized: bool = False,
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
            "IMAGES_GENERATED": "IMAGES_APPROVED",
            "AUDIO_PLAN_GENERATED": "AUDIO_PLAN_APPROVED",
            "AUDIO_MIX_READY": "AUDIO_APPROVED",
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
        if current in ("FINAL_REVIEW", "READY_FOR_REVIEW") or target_stage in ("COMPLETED", "APPROVED"):
            from app.services.qc import QCService
            QCService.approve_production(
                db=db,
                project_id=project_id,
                notes=notes,
                actor=actor,
            )
        else:
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
        # GENERATE_STORY / GENERATE_STORYBOARD / GENERATE_SHOT_PLAN are chargeable provider actions.
        # AUTO must NOT silently execute a chargeable action after approval.
        # Unless explicit persisted or one-shot cost authorization exists, AUTO must STOP and recommend the chargeable next action.
        # Video generation gates always require explicit human confirmation.
        default_cfg = getattr(project, "default_config", None) or {}
        mode_cfg = getattr(project, "mode_config", None) or {}
        has_persisted_cost_auth = False
        if isinstance(default_cfg, dict):
            has_persisted_cost_auth = bool(
                default_cfg.get("auto_cost_authorized") or default_cfg.get("cost_authorized")
            )
        if not has_persisted_cost_auth and isinstance(mode_cfg, dict):
            has_persisted_cost_auth = bool(
                mode_cfg.get("auto_cost_authorized") or mode_cfg.get("cost_authorized")
            )
        has_cost_authorization = cost_authorized or has_persisted_cost_auth

        auto_mode = getattr(project, "automation_mode", "MANUAL")
        if auto_mode == "AUTO":
            b_summary = BudgetService.get_budget_status(db, project_id)
            if b_summary.get("is_hard_limit_exceeded"):
                cls.record_audit(
                    db=db,
                    project_id=project_id,
                    from_state=target_stage,
                    to_state=target_stage,
                    action="AUTO_HALTED",
                    actor="AUTO",
                    result=OrchestrationActionResult.BLOCKED,
                    reason_code="HARD_BUDGET_LIMIT_EXCEEDED",
                    detail="Auto-cascade halted: project hard budget limit exceeded.",
                )
                db.commit()
                updated_state = cls.evaluate_state(db, project_id)
                return ApproveStageResponse(
                    success=True,
                    from_stage=current,
                    to_stage=project.status,
                    result=OrchestrationActionResult.APPLIED,
                    message=f"Stage successfully approved: transitioned to '{project.status}'. Auto-cascade halted: hard budget limit exceeded.",
                    orchestration_state=updated_state,
                )

            if not has_cost_authorization:
                # AUTO must NOT silently execute a chargeable action after approval.
                # It must STOP and recommend the chargeable next action.
                cls.record_audit(
                    db=db,
                    project_id=project_id,
                    from_state=target_stage,
                    to_state=target_stage,
                    action="AUTO_STOPPED_AWAITING_COST_AUTHORIZATION",
                    actor="AUTO",
                    result=OrchestrationActionResult.NO_OP,
                    reason_code="CHARGEABLE_ACTION_REQUIRES_AUTHORIZATION",
                    detail=f"Auto-cascade stopped after '{target_stage}': next action is chargeable and requires explicit cost authorization.",
                )
                db.commit()
                updated_state = cls.evaluate_state(db, project_id)
                return ApproveStageResponse(
                    success=True,
                    from_stage=current,
                    to_stage=project.status,
                    result=OrchestrationActionResult.APPLIED,
                    message=f"Stage successfully approved: transitioned to '{project.status}'. Auto-cascade stopped: next action is chargeable and requires cost authorization.",
                    orchestration_state=updated_state,
                )

            # Explicit cost authorization exists: execute the downstream creative stage
            if target_stage == "STORY_APPROVED":
                cls.execute_action(
                    db=db,
                    project_id=project_id,
                    action="GENERATE_STORYBOARD",
                    actor="AUTO",
                    provider=provider,
                )
            elif target_stage == "STORYBOARD_APPROVED":
                cls.execute_action(
                    db=db,
                    project_id=project_id,
                    action="GENERATE_SHOT_PLAN",
                    actor="AUTO",
                    provider=provider,
                )
            elif target_stage == "SHOT_PLAN_APPROVED":
                # Mandatory STOP: Keyframe and video generation require explicit execution / authorization
                pass
            elif target_stage == "IMAGES_APPROVED":
                # Mandatory STOP: Video generation ALWAYS requires explicit human confirmation!
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
        if action_upper in ("APPROVE_STORY", "APPROVE_STORYBOARD", "APPROVE_SHOT_PLAN", "APPROVE_IMAGES", "APPROVE_AUDIO_PLAN", "APPROVE_AUDIO_MIX", "APPROVE_FINAL"):
            # Enforce gate matching for approval actions
            expected_current = {
                "APPROVE_STORY": ("STORY_GENERATED", "STORY_APPROVED"),
                "APPROVE_STORYBOARD": ("STORYBOARD_GENERATED", "STORYBOARD_APPROVED"),
                "APPROVE_SHOT_PLAN": ("SHOT_PLAN_GENERATED", "SHOT_PLAN_APPROVED"),
                "APPROVE_IMAGES": ("IMAGES_GENERATED", "IMAGES_APPROVED"),
                "APPROVE_AUDIO_PLAN": ("AUDIO_PLAN_GENERATED", "AUDIO_PLAN_APPROVED"),
                "APPROVE_AUDIO_MIX": ("AUDIO_MIX_READY", "AUDIO_APPROVED"),
                "APPROVE_FINAL": ("FINAL_REVIEW", "READY_FOR_REVIEW", "COMPLETED", "READY_FOR_ASSEMBLY"),
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
                "APPROVE_IMAGES": "IMAGES_APPROVED",
                "APPROVE_AUDIO_PLAN": "AUDIO_PLAN_APPROVED",
                "APPROVE_AUDIO_MIX": "AUDIO_APPROVED",
                "APPROVE_FINAL": "COMPLETED",
            }[action_upper]

            cost_auth = bool(params.get("cost_authorized", False))
            approval_res = cls.approve_stage(
                db=db,
                project_id=project_id,
                stage=target_stage_for_action,
                notes=params.get("notes"),
                cost_authorized=cost_auth,
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

        # ----------------- 3b. Keyframe Generation Actions -----------------
        elif action_upper in (
            "START_KEYFRAME_GENERATION",
            "GENERATE_KEYFRAMES",
            "CONTINUE_INCOMPLETE_KEYFRAMES",
            "RETRY_FAILED_KEYFRAMES",
            "GENERATE_SELECTED_KEYFRAMES",
        ):
            if current not in ("SHOT_PLAN_APPROVED", "IMAGES_GENERATED", "IMAGES_APPROVED", "IMAGES_IN_PROGRESS"):
                cls.record_audit(
                    db=db,
                    project_id=project_id,
                    from_state=current,
                    to_state=current,
                    action=action_upper,
                    actor=actor,
                    result=OrchestrationActionResult.BLOCKED,
                    reason_code="STAGE_NOT_APPROVED",
                    detail=f"Keyframe generation requires approved shot plan or images stage, current status is '{current}'.",
                )
                db.commit()
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Keyframe generation requires 'SHOT_PLAN_APPROVED' or images stage, current status is '{current}'.",
                )

            # Check reconciliation safety: fail closed if any job requires reconciliation
            story = db.query(Story).filter(Story.project_id == project_id).first()
            recon_count = (
                db.query(func.count(GenerationJob.id))
                .join(Shot, GenerationJob.shot_id == Shot.id)
                .join(Scene, Shot.scene_id == Scene.id)
                .filter(
                    (Scene.project_id == project_id)
                    | (Scene.story_id == (story.id if story else uuid.uuid4())),
                    GenerationJob.status == "RECONCILIATION_REQUIRED",
                )
                .scalar()
                or 0
            )
            if recon_count > 0:
                cls.record_audit(
                    db=db,
                    project_id=project_id,
                    from_state=current,
                    to_state=current,
                    action=action_upper,
                    actor=actor,
                    result=OrchestrationActionResult.BLOCKED,
                    reason_code="RECONCILIATION_REQUIRED",
                    detail=f"Cannot dispatch keyframe generation: {recon_count} job(s) require reconciliation before workflow continuation.",
                )
                db.commit()
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Cannot dispatch keyframe generation: {recon_count} job(s) require reconciliation before workflow continuation.",
                )

            # Check hard limit
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
                    detail="Project hard budget limit exceeded. Keyframe generation dispatch is blocked.",
                )

            # Check cost authorization in AUTO mode
            default_cfg = getattr(project, "default_config", None) or {}
            mode_cfg = getattr(project, "mode_config", None) or {}
            has_persisted_cost_auth = False
            if isinstance(default_cfg, dict):
                has_persisted_cost_auth = bool(
                    default_cfg.get("auto_cost_authorized") or default_cfg.get("cost_authorized")
                )
            if not has_persisted_cost_auth and isinstance(mode_cfg, dict):
                has_persisted_cost_auth = bool(
                    mode_cfg.get("auto_cost_authorized") or mode_cfg.get("cost_authorized")
                )
            cost_auth = bool(params.get("cost_authorized", False)) or has_persisted_cost_auth

            if actor == "AUTO" and not cost_auth:
                cls.record_audit(
                    db=db,
                    project_id=project_id,
                    from_state=current,
                    to_state=current,
                    action="AUTO_STOPPED_AWAITING_COST_AUTHORIZATION",
                    actor="AUTO",
                    result=OrchestrationActionResult.BLOCKED,
                    reason_code="CHARGEABLE_ACTION_REQUIRES_AUTHORIZATION",
                    detail="Keyframe generation is chargeable and requires explicit cost authorization.",
                )
                db.commit()
                raise HTTPException(
                    status_code=status.HTTP_402_PAYMENT_REQUIRED,
                    detail="Keyframe generation is chargeable and requires explicit cost authorization in AUTO mode.",
                )

            # Determine operation type
            if action_upper in ("START_KEYFRAME_GENERATION", "GENERATE_KEYFRAMES", "CONTINUE_INCOMPLETE_KEYFRAMES"):
                op_type = "CONTINUE_INCOMPLETE"
                shot_ids = None
            elif action_upper == "RETRY_FAILED_KEYFRAMES":
                op_type = "RETRY_FAILED"
                shot_ids = None
            else:  # GENERATE_SELECTED_KEYFRAMES
                op_type = "GENERATE_SELECTED"
                raw_shot_ids = params.get("shot_ids") or params.get("selected_shot_ids") or []
                shot_ids = [uuid.UUID(s) if isinstance(s, str) else s for s in raw_shot_ids]

            batch_run, _ = KeyframeGenerationService.execute_keyframe_batch(
                db=db,
                project_id=project_id,
                operation_type=op_type,
                shot_ids=shot_ids,
                cost_authorized=cost_auth,
                actor=actor,
            )

            updated_state = cls.evaluate_state(db, project_id)
            return ExecuteActionResponse(
                success=True,
                action=action_upper,
                from_stage=current,
                to_stage=project.status or current,
                result=OrchestrationActionResult.APPLIED,
                message=f"Keyframe batch execution completed: {batch_run.completed_count} generated, {batch_run.failed_count} failed, {batch_run.skipped_count} skipped.",
                orchestration_state=updated_state,
            )

        elif action_upper == "GENERATE_SHOT_KEYFRAME":
            raw_shot_id = params.get("shot_id")
            if not raw_shot_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Parameter 'shot_id' is required for GENERATE_SHOT_KEYFRAME.",
                )
            shot_id = uuid.UUID(raw_shot_id) if isinstance(raw_shot_id, str) else raw_shot_id

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
                    detail="Project hard budget limit exceeded. Keyframe generation dispatch is blocked.",
                )

            default_cfg = getattr(project, "default_config", None) or {}
            mode_cfg = getattr(project, "mode_config", None) or {}
            has_persisted_cost_auth = False
            if isinstance(default_cfg, dict):
                has_persisted_cost_auth = bool(
                    default_cfg.get("auto_cost_authorized") or default_cfg.get("cost_authorized")
                )
            if not has_persisted_cost_auth and isinstance(mode_cfg, dict):
                has_persisted_cost_auth = bool(
                    mode_cfg.get("auto_cost_authorized") or mode_cfg.get("cost_authorized")
                )
            cost_auth = bool(params.get("cost_authorized", False)) or has_persisted_cost_auth

            if actor == "AUTO" and not cost_auth:
                cls.record_audit(
                    db=db,
                    project_id=project_id,
                    from_state=current,
                    to_state=current,
                    action="AUTO_STOPPED_AWAITING_COST_AUTHORIZATION",
                    actor="AUTO",
                    result=OrchestrationActionResult.BLOCKED,
                    reason_code="CHARGEABLE_ACTION_REQUIRES_AUTHORIZATION",
                    detail="Keyframe generation is chargeable and requires explicit cost authorization.",
                )
                db.commit()
                raise HTTPException(
                    status_code=status.HTTP_402_PAYMENT_REQUIRED,
                    detail="Keyframe generation is chargeable and requires explicit cost authorization in AUTO mode.",
                )

            asset, job = KeyframeGenerationService.generate_shot_keyframe(
                db=db,
                project_id=project_id,
                shot_id=shot_id,
                cost_authorized=cost_auth,
                actor=actor,
                provider_specific_params=params.get("provider_specific_params"),
            )
            updated_state = cls.evaluate_state(db, project_id)
            return ExecuteActionResponse(
                success=True,
                action=action_upper,
                from_stage=current,
                to_stage=project.status or current,
                result=OrchestrationActionResult.APPLIED,
                message=f"Keyframe generated successfully for shot '{shot_id}'.",
                orchestration_state=updated_state,
            )

        # ----------------- 4a. Action: START_VIDEO_GENERATION -----------------
        elif action_upper == "START_VIDEO_GENERATION":
            if current not in ("SHOT_PLAN_APPROVED", "IMAGES_GENERATED", "IMAGES_APPROVED"):
                cls.record_audit(
                    db=db,
                    project_id=project_id,
                    from_state=current,
                    to_state=current,
                    action=action_upper,
                    actor=actor,
                    result=OrchestrationActionResult.BLOCKED,
                    reason_code="STAGE_NOT_APPROVED",
                    detail=f"START_VIDEO_GENERATION requires 'SHOT_PLAN_APPROVED' stage, current status is '{current}'.",
                )
                db.commit()
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"START_VIDEO_GENERATION requires 'SHOT_PLAN_APPROVED' stage, current project status is '{current}'.",
                )

            # Check reconciliation safety: fail closed if any job requires reconciliation
            story = db.query(Story).filter(Story.project_id == project_id).first()
            recon_count = (
                db.query(func.count(GenerationJob.id))
                .join(Shot, GenerationJob.shot_id == Shot.id)
                .join(Scene, Shot.scene_id == Scene.id)
                .filter(
                    (Scene.project_id == project_id)
                    | (Scene.story_id == (story.id if story else uuid.uuid4())),
                    GenerationJob.status == "RECONCILIATION_REQUIRED",
                )
                .scalar()
                or 0
            )
            if recon_count > 0:
                cls.record_audit(
                    db=db,
                    project_id=project_id,
                    from_state=current,
                    to_state=current,
                    action=action_upper,
                    actor=actor,
                    result=OrchestrationActionResult.BLOCKED,
                    reason_code="RECONCILIATION_REQUIRED",
                    detail=f"Cannot dispatch generation: {recon_count} job(s) require reconciliation before workflow continuation.",
                )
                db.commit()
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Cannot dispatch generation jobs: {recon_count} job(s) require reconciliation before workflow continuation.",
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

        # ----------------- 4b. Action: CONTINUE_INCOMPLETE -----------------
        elif action_upper == "CONTINUE_INCOMPLETE":
            if current not in ("SHOT_PLAN_APPROVED", "IMAGES_GENERATED", "IMAGES_APPROVED", "VIDEO_IN_PROGRESS"):
                cls.record_audit(
                    db=db,
                    project_id=project_id,
                    from_state=current,
                    to_state=current,
                    action=action_upper,
                    actor=actor,
                    result=OrchestrationActionResult.BLOCKED,
                    reason_code="STAGE_NOT_APPROVED",
                    detail=f"CONTINUE_INCOMPLETE requires 'SHOT_PLAN_APPROVED' or 'VIDEO_IN_PROGRESS' stage, current status is '{current}'.",
                )
                db.commit()
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"CONTINUE_INCOMPLETE requires 'SHOT_PLAN_APPROVED' or 'VIDEO_IN_PROGRESS' stage, current project status is '{current}'.",
                )

            # Check reconciliation safety: fail closed if any job requires reconciliation
            story = db.query(Story).filter(Story.project_id == project_id).first()
            recon_count = (
                db.query(func.count(GenerationJob.id))
                .join(Shot, GenerationJob.shot_id == Shot.id)
                .join(Scene, Shot.scene_id == Scene.id)
                .filter(
                    (Scene.project_id == project_id)
                    | (Scene.story_id == (story.id if story else uuid.uuid4())),
                    GenerationJob.status == "RECONCILIATION_REQUIRED",
                )
                .scalar()
                or 0
            )
            if recon_count > 0:
                cls.record_audit(
                    db=db,
                    project_id=project_id,
                    from_state=current,
                    to_state=current,
                    action=action_upper,
                    actor=actor,
                    result=OrchestrationActionResult.BLOCKED,
                    reason_code="RECONCILIATION_REQUIRED",
                    detail=f"Cannot dispatch generation: {recon_count} job(s) require reconciliation before workflow continuation.",
                )
                db.commit()
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Cannot dispatch generation jobs: {recon_count} job(s) require reconciliation before workflow continuation.",
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
            if current not in ("SHOT_PLAN_APPROVED", "IMAGES_GENERATED", "IMAGES_APPROVED", "VIDEO_IN_PROGRESS"):
                cls.record_audit(
                    db=db,
                    project_id=project_id,
                    from_state=current,
                    to_state=current,
                    action=action_upper,
                    actor=actor,
                    result=OrchestrationActionResult.BLOCKED,
                    reason_code="STAGE_NOT_APPROVED",
                    detail=f"GENERATE_SELECTED_SHOTS requires 'SHOT_PLAN_APPROVED' or 'VIDEO_IN_PROGRESS' stage, current status is '{current}'.",
                )
                db.commit()
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"GENERATE_SELECTED_SHOTS requires 'SHOT_PLAN_APPROVED' or 'VIDEO_IN_PROGRESS' stage, current status is '{current}'.",
                )

            # Check reconciliation safety: fail closed if any job requires reconciliation
            story = db.query(Story).filter(Story.project_id == project_id).first()
            recon_count = (
                db.query(func.count(GenerationJob.id))
                .join(Shot, GenerationJob.shot_id == Shot.id)
                .join(Scene, Shot.scene_id == Scene.id)
                .filter(
                    (Scene.project_id == project_id)
                    | (Scene.story_id == (story.id if story else uuid.uuid4())),
                    GenerationJob.status == "RECONCILIATION_REQUIRED",
                )
                .scalar()
                or 0
            )
            if recon_count > 0:
                cls.record_audit(
                    db=db,
                    project_id=project_id,
                    from_state=current,
                    to_state=current,
                    action=action_upper,
                    actor=actor,
                    result=OrchestrationActionResult.BLOCKED,
                    reason_code="RECONCILIATION_REQUIRED",
                    detail=f"Cannot dispatch generation: {recon_count} job(s) require reconciliation before workflow continuation.",
                )
                db.commit()
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Cannot dispatch generation jobs: {recon_count} job(s) require reconciliation before workflow continuation.",
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
            if current not in ("VIDEO_IN_PROGRESS", "NEEDS_ATTENTION"):
                cls.record_audit(
                    db=db,
                    project_id=project_id,
                    from_state=current,
                    to_state=current,
                    action=action_upper,
                    actor=actor,
                    result=OrchestrationActionResult.BLOCKED,
                    reason_code="STAGE_NOT_APPROVED",
                    detail=f"RETRY_FAILED requires 'VIDEO_IN_PROGRESS' or 'NEEDS_ATTENTION' stage, current status is '{current}'.",
                )
                db.commit()
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"RETRY_FAILED requires 'VIDEO_IN_PROGRESS' or 'NEEDS_ATTENTION' stage, current project status is '{current}'.",
                )

            # Check reconciliation safety: fail closed if any job requires reconciliation
            story = db.query(Story).filter(Story.project_id == project_id).first()
            recon_count = (
                db.query(func.count(GenerationJob.id))
                .join(Shot, GenerationJob.shot_id == Shot.id)
                .join(Scene, Shot.scene_id == Scene.id)
                .filter(
                    (Scene.project_id == project_id)
                    | (Scene.story_id == (story.id if story else uuid.uuid4())),
                    GenerationJob.status == "RECONCILIATION_REQUIRED",
                )
                .scalar()
                or 0
            )
            if recon_count > 0:
                cls.record_audit(
                    db=db,
                    project_id=project_id,
                    from_state=current,
                    to_state=current,
                    action=action_upper,
                    actor=actor,
                    result=OrchestrationActionResult.BLOCKED,
                    reason_code="RECONCILIATION_REQUIRED",
                    detail=f"Cannot dispatch generation: {recon_count} job(s) require reconciliation before workflow continuation.",
                )
                db.commit()
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Cannot dispatch generation jobs: {recon_count} job(s) require reconciliation before workflow continuation.",
                )
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

            # Truthful active shots and production completeness
            story = db.query(Story).filter(Story.project_id == project_id).first()
            scenes_query = (
                db.query(Scene)
                .filter(
                    (Scene.project_id == project_id)
                    | (Scene.story_id == (story.id if story else uuid.uuid4()))
                )
                .all()
            )
            active_scenes = [s for s in scenes_query if not (s.scene_config or {}).get("archived")]
            active_scene_ids = {s.id for s in active_scenes}
            active_shots = (
                db.query(Shot)
                .filter(Shot.scene_id.in_(active_scene_ids), Shot.status != "ARCHIVED")
                .all()
            ) if active_scene_ids else []
            shot_count = len(active_shots)

            active_shot_ids = [s.id for s in active_shots]
            if active_shot_ids:
                job_counts_query = (
                    db.query(GenerationJob.status, func.count(GenerationJob.id))
                    .filter(GenerationJob.shot_id.in_(active_shot_ids))
                    .group_by(GenerationJob.status)
                    .all()
                )
                job_counts = {s: cnt for s, cnt in job_counts_query}
                completed_job_shot_ids = set(
                    s_id for (s_id,) in (
                        db.query(GenerationJob.shot_id)
                        .filter(
                            GenerationJob.shot_id.in_(active_shot_ids),
                            GenerationJob.status == "COMPLETED",
                        )
                        .distinct()
                        .all()
                    )
                )
            else:
                job_counts = {}
                completed_job_shot_ids = set()

            active_jobs = sum(job_counts.get(s, 0) for s in ACTIVE_JOB_STATUSES)
            recon_jobs = job_counts.get("RECONCILIATION_REQUIRED", 0)

            production_ready_shot_ids = {
                s.id for s in active_shots
                if (s.id in completed_job_shot_ids) or (
                    s.shot_type not in ("AI_GENERATED", "MIXED")
                    and (s.source_asset_id is not None or s.status == "COMPLETED")
                )
            }
            production_ready_count = len(production_ready_shot_ids)

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
            if shot_count == 0 or production_ready_count < shot_count:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cannot proceed to final review: only {production_ready_count}/{shot_count} shots are production-ready.",
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
            job_id_param = params.get("job_id")
            resolution = params.get("resolution")
            evidence = params.get("evidence")

            VALID_RESOLUTIONS = {"CONFIRMED_FAILED", "CONFIRMED_COMPLETED", "CONFIRMED_CANCELLED"}

            if not job_id_param or not resolution or not evidence or resolution not in VALID_RESOLUTIONS or not str(evidence).strip():
                cls.record_audit(
                    db=db,
                    project_id=project_id,
                    from_state=current,
                    to_state=current,
                    action=action_upper,
                    actor=actor,
                    result=OrchestrationActionResult.BLOCKED,
                    reason_code="EVIDENCE_REQUIRED",
                    detail="Explicit 'job_id', 'resolution' ('CONFIRMED_FAILED', 'CONFIRMED_COMPLETED', 'CONFIRMED_CANCELLED'), and 'evidence' are required.",
                )
                db.commit()
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Explicit 'job_id', 'resolution' ('CONFIRMED_FAILED', 'CONFIRMED_COMPLETED', 'CONFIRMED_CANCELLED'), and 'evidence' are required to resolve a reconciliation-required job.",
                )

            try:
                target_job_id = uuid.UUID(str(job_id_param))
            except (ValueError, TypeError):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid job_id '{job_id_param}'.")

            target_job = db.get(GenerationJob, target_job_id)
            if not target_job:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"GenerationJob '{target_job_id}' not found.")

            if target_job.status != "RECONCILIATION_REQUIRED":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Job '{target_job_id}' status is '{target_job.status}', not 'RECONCILIATION_REQUIRED'.",
                )

            evidence_str = str(evidence).strip()
            if resolution == "CONFIRMED_FAILED":
                target_job.status = "FAILED"
                target_job.error_message = (
                    (target_job.error_message or "") + f" [Reconciled to FAILED: {evidence_str}]"
                ).strip()
            elif resolution == "CONFIRMED_COMPLETED":
                target_job.status = "COMPLETED"
                output_url = params.get("output_url")
                if output_url:
                    target_job.output_url = output_url
                target_job.error_message = (
                    (target_job.error_message or "") + f" [Reconciled to COMPLETED: {evidence_str}]"
                ).strip()
            elif resolution == "CONFIRMED_CANCELLED":
                target_job.status = "CANCELLED"
                target_job.error_message = (
                    (target_job.error_message or "") + f" [Reconciled to CANCELLED: {evidence_str}]"
                ).strip()

            cls.record_audit(
                db=db,
                project_id=project_id,
                from_state=current,
                to_state=current,
                action=action_upper,
                actor=actor,
                result=OrchestrationActionResult.APPLIED,
                reason_code=resolution,
                detail=f"Job {target_job.id} resolved to {target_job.status}. Evidence: {evidence_str}",
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

            story = db.query(Story).filter(Story.project_id == project_id).first()

            if action_upper == "REVISE_STORY":
                if video_mode != "STORY" or current not in ("STORY_GENERATED", "STORY_APPROVED"):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Cannot revise story from stage '{current}' in {video_mode} mode.",
                    )
                new_stage = "DRAFT"
                # Soft-archive downstream scenes and shots
                if story:
                    for sc in list(story.scenes):
                        if not sc.is_locked:
                            sc.scene_config = dict(sc.scene_config or {})
                            sc.scene_config["archived"] = True
                            for sh in sc.shots:
                                if not sh.is_locked:
                                    sh.status = "ARCHIVED"

            elif action_upper == "REVISE_STORYBOARD":
                if current not in ("STORYBOARD_GENERATED", "STORYBOARD_APPROVED"):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Cannot revise storyboard from stage '{current}'.",
                    )
                new_stage = "STORY_APPROVED" if video_mode == "STORY" else "DRAFT"
                # Soft-archive downstream scenes and shots
                scenes_to_clear = (
                    db.query(Scene)
                    .filter(
                        (Scene.project_id == project_id)
                        | (Scene.story_id == (story.id if story else uuid.uuid4()))
                    )
                    .all()
                )
                for sc in scenes_to_clear:
                    if not sc.is_locked:
                        sc.scene_config = dict(sc.scene_config or {})
                        sc.scene_config["archived"] = True
                        for sh in sc.shots:
                            if not sh.is_locked:
                                sh.status = "ARCHIVED"

            elif action_upper == "REVISE_SHOT_PLAN":
                if current not in ("SHOT_PLAN_GENERATED", "SHOT_PLAN_APPROVED", "IMAGES_GENERATED", "IMAGES_APPROVED"):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Cannot revise shot plan from stage '{current}'.",
                    )
                new_stage = "STORYBOARD_APPROVED" if video_mode != "LOOP" else "DRAFT"
                # Soft-archive downstream shots
                scenes_to_clear = (
                    db.query(Scene)
                    .filter(
                        (Scene.project_id == project_id)
                        | (Scene.story_id == (story.id if story else uuid.uuid4()))
                    )
                    .all()
                )
                for sc in scenes_to_clear:
                    for sh in sc.shots:
                        if not sh.is_locked:
                            sh.status = "ARCHIVED"

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

        # ----------------- 11. Audio Actions -----------------
        elif action_upper == "GENERATE_AUDIO_PLAN":
            from app.services.audio_production import AudioProductionService
            plan = AudioProductionService.generate_audio_plan(db=db, project_id=project_id)
            project.status = "AUDIO_PLAN_GENERATED"
            cls.record_audit(
                db=db,
                project_id=project_id,
                from_state=current,
                to_state="AUDIO_PLAN_GENERATED",
                action="GENERATE_AUDIO_PLAN",
                actor=actor,
                result=OrchestrationActionResult.APPLIED,
                detail=f"Audio plan generated (version {plan.version}).",
            )
            db.commit()

        elif action_upper in (
            "START_AUDIO_GENERATION",
            "GENERATE_ALL_VO",
            "ASSIGN_BGM",
            "ASSIGN_SFX",
            "ASSIGN_AMBIENCE",
            "CONTINUE_INCOMPLETE_AUDIO",
            "RETRY_FAILED_AUDIO",
        ):
            from app.services.audio_production import AudioProductionService
            cost_auth = bool(params.get("cost_authorized", False))
            provider_name = params.get("provider_name")
            batch_action = "CONTINUE_INCOMPLETE_AUDIO" if action_upper == "START_AUDIO_GENERATION" else action_upper
            res = AudioProductionService.execute_audio_batch(
                db=db,
                project_id=project_id,
                action=batch_action,
                cost_authorized=cost_auth,
                actor=actor,
                provider_name=provider_name,
            )
            project.status = "AUDIO_IN_PROGRESS"
            cls.record_audit(
                db=db,
                project_id=project_id,
                from_state=current,
                to_state="AUDIO_IN_PROGRESS",
                action=action_upper,
                actor=actor,
                result=OrchestrationActionResult.APPLIED,
                detail=f"Processed: {res['processed']}, succeeded: {res['succeeded']}, failed: {res['failed']}.",
            )
            db.commit()

        elif action_upper == "AUTO_MIX_AUDIO":
            from app.services.audio_production import AudioProductionService
            mix_res = AudioProductionService.compute_auto_mix(db=db, project_id=project_id)
            project.status = "AUDIO_MIX_READY"
            cls.record_audit(
                db=db,
                project_id=project_id,
                from_state=current,
                to_state="AUDIO_MIX_READY",
                action="AUTO_MIX_AUDIO",
                actor=actor,
                result=OrchestrationActionResult.APPLIED,
                detail=f"Auto-mix computed for {mix_res['total_tracks']} tracks.",
            )
            db.commit()

        elif action_upper == "PROCEED_TO_ASSEMBLY":
            project.status = "READY_FOR_ASSEMBLY"
            cls.record_audit(
                db=db,
                project_id=project_id,
                from_state=current,
                to_state="READY_FOR_ASSEMBLY",
                action="PROCEED_TO_ASSEMBLY",
                actor=actor,
                result=OrchestrationActionResult.APPLIED,
                detail="Advanced to timeline assembly stage.",
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
        auto_cost_authorized: Optional[bool] = None,
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

        if auto_cost_authorized is not None:
            cfg = dict(project.default_config or {})
            cfg["auto_cost_authorized"] = auto_cost_authorized
            project.default_config = cfg
            cls.record_audit(
                db=db,
                project_id=project_id,
                from_state=current,
                to_state=current,
                action="UPDATE_AUTO_COST_AUTHORIZATION",
                actor=actor,
                result=OrchestrationActionResult.APPLIED,
                detail=f"Set auto_cost_authorized to {auto_cost_authorized}",
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
