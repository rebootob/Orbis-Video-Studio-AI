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
    def _resolve_shot_visual_source(shot: Shot, asset_map: Dict[str, Asset]) -> Tuple[Optional[uuid.UUID], str, Optional[float]]:
        """
        Resolves the visual asset for a shot adhering strictly to resolution order:
        1. Approved/current VIDEO asset
        2. Current VIDEO asset
        3. Approved/current KEYFRAME / IMAGE asset
        4. MISSING blocker

        Returns:
        (selected_asset_id, source_type, known_source_duration)
        where known_source_duration is float if known from Asset/metadata, or None if UNKNOWN.
        Do NOT fabricate 4.0 as authoritative source media duration.
        """
        selected_asset_id: Optional[uuid.UUID] = None
        source_type = "MISSING"
        known_source_duration: Optional[float] = None

        def asset_category(a: Asset) -> str:
            atype = (a.asset_type or "").upper()
            ctype = (a.content_type or "").lower()
            if atype == "VIDEO" or "video" in ctype:
                return "VIDEO"
            elif atype in ("KEYFRAME", "IMAGE", "PHOTO", "GRAPHIC") or "image" in ctype or "keyframe" in ctype:
                return "KEYFRAME" if atype == "KEYFRAME" else "IMAGE"
            return "UNKNOWN"

        def get_asset_duration(a: Asset) -> Optional[float]:
            if hasattr(a, "duration_seconds") and getattr(a, "duration_seconds") is not None:
                return float(getattr(a, "duration_seconds"))
            if hasattr(a, "duration") and getattr(a, "duration") is not None:
                return float(getattr(a, "duration"))
            if hasattr(a, "metadata") and isinstance(getattr(a, "metadata"), dict):
                meta = getattr(a, "metadata")
                if meta.get("duration_seconds"):
                    return float(meta["duration_seconds"])
                if meta.get("duration"):
                    return float(meta["duration"])
            return None

        # Step 1 & 2: Check shot.source_asset_id
        if shot.source_asset_id and str(shot.source_asset_id) in asset_map:
            source_asset = asset_map[str(shot.source_asset_id)]
            cat = asset_category(source_asset)

            if cat == "VIDEO":
                selected_asset_id = source_asset.id
                source_type = "VIDEO"
                a_dur = get_asset_duration(source_asset)
                if a_dur is not None and a_dur > 0:
                    known_source_duration = a_dur
                elif isinstance(shot.source_metadata, dict) and shot.source_metadata.get("duration_seconds"):
                    known_source_duration = float(shot.source_metadata["duration_seconds"])
                elif isinstance(shot.source_metadata, dict) and shot.source_metadata.get("duration"):
                    known_source_duration = float(shot.source_metadata["duration"])
                return selected_asset_id, source_type, known_source_duration

            elif cat in ("IMAGE", "KEYFRAME"):
                # source_asset_id is an IMAGE/KEYFRAME asset -> MUST NOT BECOME VIDEO!
                selected_asset_id = source_asset.id
                source_type = "KEYFRAME" if cat == "KEYFRAME" else "IMAGE"
                return selected_asset_id, source_type, None

        # Step 3: Check shot.keyframe_asset_id fallback
        if shot.keyframe_asset_id and str(shot.keyframe_asset_id) in asset_map:
            keyframe_asset = asset_map[str(shot.keyframe_asset_id)]
            selected_asset_id = keyframe_asset.id
            source_type = "KEYFRAME"
            return selected_asset_id, source_type, None

        # Step 4: MISSING
        return None, "MISSING", None

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
        existing_placements: Dict[str, AssemblyShotPlacement] = {}
        existing_scenes_order: List[uuid.UUID] = []

        if existing_timeline:
            # Preserve manual scene order from existing_timeline
            sorted_existing_scenes = sorted(existing_timeline.scenes, key=lambda s: s.scene_order)
            existing_scenes_order = [s.scene_id for s in sorted_existing_scenes]
            for scene in existing_timeline.scenes:
                for placement in scene.shot_placements:
                    existing_placements[str(placement.shot_id)] = placement

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

        # Fetch canonical project scenes & shots
        db_scenes = db.query(Scene).filter(Scene.project_id == p_uuid).order_by(Scene.scene_number.asc()).all()
        db_scene_map: Dict[str, Scene] = {str(s.id): s for s in db_scenes}
        scene_ids = [s.id for s in db_scenes]

        shots = []
        if scene_ids:
            shots = db.query(Shot).filter(Shot.scene_id.in_(scene_ids)).order_by(Shot.shot_number.asc()).all()

        assets = db.query(Asset).filter(Asset.project_id == p_uuid).all()
        asset_map: Dict[str, Asset] = {str(a.id): a for a in assets}

        # 1. Determine Ordered Scene List for Assembly (preserving manual scene order)
        ordered_assembly_scene_ids: List[uuid.UUID] = []
        for sc_id in existing_scenes_order:
            if str(sc_id) in db_scene_map and sc_id not in ordered_assembly_scene_ids:
                ordered_assembly_scene_ids.append(sc_id)
        for db_sc in db_scenes:
            if db_sc.id not in ordered_assembly_scene_ids:
                ordered_assembly_scene_ids.append(db_sc.id)

        # 2. Determine Assembly Scene Assignment for each shot (preserving cross-scene moves)
        shots_by_assembly_scene_id: Dict[str, List[Tuple[Shot, Optional[AssemblyShotPlacement]]]] = {
            str(sc_id): [] for sc_id in ordered_assembly_scene_ids
        }

        for shot in shots:
            existing_p = existing_placements.get(str(shot.id))
            if existing_p and existing_p.scene_id and str(existing_p.scene_id) in shots_by_assembly_scene_id:
                target_sc_id_str = str(existing_p.scene_id)
            else:
                target_sc_id_str = str(shot.scene_id)
                if target_sc_id_str not in shots_by_assembly_scene_id:
                    shots_by_assembly_scene_id[target_sc_id_str] = []

            shots_by_assembly_scene_id[target_sc_id_str].append((shot, existing_p))

        # 3. Build assembly scenes and placements
        for scene_idx, scene_id in enumerate(ordered_assembly_scene_ids):
            assembly_scene = AssemblyScene(
                id=uuid.uuid4(),
                timeline_id=timeline.id,
                scene_id=scene_id,
                scene_order=scene_idx,
            )
            db.add(assembly_scene)
            db.flush()

            assigned_shots = shots_by_assembly_scene_id.get(str(scene_id), [])
            # Sort assigned shots: by existing placement shot_order if present, else by shot.shot_number
            def shot_sort_key(item: Tuple[Shot, Optional[AssemblyShotPlacement]]):
                sh, p = item
                if p is not None:
                    return (0, p.shot_order)
                return (1, sh.shot_number)

            sorted_assigned = sorted(assigned_shots, key=shot_sort_key)

            for shot_idx, (shot, existing_p) in enumerate(sorted_assigned):
                res_asset_id, res_source_type, known_src_dur = cls._resolve_shot_visual_source(shot, asset_map)

                if existing_p:
                    if existing_p.is_locked:
                        # Fully preserve locked placement
                        selected_asset_id = existing_p.visual_asset_id
                        source_type = existing_p.source_type
                        trim_in = existing_p.trim_in
                        trim_out = existing_p.trim_out
                        still_duration = existing_p.still_duration
                        effective_duration = existing_p.effective_duration
                        transition_to_next = existing_p.transition_to_next
                        is_locked = True
                        p_version = existing_p.version
                    else:
                        # Unlocked placement state preservation / reconciliation
                        if str(res_asset_id) == str(existing_p.visual_asset_id) or existing_p.version > 1 or existing_p.visual_asset_id:
                            selected_asset_id = existing_p.visual_asset_id if existing_p.visual_asset_id else res_asset_id
                            source_type = existing_p.source_type if existing_p.visual_asset_id else res_source_type
                            trim_in = existing_p.trim_in
                            trim_out = existing_p.trim_out if existing_p.trim_out is not None else known_src_dur
                            still_duration = existing_p.still_duration
                            transition_to_next = existing_p.transition_to_next
                            is_locked = False
                            p_version = existing_p.version
                        else:
                            selected_asset_id = res_asset_id
                            source_type = res_source_type
                            trim_in = 0.0
                            trim_out = known_src_dur if res_source_type == "VIDEO" else None
                            still_duration = 4.0
                            transition_to_next = existing_p.transition_to_next
                            is_locked = False
                            p_version = 1

                        if source_type == "VIDEO":
                            if trim_out is not None:
                                effective_duration = max(0.1, trim_out - trim_in)
                            else:
                                effective_duration = max(0.1, 4.0 - trim_in)
                        else:
                            effective_duration = max(0.1, still_duration)
                else:
                    # New shot placement
                    selected_asset_id = res_asset_id
                    source_type = res_source_type
                    trim_in = 0.0
                    trim_out = known_src_dur if res_source_type == "VIDEO" else None
                    still_duration = 4.0
                    effective_duration = known_src_dur if (res_source_type == "VIDEO" and known_src_dur is not None) else 4.0
                    transition_to_next = "CUT"
                    is_locked = False
                    p_version = 1

                placement = AssemblyShotPlacement(
                    id=uuid.uuid4(),
                    timeline_id=timeline.id,
                    assembly_scene_id=assembly_scene.id,
                    scene_id=scene_id,  # Preserves target assembly scene ID!
                    shot_id=shot.id,
                    shot_order=shot_idx,
                    visual_asset_id=selected_asset_id,
                    source_type=source_type,
                    trim_in=trim_in,
                    trim_out=trim_out,
                    effective_duration=effective_duration,
                    still_duration=still_duration,
                    transition_to_next=transition_to_next,
                    is_locked=is_locked,
                    version=p_version,
                )
                db.add(placement)

        audit = TimelineAudit(
            id=uuid.uuid4(),
            project_id=p_uuid,
            timeline_id=timeline.id,
            action="AUTO_ASSEMBLE",
            actor=actor,
            change_reason="Automated timeline assembly with state and structure preservation",
        )
        db.add(audit)
        db.commit()
        db.refresh(timeline)
        return timeline

    @classmethod
    def _ensure_unapproved_active_timeline(cls, db: Session, timeline: AssemblyTimeline, actor: str = "system") -> AssemblyTimeline:
        """If the current active timeline is APPROVED, preserve it as immutable history
        and spawn a new active timeline revision (vN+1, status='DRAFT') for edits."""
        if timeline.status != "APPROVED":
            return timeline

        timeline.is_active = False

        new_timeline = AssemblyTimeline(
            id=uuid.uuid4(),
            project_id=timeline.project_id,
            version=timeline.version + 1,
            status="DRAFT",
            is_active=True,
        )
        db.add(new_timeline)
        db.flush()

        for scene in timeline.scenes:
            new_scene = AssemblyScene(
                id=uuid.uuid4(),
                timeline_id=new_timeline.id,
                scene_id=scene.scene_id,
                scene_order=scene.scene_order,
            )
            db.add(new_scene)
            db.flush()

            for p in scene.shot_placements:
                new_p = AssemblyShotPlacement(
                    id=uuid.uuid4(),
                    timeline_id=new_timeline.id,
                    assembly_scene_id=new_scene.id,
                    scene_id=p.scene_id,
                    shot_id=p.shot_id,
                    shot_order=p.shot_order,
                    visual_asset_id=p.visual_asset_id,
                    source_type=p.source_type,
                    trim_in=p.trim_in,
                    trim_out=p.trim_out,
                    effective_duration=p.effective_duration,
                    still_duration=p.still_duration,
                    transition_to_next=p.transition_to_next,
                    is_locked=p.is_locked,
                    version=p.version + 1,
                )
                db.add(new_p)

        audit = TimelineAudit(
            id=uuid.uuid4(),
            project_id=timeline.project_id,
            timeline_id=new_timeline.id,
            action="CLONE_NEW_REVISION_AFTER_APPROVAL",
            actor=actor,
            change_reason=f"Spawned active timeline revision v{new_timeline.version} to preserve approved revision v{timeline.version}",
        )
        db.add(audit)
        db.flush()
        return new_timeline

    @classmethod
    def reorder_scenes(cls, db: Session, project_id: str, scene_orders: List[Tuple[str, int]], actor: str = "USER") -> AssemblyTimeline:
        p_uuid = _to_uuid(project_id)
        project = db.query(Project).filter(Project.id == p_uuid).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        timeline = cls.get_active_timeline(db, project_id)
        if not timeline:
            timeline = cls.auto_assemble_timeline(db, project_id)
        else:
            timeline = cls._ensure_unapproved_active_timeline(db, timeline, actor=actor)

        scene_map = {str(s.scene_id): s for s in timeline.scenes}
        for scene_id, order in scene_orders:
            if scene_id in scene_map:
                scene_map[scene_id].scene_order = order

        timeline.version += 1
        audit = TimelineAudit(
            id=uuid.uuid4(),
            project_id=p_uuid,
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
        p_uuid = _to_uuid(project_id)
        project = db.query(Project).filter(Project.id == p_uuid).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        timeline = cls.get_active_timeline(db, project_id)
        if not timeline:
            timeline = cls.auto_assemble_timeline(db, project_id)
        else:
            timeline = cls._ensure_unapproved_active_timeline(db, timeline, actor=actor)

        sc_uuid = _to_uuid(scene_id)
        assembly_scene = db.query(AssemblyScene).filter(
            AssemblyScene.timeline_id == timeline.id,
            AssemblyScene.scene_id == sc_uuid
        ).first()

        if not assembly_scene:
            raise HTTPException(status_code=404, detail="Scene placement not found in active timeline")

        placement_map = {str(p.shot_id): p for p in assembly_scene.shot_placements}
        for shot_id, order in shot_orders:
            if shot_id in placement_map:
                placement_map[shot_id].shot_order = order

        timeline.version += 1
        audit = TimelineAudit(
            id=uuid.uuid4(),
            project_id=p_uuid,
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
        p_uuid = _to_uuid(project_id)
        project = db.query(Project).filter(Project.id == p_uuid).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        timeline = cls.get_active_timeline(db, project_id)
        if not timeline:
            timeline = cls.auto_assemble_timeline(db, project_id)
        else:
            timeline = cls._ensure_unapproved_active_timeline(db, timeline, actor=actor)

        sh_uuid = _to_uuid(shot_id)
        placement = db.query(AssemblyShotPlacement).filter(
            AssemblyShotPlacement.timeline_id == timeline.id,
            AssemblyShotPlacement.shot_id == sh_uuid
        ).first()

        if not placement:
            raise HTTPException(status_code=404, detail="Shot placement not found in active timeline for project")

        if placement.is_locked:
            raise HTTPException(status_code=400, detail="Cannot move locked shot placement")

        target_sc_uuid = _to_uuid(target_scene_id)
        target_assembly_scene = db.query(AssemblyScene).filter(
            AssemblyScene.timeline_id == timeline.id,
            AssemblyScene.scene_id == target_sc_uuid
        ).first()

        if not target_assembly_scene:
            raise HTTPException(status_code=404, detail="Target scene not found in active timeline for project")

        placement.assembly_scene_id = target_assembly_scene.id
        placement.scene_id = target_sc_uuid
        placement.shot_order = target_position
        placement.version += 1

        timeline.version += 1
        audit = TimelineAudit(
            id=uuid.uuid4(),
            project_id=p_uuid,
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
        # Ownership validation
        p_uuid = _to_uuid(project_id)
        project = db.query(Project).filter(Project.id == p_uuid).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        active_timeline = cls.get_active_timeline(db, project_id)
        if not active_timeline:
            raise HTTPException(status_code=404, detail="No active timeline found for project")
        else:
            active_timeline = cls._ensure_unapproved_active_timeline(db, active_timeline, actor=actor)

        pl_uuid = _to_uuid(placement_id)
        placement = db.query(AssemblyShotPlacement).filter(
            AssemblyShotPlacement.id == pl_uuid,
            AssemblyShotPlacement.timeline_id == active_timeline.id
        ).first()

        if not placement:
            old_placement = db.query(AssemblyShotPlacement).filter(AssemblyShotPlacement.id == pl_uuid).first()
            if old_placement:
                placement = db.query(AssemblyShotPlacement).filter(
                    AssemblyShotPlacement.shot_id == old_placement.shot_id,
                    AssemblyShotPlacement.timeline_id == active_timeline.id
                ).first()

        if not placement:
            raise HTTPException(status_code=404, detail="Placement not found in active timeline for project")

        has_modifications = (
            trim_in is not None
            or trim_out is not None
            or still_duration is not None
            or transition_to_next is not None
        )

        # Lock Safety Rule: Reject mixed unlock + modify in a single request
        if is_locked is False and has_modifications:
            raise HTTPException(
                status_code=400,
                detail="Cannot combine unlock (is_locked=false) with placement modifications. Unlock placement first in an isolated request."
            )

        # Reject modifying a locked placement without unlocking first in a prior request
        if placement.is_locked and has_modifications:
            raise HTTPException(
                status_code=400,
                detail="Placement is locked. Unlock placement first before making modifications."
            )

        audit_action = "UPDATE_PLACEMENT"

        # Explicit lock / unlock handling
        if is_locked is not None:
            if is_locked != placement.is_locked:
                placement.is_locked = is_locked
                audit_action = "UNLOCK_PLACEMENT" if not is_locked else "LOCK_PLACEMENT"

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
            if placement.trim_out is not None:
                placement.effective_duration = max(0.1, placement.trim_out - placement.trim_in)
            else:
                placement.effective_duration = max(0.1, 4.0 - placement.trim_in)
        else:
            placement.effective_duration = max(0.1, placement.still_duration)

        placement.version += 1

        audit = TimelineAudit(
            id=uuid.uuid4(),
            project_id=p_uuid,
            timeline_id=placement.timeline_id,
            action=audit_action,
            actor=actor,
            change_reason=reason or f"Updated placement {placement_id}",
        )
        db.add(audit)
        db.commit()
        db.refresh(placement)
        return placement

    @classmethod
    def create_checkpoint(cls, db: Session, project_id: str, label: str, actor: str = "USER") -> TimelineCheckpoint:
        p_uuid = _to_uuid(project_id)
        project = db.query(Project).filter(Project.id == p_uuid).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        timeline = cls.get_active_timeline(db, project_id)
        if not timeline:
            timeline = cls.auto_assemble_timeline(db, project_id)

        snapshot_data = cls._build_timeline_snapshot(db, timeline)

        last_ckpt = db.query(TimelineCheckpoint).filter(
            TimelineCheckpoint.timeline_id == timeline.id
        ).order_by(TimelineCheckpoint.checkpoint_number.desc()).first()

        next_number = (last_ckpt.checkpoint_number + 1) if last_ckpt else 1

        checkpoint = TimelineCheckpoint(
            id=uuid.uuid4(),
            project_id=p_uuid,
            timeline_id=timeline.id,
            checkpoint_number=next_number,
            label=label,
            snapshot_data=snapshot_data,
            actor=actor,
        )
        db.add(checkpoint)

        audit = TimelineAudit(
            id=uuid.uuid4(),
            project_id=p_uuid,
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
        project = db.query(Project).filter(Project.id == p_uuid).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        return db.query(TimelineCheckpoint).filter(
            TimelineCheckpoint.project_id == p_uuid
        ).order_by(TimelineCheckpoint.checkpoint_number.desc()).offset(offset).limit(limit).all()

    @classmethod
    def restore_checkpoint(cls, db: Session, project_id: str, checkpoint_id: str, actor: str = "USER", reason: Optional[str] = None) -> AssemblyTimeline:
        ckpt_uuid = _to_uuid(checkpoint_id)
        p_uuid = _to_uuid(project_id)
        project = db.query(Project).filter(Project.id == p_uuid).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        checkpoint = db.query(TimelineCheckpoint).filter(
            TimelineCheckpoint.id == ckpt_uuid,
            TimelineCheckpoint.project_id == p_uuid
        ).first()

        if not checkpoint:
            raise HTTPException(status_code=404, detail="Checkpoint not found for this project")

        active_timeline = cls.get_active_timeline(db, project_id)
        if active_timeline:
            active_timeline.is_active = False

        new_version = (active_timeline.version + 1) if active_timeline else 1

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
        p_uuid = _to_uuid(project_id)
        project = db.query(Project).filter(Project.id == p_uuid).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        if fix_code == "auto_assemble":
            t = cls.auto_assemble_timeline(db, project_id)
            return {"status": "SUCCESS", "message": "Auto assembled timeline", "timeline_id": str(t.id)}

        if fix_code == "use_keyframe_still" and target_id:
            active_timeline = cls.get_active_timeline(db, project_id)
            if not active_timeline:
                raise HTTPException(status_code=404, detail="No active timeline found")

            t_uuid = _to_uuid(target_id)
            placement = db.query(AssemblyShotPlacement).filter(
                AssemblyShotPlacement.id == t_uuid,
                AssemblyShotPlacement.timeline_id == active_timeline.id
            ).first()
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
