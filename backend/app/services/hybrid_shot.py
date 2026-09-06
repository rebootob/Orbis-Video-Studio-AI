import uuid
from typing import Optional, Dict, Any
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.shot import Shot
from app.models.scene import Scene
from app.models.project import Project
from app.models.asset import Asset
from app.services.video_modes import validate_shot_type
from app.services.lock_machine import LockMachineService
from app.schemas.shot import ShotCreateRequest, ShotUpdateRequest, EffectiveShotConfigResponse


class HybridShotService:
    @classmethod
    def get_scene_project_id(cls, db: Session, scene: Scene) -> Optional[uuid.UUID]:
        if scene.project_id:
            return scene.project_id
        if scene.story and scene.story.project_id:
            return scene.story.project_id
        if scene.story_id:
            from app.models.story import Story
            story = db.get(Story, scene.story_id)
            if story:
                return story.project_id
        return None

    @classmethod
    def create_shot(
        cls,
        db: Session,
        scene_id: uuid.UUID,
        request: ShotCreateRequest,
    ) -> Shot:
        scene = db.get(Scene, scene_id)
        if not scene:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Scene '{scene_id}' not found",
            )

        # Check if parent Scene (or Script) is locked
        LockMachineService.check_mutation_allowed(db, "SCENE", scene_id)

        # Validate shot type
        norm_type = validate_shot_type(request.shot_type)

        project_id = cls.get_scene_project_id(db, scene)

        # Validate source asset ownership context if provided
        if request.source_asset_id:
            asset = db.get(Asset, request.source_asset_id)
            if not asset:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Source Asset '{request.source_asset_id}' not found",
                )
            if project_id is not None and asset.project_id != project_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Asset '{request.source_asset_id}' belongs to Project '{asset.project_id}', not Scene Project '{project_id}'",
                )

        shot = Shot(
            id=uuid.uuid4(),
            scene_id=scene_id,
            shot_number=request.shot_number,
            shot_type=norm_type,
            source_asset_id=request.source_asset_id,
            source_metadata=request.source_metadata,
            provider_config=request.provider_config,
            visual_prompt=request.visual_prompt,
            image_prompt=request.image_prompt,
            video_prompt=request.video_prompt,
            camera=request.camera,
            subject=request.subject,
            action=request.action,
            duration_seconds=request.duration_seconds,
            is_locked=False,
            status="PENDING",
        )
        db.add(shot)
        db.commit()
        db.refresh(shot)
        return shot

    @classmethod
    def update_shot(
        cls,
        db: Session,
        shot_id: uuid.UUID,
        request: ShotUpdateRequest,
    ) -> Shot:
        shot = db.get(Shot, shot_id)
        if not shot:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Shot '{shot_id}' not found",
            )

        # Check if shot or parent scene/script is locked
        LockMachineService.check_mutation_allowed(db, "SHOT", shot_id)

        if request.shot_type is not None:
            shot.shot_type = validate_shot_type(request.shot_type)

        if request.source_asset_id is not None:
            scene = shot.scene
            project_id = cls.get_scene_project_id(db, scene) if scene else None
            asset = db.get(Asset, request.source_asset_id)
            if not asset:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Source Asset '{request.source_asset_id}' not found",
                )
            if project_id is not None and asset.project_id != project_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Asset '{request.source_asset_id}' belongs to Project '{asset.project_id}', not Scene Project '{project_id}'",
                )
            shot.source_asset_id = request.source_asset_id

        if request.source_metadata is not None:
            shot.source_metadata = request.source_metadata
        if request.provider_config is not None:
            shot.provider_config = request.provider_config
        if request.visual_prompt is not None:
            shot.visual_prompt = request.visual_prompt
        if request.image_prompt is not None:
            shot.image_prompt = request.image_prompt
        if request.video_prompt is not None:
            shot.video_prompt = request.video_prompt
        if request.camera is not None:
            shot.camera = request.camera
        if request.subject is not None:
            shot.subject = request.subject
        if request.action is not None:
            shot.action = request.action
        if request.duration_seconds is not None:
            shot.duration_seconds = request.duration_seconds

        db.commit()
        db.refresh(shot)
        return shot

    @classmethod
    def resolve_inherited_config(
        cls,
        db: Session,
        shot_id: uuid.UUID,
    ) -> EffectiveShotConfigResponse:
        shot = db.get(Shot, shot_id)
        if not shot:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Shot '{shot_id}' not found",
            )
        scene = shot.scene
        if not scene:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Scene for Shot '{shot_id}' not found",
            )
        project_id = cls.get_scene_project_id(db, scene)
        project = db.get(Project, project_id) if project_id else None

        # 1. Resolve aspect ratio
        shot_pcfg = shot.provider_config or {}
        scene_cfg = scene.scene_config or {}
        proj_mode_cfg = (project.mode_config or {}) if project else {}
        proj_def_cfg = (project.default_config or {}) if project else {}

        resolved_aspect_ratio = (
            shot_pcfg.get("aspect_ratio")
            or scene_cfg.get("aspect_ratio")
            or scene_cfg.get("preferred_aspect_ratio")
            or (project.preferred_aspect_ratio if project else None)
            or "16:9"
        )

        # 2. Resolve duration
        resolved_duration = (
            shot.duration_seconds
            or scene.duration_seconds
            or (project.target_duration_seconds if project else None)
            or 4.0
        )

        # 3. Deterministic config merge: Project -> Scene -> Shot
        merged_config: Dict[str, Any] = {}
        merged_config.update(proj_def_cfg)
        merged_config.update(proj_mode_cfg)
        merged_config.update(scene_cfg)
        merged_config.update(shot_pcfg)

        merged_config["resolved_aspect_ratio"] = resolved_aspect_ratio
        merged_config["resolved_duration_seconds"] = resolved_duration

        return EffectiveShotConfigResponse(
            shot_id=shot.id,
            scene_id=scene.id,
            project_id=project_id or uuid.UUID(int=0),
            resolved_aspect_ratio=resolved_aspect_ratio,
            resolved_duration_seconds=resolved_duration,
            effective_config=merged_config,
        )
