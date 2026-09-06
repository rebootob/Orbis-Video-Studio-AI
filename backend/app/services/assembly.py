import uuid
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from fastapi import HTTPException, status

from app.models.project import Project
from app.models.scene import Scene
from app.models.shot import Shot
from app.models.asset import Asset
from app.models.audio_clip import AudioClip
from app.models.assembly import (
    AssemblyTimeline,
    AssemblyScene,
    AssemblyShotPlacement,
    TimelineCheckpoint,
    TimelineAudit,
)
from app.schemas.assembly import (
    AssemblyTimelineRead,
    AssemblySceneRead,
    AssemblyShotPlacementRead,
    AudioClipSummaryRead,
    AssemblyBlocker,
    RecommendedFix,
)


def utc_now():
    return datetime.now(timezone.utc)


def _to_uuid(val: Any) -> uuid.UUID:
    if isinstance(val, uuid.UUID):
        return val
    return uuid.UUID(str(val))


class AssemblyService:

    @staticmethod
    def get_active_timeline(db: Session, project_id: str) -> Optional[AssemblyTimeline]:
        p_uuid = _to_uuid(project_id)
        return db.query(AssemblyTimeline).filter(
            AssemblyTimeline.project_id == p_uuid,
            AssemblyTimeline.is_active == True
        ).first()

    @classmethod
    def get_or_create_active_timeline(cls, db: Session, project_id: str) -> AssemblyTimeline:
        timeline = cls.get_active_timeline(db, project_id)
        if not timeline:
            timeline = cls.auto_assemble_timeline(db, project_id)
        return timeline

    @classmethod
    def auto_assemble_timeline(cls, db: Session, project_id: str, actor: str = "system") -> AssemblyTimeline:
        p_uuid = _to_uuid(project_id)
        project = db.query(Project).filter(Project.id == p_uuid).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        existing_timeline = cls.get_active_timeline(db, project_id)
        new_version = (existing_timeline.version + 1) if existing_timeline else 1

        if existing_timeline:
            existing_timeline.is_active = False

        # Create new timeline
        timeline_id = uuid.uuid4()
        timeline = AssemblyTimeline(
            id=timeline_id,
            project_id=p_uuid,
            version=new_version,
            status="DRAFT",
            is_active=True,
        )
        db.add(timeline)
        db.flush()

        # Fetch scenes & shots ordered
        scenes = db.query(Scene).filter(Scene.project_id == p_uuid).order_by(Scene.scene_number.asc()).all()
        scene_ids = [s.id for s in scenes]

        shots = []
        if scene_ids:
            shots = db.query(Shot).filter(Shot.scene_id.in_(scene_ids)).order_by(Shot.shot_number.asc()).all()

        # Fetch visual assets for project in one set-based query
        assets = db.query(Asset).filter(Asset.project_id == p_uuid).all()
        asset_map: Dict[str, Asset] = {str(a.id): a for a in assets}

        # Build assembly scenes and placements
        for scene_idx, scene in enumerate(scenes):
            assembly_scene = AssemblyScene(
                id=uuid.uuid4(),
                timeline_id=timeline.id,
                scene_id=scene.id,
                scene_order=scene_idx,
            )
            db.add(assembly_scene)
            db.flush()

            scene_shots = [sh for sh in shots if sh.scene_id == scene.id]
            for shot_idx, shot in enumerate(scene_shots):
                selected_asset_id: Optional[uuid.UUID] = None
                source_type = "MISSING"
                trim_in = 0.0
                trim_out: Optional[float] = None
                effective_duration = 4.0
                still_duration = 4.0

                # 1. Approved/current video asset for shot
                if shot.source_asset_id and str(shot.source_asset_id) in asset_map:
                    v_asset = asset_map[str(shot.source_asset_id)]
                    selected_asset_id = v_asset.id
                    source_type = "VIDEO"
                    trim_out = 4.0
                    effective_duration = 4.0
                # 2. Keyframe or Image asset fallback for shot
                elif shot.keyframe_asset_id and str(shot.keyframe_asset_id) in asset_map:
                    k_asset = asset_map[str(shot.keyframe_asset_id)]
                    selected_asset_id = k_asset.id
                    source_type = "KEYFRAME"
                    still_duration = 4.0
                    effective_duration = 4.0

                placement = AssemblyShotPlacement(
                    id=uuid.uuid4(),
                    timeline_id=timeline.id,
                    assembly_scene_id=assembly_scene.id,
                    scene_id=scene.id,
                    shot_id=shot.id,
                    shot_order=shot_idx,
                    visual_asset_id=selected_asset_id,
                    source_type=source_type,
                    trim_in=trim_in,
                    trim_out=trim_out,
                    effective_duration=effective_duration,
                    still_duration=still_duration,
                    transition_to_next="CUT",
                    is_locked=False,
                    version=1,
                )
                db.add(placement)

        audit = TimelineAudit(
            id=uuid.uuid4(),
            project_id=p_uuid,
            timeline_id=timeline.id,
            action="AUTO_ASSEMBLE",
            actor=actor,
            change_reason="Automated initial timeline assembly",
        )
        db.add(audit)
        db.commit()
        db.refresh(timeline)
        return timeline

    @classmethod
    def reorder_scenes(cls, db: Session, project_id: str, scene_orders: List[Tuple[str, int]], actor: str = "USER") -> AssemblyTimeline:
        timeline = cls.get_active_timeline(db, project_id)
        if not timeline:
            timeline = cls.auto_assemble_timeline(db, project_id)

        scene_map = {str(s.scene_id): s for s in timeline.scenes}
        for scene_id, order in scene_orders:
            if scene_id in scene_map:
                scene_map[scene_id].scene_order = order

        timeline.version += 1
        audit = TimelineAudit(
            id=uuid.uuid4(),
            project_id=_to_uuid(project_id),
            timeline_id=timeline.id,
            action="REORDER_SCENES",
            actor=actor,
            change_reason=f"Reordered {len(scene_orders)} scenes",
        )
        db.add(audit)
        db.commit()
        db.refresh(timeline)
        return timeline

    @classmethod
    def reorder_shots_in_scene(cls, db: Session, project_id: str, scene_id: str, shot_orders: List[Tuple[str, int]], actor: str = "USER") -> AssemblyTimeline:
        timeline = cls.get_active_timeline(db, project_id)
        if not timeline:
            timeline = cls.auto_assemble_timeline(db, project_id)

        sc_uuid = _to_uuid(scene_id)
        assembly_scene = db.query(AssemblyScene).filter(
            AssemblyScene.timeline_id == timeline.id,
            AssemblyScene.scene_id == sc_uuid
        ).first()

        if not assembly_scene:
            raise HTTPException(status_code=404, detail="Scene placement not found in timeline")

        placement_map = {str(p.shot_id): p for p in assembly_scene.shot_placements}
        for shot_id, order in shot_orders:
            if shot_id in placement_map:
                placement_map[shot_id].shot_order = order

        timeline.version += 1
        audit = TimelineAudit(
            id=uuid.uuid4(),
            project_id=_to_uuid(project_id),
            timeline_id=timeline.id,
            action="REORDER_SHOTS",
            actor=actor,
            change_reason=f"Reordered shots in scene {scene_id}",
        )
        db.add(audit)
        db.commit()
        db.refresh(timeline)
        return timeline

    @classmethod
    def move_shot_to_scene(
        cls,
        db: Session,
        project_id: str,
        shot_id: str,
        target_scene_id: str,
        target_position: int = 0,
        actor: str = "USER",
        reason: Optional[str] = None
    ) -> AssemblyTimeline:
        timeline = cls.get_active_timeline(db, project_id)
        if not timeline:
            timeline = cls.auto_assemble_timeline(db, project_id)

        sh_uuid = _to_uuid(shot_id)
        placement = db.query(AssemblyShotPlacement).filter(
            AssemblyShotPlacement.timeline_id == timeline.id,
            AssemblyShotPlacement.shot_id == sh_uuid
        ).first()

        if not placement:
            raise HTTPException(status_code=404, detail="Shot placement not found")

        if placement.is_locked:
            raise HTTPException(status_code=400, detail="Cannot move locked shot placement")

        target_sc_uuid = _to_uuid(target_scene_id)
        target_assembly_scene = db.query(AssemblyScene).filter(
            AssemblyScene.timeline_id == timeline.id,
            AssemblyScene.scene_id == target_sc_uuid
        ).first()

        if not target_assembly_scene:
            raise HTTPException(status_code=404, detail="Target scene not found in timeline")

        # Update placement target scene
        placement.assembly_scene_id = target_assembly_scene.id
        placement.scene_id = target_sc_uuid
        placement.shot_order = target_position
        placement.version += 1

        timeline.version += 1
        audit = TimelineAudit(
            id=uuid.uuid4(),
            project_id=_to_uuid(project_id),
            timeline_id=timeline.id,
            action="MOVE_SHOT_TO_SCENE",
            actor=actor,
            change_reason=reason or f"Moved shot {shot_id} to scene {target_scene_id}",
        )
        db.add(audit)
        db.commit()
        db.refresh(timeline)
        return timeline

    @classmethod
    def update_shot_placement(
        cls,
        db: Session,
        project_id: str,
        placement_id: str,
        trim_in: Optional[float] = None,
        trim_out: Optional[float] = None,
        still_duration: Optional[float] = None,
        transition_to_next: Optional[str] = None,
        is_locked: Optional[bool] = None,
        reason: Optional[str] = None,
        actor: str = "USER",
    ) -> AssemblyShotPlacement:
        pl_uuid = _to_uuid(placement_id)
        placement = db.query(AssemblyShotPlacement).filter(
            AssemblyShotPlacement.id == pl_uuid
        ).first()

        if not placement:
            raise HTTPException(status_code=404, detail="Placement not found")

        if placement.is_locked and is_locked is not True and (
            trim_in is not None or trim_out is not None or still_duration is not None or transition_to_next is not None
        ):
            if is_locked is False:
                # Explicit unlock allowed
                placement.is_locked = False
            else:
                raise HTTPException(status_code=400, detail="Cannot modify locked placement. Unlock first.")

        if is_locked is not None:
            placement.is_locked = is_locked

        if trim_in is not None:
            placement.trim_in = max(0.0, trim_in)

        if trim_out is not None:
            placement.trim_out = max(placement.trim_in + 0.1, trim_out)

        if still_duration is not None:
            placement.still_duration = max(0.1, still_duration)

        if transition_to_next is not None:
            if transition_to_next not in ("CUT", "FADE", "DISSOLVE"):
                raise HTTPException(status_code=400, detail="Invalid transition type")
            placement.transition_to_next = transition_to_next

        # Recalculate effective duration
        if placement.source_type == "VIDEO":
            t_out = placement.trim_out or 4.0
            placement.effective_duration = max(0.1, t_out - placement.trim_in)
        else:
            placement.effective_duration = max(0.1, placement.still_duration)

        placement.version += 1

        audit = TimelineAudit(
            id=uuid.uuid4(),
            project_id=_to_uuid(project_id),
            timeline_id=placement.timeline_id,
            action="UPDATE_PLACEMENT",
            actor=actor,
            change_reason=reason or f"Updated placement {placement_id}",
        )
        db.add(audit)
        db.commit()
        db.refresh(placement)
        return placement

    @classmethod
    def create_checkpoint(cls, db: Session, project_id: str, label: str, actor: str = "USER") -> TimelineCheckpoint:
        timeline = cls.get_active_timeline(db, project_id)
        if not timeline:
            timeline = cls.auto_assemble_timeline(db, project_id)

        # Build snapshot data
        snapshot_data = cls._build_timeline_snapshot(db, timeline)

        last_ckpt = db.query(TimelineCheckpoint).filter(
            TimelineCheckpoint.timeline_id == timeline.id
        ).order_by(TimelineCheckpoint.checkpoint_number.desc()).first()

        next_number = (last_ckpt.checkpoint_number + 1) if last_ckpt else 1

        checkpoint = TimelineCheckpoint(
            id=uuid.uuid4(),
            project_id=_to_uuid(project_id),
            timeline_id=timeline.id,
            checkpoint_number=next_number,
            label=label,
            snapshot_data=snapshot_data,
            actor=actor,
        )
        db.add(checkpoint)

        audit = TimelineAudit(
            id=uuid.uuid4(),
            project_id=_to_uuid(project_id),
            timeline_id=timeline.id,
            action="CREATE_CHECKPOINT",
            actor=actor,
            change_reason=f"Created checkpoint #{next_number}: {label}",
            snapshot_data=snapshot_data,
        )
        db.add(audit)
        db.commit()
        db.refresh(checkpoint)
        return checkpoint

    @classmethod
    def list_checkpoints(cls, db: Session, project_id: str, limit: int = 50, offset: int = 0) -> List[TimelineCheckpoint]:
        p_uuid = _to_uuid(project_id)
        return db.query(TimelineCheckpoint).filter(
            TimelineCheckpoint.project_id == p_uuid
        ).order_by(TimelineCheckpoint.checkpoint_number.desc()).offset(offset).limit(limit).all()

    @classmethod
    def restore_checkpoint(cls, db: Session, project_id: str, checkpoint_id: str, actor: str = "USER", reason: Optional[str] = None) -> AssemblyTimeline:
        ckpt_uuid = _to_uuid(checkpoint_id)
        p_uuid = _to_uuid(project_id)
        checkpoint = db.query(TimelineCheckpoint).filter(
            TimelineCheckpoint.id == ckpt_uuid,
            TimelineCheckpoint.project_id == p_uuid
        ).first()

        if not checkpoint:
            raise HTTPException(status_code=404, detail="Checkpoint not found")

        active_timeline = cls.get_active_timeline(db, project_id)
        if active_timeline:
            active_timeline.is_active = False

        new_version = (active_timeline.version + 1) if active_timeline else 1

        # Re-create timeline from snapshot data (NO_SILENT_HISTORY_LOSS)
        new_timeline = AssemblyTimeline(
            id=uuid.uuid4(),
            project_id=p_uuid,
            version=new_version,
            status="DRAFT",
            is_active=True,
        )
        db.add(new_timeline)
        db.flush()

        snapshot_scenes = checkpoint.snapshot_data.get("scenes", [])
        for s_data in snapshot_scenes:
            a_scene = AssemblyScene(
                id=uuid.uuid4(),
                timeline_id=new_timeline.id,
                scene_id=_to_uuid(s_data["scene_id"]),
                scene_order=s_data["scene_order"],
            )
            db.add(a_scene)
            db.flush()

            for p_data in s_data.get("placements", []):
                v_asset_id = _to_uuid(p_data["visual_asset_id"]) if p_data.get("visual_asset_id") else None
                placement = AssemblyShotPlacement(
                    id=uuid.uuid4(),
                    timeline_id=new_timeline.id,
                    assembly_scene_id=a_scene.id,
                    scene_id=_to_uuid(s_data["scene_id"]),
                    shot_id=_to_uuid(p_data["shot_id"]),
                    shot_order=p_data["shot_order"],
                    visual_asset_id=v_asset_id,
                    source_type=p_data.get("source_type", "VIDEO"),
                    trim_in=p_data.get("trim_in", 0.0),
                    trim_out=p_data.get("trim_out"),
                    effective_duration=p_data.get("effective_duration", 4.0),
                    still_duration=p_data.get("still_duration", 4.0),
                    transition_to_next=p_data.get("transition_to_next", "CUT"),
                    is_locked=p_data.get("is_locked", False),
                    version=p_data.get("version", 1),
                )
                db.add(placement)

        audit = TimelineAudit(
            id=uuid.uuid4(),
            project_id=p_uuid,
            timeline_id=new_timeline.id,
            action="RESTORE_CHECKPOINT",
            actor=actor,
            change_reason=reason or f"Restored checkpoint #{checkpoint.checkpoint_number}: {checkpoint.label}",
            snapshot_data=checkpoint.snapshot_data,
        )
        db.add(audit)
        db.commit()
        db.refresh(new_timeline)
        return new_timeline

    @classmethod
    def get_timeline_blockers(cls, db: Session, project_id: str) -> List[AssemblyBlocker]:
        timeline = cls.get_active_timeline(db, project_id)
        if not timeline:
            return [
                AssemblyBlocker(
                    code="NO_TIMELINE",
                    message="No active timeline assembly exists.",
                    severity="ERROR",
                    recommended_fixes=[
                        RecommendedFix(
                            fix_code="auto_assemble",
                            label="Auto Assemble Timeline",
                            action_type="AUTO_ASSEMBLE",
                        )
                    ],
                )
            ]

        blockers: List[AssemblyBlocker] = []

        # Check placements for MISSING visuals
        for scene in timeline.scenes:
            for placement in scene.shot_placements:
                if placement.source_type == "MISSING" or not placement.visual_asset_id:
                    # Check if keyframe asset exists for shot
                    shot = db.query(Shot).filter(Shot.id == placement.shot_id).first()
                    fixes = [
                        RecommendedFix(
                            fix_code="generate_visual",
                            label="Generate Video Shot",
                            action_type="GENERATE_SHOT",
                            payload={"shot_id": str(placement.shot_id)},
                        )
                    ]
                    if shot and shot.keyframe_asset_id:
                        fixes.insert(0, RecommendedFix(
                            fix_code="use_keyframe_still",
                            label="Use Keyframe Still Image",
                            action_type="USE_KEYFRAME",
                            payload={"placement_id": str(placement.id), "keyframe_asset_id": str(shot.keyframe_asset_id)},
                        ))

                    blockers.append(
                        AssemblyBlocker(
                            code="MISSING_VISUAL",
                            message=f"Shot '{(shot.visual_prompt[:30] if shot and shot.visual_prompt else f'#{shot.shot_number}') if shot else str(placement.shot_id)}' has no video asset assigned.",
                            severity="WARNING",
                            target_id=str(placement.id),
                            recommended_fixes=fixes,
                        )
                    )

        # Check audio clips integration
        p_uuid = _to_uuid(project_id)
        audio_clips = db.query(AudioClip).filter(AudioClip.project_id == p_uuid).all()
        has_vo = any(ac.audio_type in ("VO", "DIALOGUE") for ac in audio_clips)
        if not has_vo and len(timeline.shot_placements) > 0:
            blockers.append(
                AssemblyBlocker(
                    code="MISSING_REQUIRED_AUDIO",
                    message="No Voiceover or Dialogue audio tracks found for this assembly.",
                    severity="WARNING",
                    target_id=str(project_id),
                    recommended_fixes=[
                        RecommendedFix(
                            fix_code="generate_audio_plan",
                            label="Generate Audio Production Plan",
                            action_type="GENERATE_AUDIO_PLAN",
                        )
                    ],
                )
            )

        return blockers

    @classmethod
    def apply_recommended_fix(cls, db: Session, project_id: str, blocker_code: str, target_id: Optional[str], fix_code: str) -> Dict[str, Any]:
        if fix_code == "auto_assemble":
            t = cls.auto_assemble_timeline(db, project_id)
            return {"status": "SUCCESS", "message": "Auto assembled timeline", "timeline_id": str(t.id)}

        if fix_code == "use_keyframe_still" and target_id:
            t_uuid = _to_uuid(target_id)
            placement = db.query(AssemblyShotPlacement).filter(AssemblyShotPlacement.id == t_uuid).first()
            if placement:
                shot = db.query(Shot).filter(Shot.id == placement.shot_id).first()
                if shot and shot.keyframe_asset_id:
                    placement.visual_asset_id = shot.keyframe_asset_id
                    placement.source_type = "KEYFRAME"
                    placement.still_duration = 4.0
                    placement.effective_duration = 4.0
                    db.commit()
                    return {"status": "SUCCESS", "message": f"Applied keyframe still fallback for shot {shot.id}"}

        return {"status": "NO_OP", "message": f"Fix action {fix_code} acknowledged"}

    @classmethod
    def build_timeline_read_schema(cls, db: Session, timeline: AssemblyTimeline) -> AssemblyTimelineRead:
        asset_ids = [p.visual_asset_id for s in timeline.scenes for p in s.shot_placements if p.visual_asset_id]
        assets = db.query(Asset).filter(Asset.id.in_(asset_ids)).all() if asset_ids else []
        asset_map = {str(a.id): a for a in assets}

        shot_ids = [p.shot_id for s in timeline.scenes for p in s.shot_placements]
        shots = db.query(Shot).filter(Shot.id.in_(shot_ids)).all() if shot_ids else []
        shot_map = {str(s.id): s for s in shots}

        scenes_read: List[AssemblySceneRead] = []
        total_duration = 0.0
        shot_count = 0

        for scene in timeline.scenes:
            placements_read: List[AssemblyShotPlacementRead] = []
            for p in scene.shot_placements:
                total_duration += p.effective_duration
                shot_count += 1

                asset = asset_map.get(str(p.visual_asset_id)) if p.visual_asset_id else None
                shot = shot_map.get(str(p.shot_id))

                placements_read.append(
                    AssemblyShotPlacementRead(
                        id=str(p.id),
                        timeline_id=str(p.timeline_id),
                        assembly_scene_id=str(p.assembly_scene_id),
                        scene_id=str(p.scene_id),
                        shot_id=str(p.shot_id),
                        shot_order=p.shot_order,
                        visual_asset_id=str(p.visual_asset_id) if p.visual_asset_id else None,
                        source_type=p.source_type,
                        trim_in=p.trim_in,
                        trim_out=p.trim_out,
                        effective_duration=p.effective_duration,
                        still_duration=p.still_duration,
                        transition_to_next=p.transition_to_next,
                        is_locked=p.is_locked,
                        version=p.version,
                        asset_url=asset.storage_key if asset else None,
                        asset_thumbnail_url=None,
                        shot_title=(shot.visual_prompt[:30] if shot and shot.visual_prompt else (f"Shot #{shot.shot_number}" if shot else None)),
                        shot_prompt=shot.visual_prompt if shot else None,
                        created_at=p.created_at,
                        updated_at=p.updated_at,
                    )
                )

            scenes_read.append(
                AssemblySceneRead(
                    id=str(scene.id),
                    timeline_id=str(scene.timeline_id),
                    scene_id=str(scene.scene_id),
                    scene_order=scene.scene_order,
                    scene_title=f"Scene #{scene.scene_order + 1}",
                    placements=placements_read,
                )
            )

        p_uuid = _to_uuid(timeline.project_id)
        audio_clips = db.query(AudioClip).filter(AudioClip.project_id == p_uuid).all()
        audio_read = [
            AudioClipSummaryRead(
                id=str(ac.id),
                audio_type=ac.audio_type,
                scope=ac.scope,
                name=ac.name,
                start_time=ac.start_time,
                duration_seconds=ac.duration_seconds,
                volume=ac.volume,
                is_muted=ac.mute,
                scene_id=str(ac.scene_id) if ac.scene_id else None,
                shot_id=str(ac.shot_id) if ac.shot_id else None,
            )
            for ac in audio_clips
        ]

        blockers = cls.get_timeline_blockers(db, str(timeline.project_id))

        return AssemblyTimelineRead(
            id=str(timeline.id),
            project_id=str(timeline.project_id),
            version=timeline.version,
            status=timeline.status,
            is_active=timeline.is_active,
            total_duration=round(total_duration, 2),
            scene_count=len(scenes_read),
            shot_count=shot_count,
            scenes=scenes_read,
            audio_clips=audio_read,
            blockers=blockers,
            created_at=timeline.created_at,
            updated_at=timeline.updated_at,
        )

    @staticmethod
    def _build_timeline_snapshot(db: Session, timeline: AssemblyTimeline) -> Dict[str, Any]:
        scenes_data = []
        for s in timeline.scenes:
            p_data = []
            for p in s.shot_placements:
                p_data.append({
                    "id": str(p.id),
                    "shot_id": str(p.shot_id),
                    "shot_order": p.shot_order,
                    "visual_asset_id": str(p.visual_asset_id) if p.visual_asset_id else None,
                    "source_type": p.source_type,
                    "trim_in": p.trim_in,
                    "trim_out": p.trim_out,
                    "effective_duration": p.effective_duration,
                    "still_duration": p.still_duration,
                    "transition_to_next": p.transition_to_next,
                    "is_locked": p.is_locked,
                    "version": p.version,
                })
            scenes_data.append({
                "id": str(s.id),
                "scene_id": str(s.scene_id),
                "scene_order": s.scene_order,
                "placements": p_data,
            })
        return {
            "timeline_id": str(timeline.id),
            "version": timeline.version,
            "status": timeline.status,
            "scenes": scenes_data,
        }
