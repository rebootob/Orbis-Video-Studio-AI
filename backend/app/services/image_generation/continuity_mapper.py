"""Continuity and Reference Library mapping for keyframe image generation."""
import uuid
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session

from app.models.project import Project
from app.models.shot import Shot
from app.models.scene import Scene
from app.models.asset import Asset
from app.models.reference_library import (
    ProjectReference,
    CharacterBible,
    LocationBible,
    StyleBible,
    BrandBible,
)
from app.models.asset_lock import AssetLock
from app.providers.image.base import ImageGenerationParams, ReferenceImageInput
from app.services.reference_library.context_builder import ReferenceContextBuilder


class ContinuityMapper:
    """Maps project reference bibles and shot visual directives into provider-neutral ImageGenerationParams."""

    @classmethod
    def check_shot_locked(cls, db: Session, project_id: uuid.UUID, shot: Shot) -> Tuple[bool, Optional[str]]:
        """Evaluate if shot is locked directly or via hierarchical parent locks."""
        project = db.get(Project, project_id)
        if project and getattr(project, "is_locked", False):
            return True, "PROJECT_LOCKED"

        if shot.is_locked:
            return True, "SHOT_LOCKED"

        # Check DB AssetLock table
        locks = (
            db.query(AssetLock.entity_type, AssetLock.entity_id)
            .filter(
                AssetLock.project_id == project_id,
                AssetLock.is_locked == True,  # noqa: E712
            )
            .all()
        )
        locked_shots = {lid for etype, lid in locks if etype == "SHOT"}
        locked_scenes = {lid for etype, lid in locks if etype == "SCENE"}
        locked_scripts = {lid for etype, lid in locks if etype == "SCRIPT"}

        if shot.id in locked_shots:
            return True, "SHOT_LOCKED"

        scene = db.get(Scene, shot.scene_id)
        if scene:
            if getattr(scene, "is_locked", False) or scene.id in locked_scenes:
                return True, "SCENE_LOCKED"
            if scene.story_id and scene.story_id in locked_scripts:
                return True, "SCRIPT_LOCKED"

        return False, None

    @classmethod
    def map_shot_to_image_params(
        cls,
        db: Session,
        project_id: uuid.UUID,
        shot: Shot,
        provider_specific_params: Optional[Dict[str, Any]] = None,
    ) -> ImageGenerationParams:
        """Construct ImageGenerationParams combining shot prompts and locked continuity references."""
        project = db.get(Project, project_id)
        aspect_ratio = (project.preferred_aspect_ratio if project and project.preferred_aspect_ratio in ("16:9", "9:16", "1:1", "4:3", "3:4") else "16:9")

        # 1. Base Prompt Construction
        prompt_parts: List[str] = []
        primary_prompt = (shot.image_prompt or shot.visual_prompt or "").strip()
        if primary_prompt:
            prompt_parts.append(primary_prompt)
        else:
            # Fallback composition from structured shot fields
            elements = []
            if shot.subject:
                elements.append(f"Subject: {shot.subject}")
            if shot.action:
                elements.append(f"Action: {shot.action}")
            if shot.camera:
                elements.append(f"Camera: {shot.camera}")
            if elements:
                prompt_parts.append("; ".join(elements))
            else:
                prompt_parts.append(f"Cinematic keyframe for shot {shot.shot_number}")

        # 2. Extract Continuity Reference Context
        ref_context = ReferenceContextBuilder.build_context(db, project_id)

        # Style Bible continuity
        style = ref_context.get("style")
        negative_prompt: Optional[str] = None
        if style:
            style_parts = []
            if style.get("visual_style"):
                style_parts.append(f"Style: {style['visual_style']}")
            if style.get("lighting_style"):
                style_parts.append(f"Lighting: {style['lighting_style']}")
            if style.get("color_direction"):
                style_parts.append(f"Color: {style['color_direction']}")
            if style_parts:
                prompt_parts.append(f"[{'; '.join(style_parts)}]")

            if style.get("negative_constraints"):
                negative_prompt = str(style["negative_constraints"]).strip()

        # Brand Bible continuity (if relevant)
        brand = ref_context.get("brand")
        if brand and brand.get("brand_colors"):
            prompt_parts.append(f"[Brand Colors: {brand['brand_colors']}]")

        full_prompt = " -- ".join(prompt_parts)

        # 3. Reference Images (from character/location/style bibles with uploaded assets)
        reference_images: List[ReferenceImageInput] = []
        character_bibles = (
            db.query(CharacterBible)
            .filter(CharacterBible.project_id == project_id, CharacterBible.reference_asset_id.isnot(None))
            .all()
        )
        for cb in character_bibles:
            if cb.reference_asset_id:
                asset = db.get(Asset, cb.reference_asset_id)
                if asset:
                    reference_images.append(
                        ReferenceImageInput(
                            type="character",
                            url=f"/assets/{asset.id}/download",
                            weight=1.0,
                        )
                    )

        location_bibles = (
            db.query(LocationBible)
            .filter(LocationBible.project_id == project_id, LocationBible.reference_asset_id.isnot(None))
            .all()
        )
        for lb in location_bibles:
            if lb.reference_asset_id:
                asset = db.get(Asset, lb.reference_asset_id)
                if asset:
                    reference_images.append(
                        ReferenceImageInput(
                            type="location",
                            url=f"/assets/{asset.id}/download",
                            weight=0.8,
                        )
                    )

        return ImageGenerationParams(
            shot_id=str(shot.id),
            prompt=full_prompt,
            negative_prompt=negative_prompt,
            aspect_ratio=aspect_ratio,
            seed=None,
            reference_images=reference_images if reference_images else None,
            provider_specific_params=provider_specific_params,
        )
