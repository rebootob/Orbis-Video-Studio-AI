import uuid
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.project import Project
from app.models.scene import Scene
from app.models.shot import Shot
from app.models.story import Story, utc_now
from app.models.story_version import StoryVersion
from app.schemas.orchestrator import (
    ExecuteActionResponse,
    OrchestrationActionModel,
    OrchestrationActionResult,
    OrchestrationActionType,
    OrchestrationStateResponse,
)
from app.services.lock_machine import LockMachineService
from app.services.production_orchestrator import ProductionOrchestrator


MANUAL_SUBMISSION_ACTIONS = {
    "SUBMIT_MANUAL_STORY",
    "SUBMIT_MANUAL_STORYBOARD",
    "SUBMIT_MANUAL_SHOT_PLAN",
}


class ManualCreativeService:
    """Zero-provider creative authoring and auditable manual stage submission.

    This service intentionally does not import or resolve CreativeProvider. Manual
    authoring uses the canonical Project -> Story -> Scene -> Shot entities and
    canonical ProductionOrchestrator audit/state primitives.
    """

    @staticmethod
    def _get_project(db: Session, project_id: uuid.UUID) -> Project:
        project = db.get(Project, project_id)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project '{project_id}' not found",
            )
        return project

    @staticmethod
    def _require_manual(project: Project) -> None:
        if (project.automation_mode or "MANUAL").upper() != "MANUAL":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Manual creative submission actions require automation_mode=MANUAL.",
            )

    @staticmethod
    def _active_scenes(db: Session, project: Project) -> List[Scene]:
        story = db.query(Story).filter(Story.project_id == project.id).first()
        story_id = story.id if story else None
        query = db.query(Scene).filter(Scene.project_id == project.id)
        if story_id is not None:
            query = db.query(Scene).filter(
                (Scene.project_id == project.id) | (Scene.story_id == story_id)
            )
        scenes = query.order_by(Scene.scene_number).all()
        return [s for s in scenes if not (s.scene_config or {}).get("archived")]

    @classmethod
    def _active_shots(cls, db: Session, project: Project) -> List[Shot]:
        scene_ids = [s.id for s in cls._active_scenes(db, project)]
        if not scene_ids:
            return []
        return (
            db.query(Shot)
            .filter(Shot.scene_id.in_(scene_ids), Shot.status != "ARCHIVED")
            .order_by(Shot.shot_number)
            .all()
        )

    @staticmethod
    def _story_validation(story: Optional[Story]) -> Tuple[bool, Optional[str]]:
        if not story:
            return False, "Create and save a manual Story first."
        if story.is_locked:
            return False, "Story is locked. Explicitly unlock it before submission."
        if not (story.title or "").strip():
            return False, "Story title is required."
        if not ((story.logline or "").strip() or (story.synopsis or "").strip()):
            return False, "Story requires a logline or synopsis before submission."
        return True, None

    @classmethod
    def _storyboard_validation(
        cls, db: Session, project: Project
    ) -> Tuple[bool, Optional[str]]:
        scenes = cls._active_scenes(db, project)
        if not scenes:
            return False, "Add at least one Scene manually before submission."
        for scene in scenes:
            if scene.is_locked:
                return False, f"Scene #{scene.scene_number} is locked."
            if not any(
                (value or "").strip()
                for value in (scene.heading, scene.description, scene.setting)
                if isinstance(value, str)
            ):
                return False, (
                    f"Scene #{scene.scene_number} requires heading, description, or setting."
                )
        return True, None

    @classmethod
    def _shot_plan_validation(
        cls, db: Session, project: Project
    ) -> Tuple[bool, Optional[str]]:
        shots = cls._active_shots(db, project)
        if not shots:
            return False, "Add at least one Shot manually before submission."
        for shot in shots:
            try:
                LockMachineService.check_mutation_allowed(db, "SHOT", shot.id)
            except HTTPException as exc:
                return False, str(exc.detail)
            if not shot.duration_seconds or shot.duration_seconds <= 0:
                return False, f"Shot #{shot.shot_number} requires a positive duration."
            if shot.shot_type in ("AI_GENERATED", "MIXED") and not any(
                (value or "").strip()
                for value in (shot.visual_prompt, shot.image_prompt, shot.video_prompt)
                if isinstance(value, str)
            ):
                return False, (
                    f"Shot #{shot.shot_number} requires a visual/image/video prompt."
                )
            if shot.shot_type not in ("AI_GENERATED", "MIXED"):
                if shot.source_asset_id is None and not any(
                    (value or "").strip()
                    for value in (shot.visual_prompt, shot.video_prompt)
                    if isinstance(value, str)
                ):
                    return False, (
                        f"Imported Shot #{shot.shot_number} requires a source asset or descriptive prompt."
                    )
        return True, None

    @classmethod
    def upsert_story(
        cls,
        db: Session,
        project_id: uuid.UUID,
        payload: Dict[str, Any],
        actor: str = "USER",
    ) -> Story:
        project = cls._get_project(db, project_id)
        cls._require_manual(project)
        if (project.video_mode or "STORY").upper() != "STORY":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Manual Story authoring is only applicable to STORY mode.",
            )
        if project.status != "DRAFT":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Manual Story editing is allowed only in DRAFT. Use the canonical revision "
                    "flow before editing an already submitted/approved Story."
                ),
            )

        story = db.query(Story).filter(Story.project_id == project_id).first()
        action = "MANUAL_STORY_CREATE"
        if story:
            LockMachineService.check_mutation_allowed(db, "SCRIPT", story.id)
            previous_version = story.version_number or 1
            db.add(
                StoryVersion(
                    id=uuid.uuid4(),
                    story_id=story.id,
                    project_id=project_id,
                    version_number=previous_version,
                    title=story.title,
                    logline=story.logline,
                    synopsis=story.synopsis,
                    tone=story.tone,
                    target_duration_seconds=story.target_duration_seconds,
                    language=story.language,
                    status="SUPERSEDED",
                    created_at=story.updated_at or utc_now(),
                )
            )
            story.version_number = previous_version + 1
            action = "MANUAL_STORY_UPDATE"
        else:
            story = Story(
                id=uuid.uuid4(),
                project_id=project_id,
                version_number=1,
                status="DRAFT",
            )
            db.add(story)

        for field in (
            "title",
            "logline",
            "synopsis",
            "tone",
            "target_duration_seconds",
            "language",
        ):
            if field in payload:
                setattr(story, field, payload[field])
        story.status = "DRAFT"

        ProductionOrchestrator.record_audit(
            db=db,
            project_id=project_id,
            from_state="DRAFT",
            to_state="DRAFT",
            action=action,
            actor=actor,
            result=OrchestrationActionResult.APPLIED,
            reason_code="MANUAL_CREATIVE_EDIT",
            detail=f"Manual Story version {story.version_number} saved without CreativeProvider dispatch.",
        )
        db.commit()
        db.refresh(story)
        return story

    @staticmethod
    def handles_action(action: str) -> bool:
        return (action or "").upper() in MANUAL_SUBMISSION_ACTIONS

    @classmethod
    def execute_submission(
        cls,
        db: Session,
        project_id: uuid.UUID,
        action: str,
        actor: str = "USER",
    ) -> ExecuteActionResponse:
        project = cls._get_project(db, project_id)
        cls._require_manual(project)
        action_upper = (action or "").upper()
        if action_upper not in MANUAL_SUBMISSION_ACTIONS:
            raise HTTPException(status_code=400, detail=f"Unsupported manual action '{action}'.")

        mode = (project.video_mode or "STORY").upper()
        current = project.status or "DRAFT"

        if action_upper == "SUBMIT_MANUAL_STORY":
            if mode != "STORY" or current != "DRAFT":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Manual Story submission requires STORY mode at DRAFT stage.",
                )
            story = db.query(Story).filter(Story.project_id == project_id).first()
            valid, reason = cls._story_validation(story)
            if not valid:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=reason)
            story.status = "GENERATED"
            target = "STORY_GENERATED"

        elif action_upper == "SUBMIT_MANUAL_STORYBOARD":
            allowed_current = "STORY_APPROVED" if mode == "STORY" else "DRAFT"
            if mode not in ("STORY", "SHORT", "SCENE") or current != allowed_current:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        f"Manual Storyboard submission is not valid for mode '{mode}' "
                        f"at stage '{current}'."
                    ),
                )
            valid, reason = cls._storyboard_validation(db, project)
            if not valid:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=reason)
            target = "STORYBOARD_GENERATED"

        else:  # SUBMIT_MANUAL_SHOT_PLAN
            if mode in ("STORY", "SHORT", "SCENE"):
                allowed_current = "STORYBOARD_APPROVED"
            elif mode == "LOOP":
                allowed_current = "DRAFT"
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Unsupported Video Mode '{mode}' for manual Shot Plan submission.",
                )
            if current != allowed_current:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        f"Manual Shot Plan submission requires stage '{allowed_current}', "
                        f"current stage is '{current}'."
                    ),
                )
            valid, reason = cls._shot_plan_validation(db, project)
            if not valid:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=reason)
            target = "SHOT_PLAN_GENERATED"

        project.status = target
        ProductionOrchestrator.record_audit(
            db=db,
            project_id=project_id,
            from_state=current,
            to_state=target,
            action=action_upper,
            actor=actor,
            result=OrchestrationActionResult.APPLIED,
            reason_code="MANUAL_CREATIVE_SUBMITTED",
            detail="Manual creative structure validated and submitted without CreativeProvider dispatch.",
        )
        db.commit()

        state = cls.overlay_state(db, ProductionOrchestrator.evaluate_state(db, project_id))
        return ExecuteActionResponse(
            success=True,
            action=action_upper,
            from_stage=current,
            to_stage=target,
            result=OrchestrationActionResult.APPLIED,
            message=f"Manual creative stage submitted successfully: '{target}'.",
            orchestration_state=state,
        )

    @classmethod
    def overlay_state(
        cls, db: Session, state: OrchestrationStateResponse
    ) -> OrchestrationStateResponse:
        project = cls._get_project(db, state.project_id)
        if (project.automation_mode or "MANUAL").upper() != "MANUAL":
            return state

        mode = (project.video_mode or "STORY").upper()
        stage = state.current_stage
        original_recommended = state.recommended_action

        action: Optional[str] = None
        label: Optional[str] = None
        description: Optional[str] = None
        valid = True
        reason: Optional[str] = None

        if mode == "STORY" and stage == "DRAFT":
            action = "SUBMIT_MANUAL_STORY"
            label = "Submit Manual Story for Review"
            description = "Save your Story/Script manually, then submit it for human review without CreativeProvider cost."
            story = db.query(Story).filter(Story.project_id == project.id).first()
            valid, reason = cls._story_validation(story)
        elif mode == "STORY" and stage == "STORY_APPROVED":
            action = "SUBMIT_MANUAL_STORYBOARD"
            label = "Submit Manual Storyboard for Review"
            description = "Build/edit Scene cards manually, then submit the Storyboard without CreativeProvider cost."
            valid, reason = cls._storyboard_validation(db, project)
        elif mode in ("SHORT", "SCENE") and stage == "DRAFT":
            action = "SUBMIT_MANUAL_STORYBOARD"
            label = "Submit Manual Storyboard for Review"
            description = "Build Scene structure manually, then submit it without CreativeProvider cost."
            valid, reason = cls._storyboard_validation(db, project)
        elif mode in ("STORY", "SHORT", "SCENE") and stage == "STORYBOARD_APPROVED":
            action = "SUBMIT_MANUAL_SHOT_PLAN"
            label = "Submit Manual Shot Plan for Review"
            description = "Build/edit detailed Shot prompts, camera and timing manually, then submit without CreativeProvider cost."
            valid, reason = cls._shot_plan_validation(db, project)
        elif mode == "LOOP" and stage == "DRAFT":
            action = "SUBMIT_MANUAL_SHOT_PLAN"
            label = "Submit Manual Loop Shot Plan for Review"
            description = "Build the Loop Shot plan manually, then submit without CreativeProvider cost."
            valid, reason = cls._shot_plan_validation(db, project)

        if not action:
            return state

        manual_action = OrchestrationActionModel(
            action=action,
            display_name=label or action,
            description=description or "Submit manually authored creative structure.",
            action_type=OrchestrationActionType.APPROVAL,
            is_chargeable=False,
            is_blocked=not valid,
            blocked_reason=reason if not valid else None,
        )

        secondary = list(state.available_actions)
        if original_recommended and original_recommended.action != action:
            if all(a.action != original_recommended.action for a in secondary):
                secondary.insert(0, original_recommended)
        state.recommended_action = manual_action
        state.available_actions = secondary
        return state
