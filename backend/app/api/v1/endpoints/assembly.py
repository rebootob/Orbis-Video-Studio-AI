from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.assembly import (
    AssemblyTimelineRead,
    AssemblyShotPlacementRead,
    PlacementUpdate,
    SceneReorderRequest,
    ShotReorderRequest,
    CrossSceneMoveRequest,
    CheckpointCreate,
    CheckpointRead,
    CheckpointRestoreRequest,
    AssemblyBlocker,
    ApplyFixRequest,
    TimelineAuditRead,
)
from app.services.assembly import AssemblyService
from app.models.assembly import TimelineAudit

router = APIRouter()


@router.get("/projects/{project_id}/assembly", response_model=AssemblyTimelineRead)
def get_assembly_timeline(
    project_id: str,
    db: Session = Depends(get_db),
) -> AssemblyTimelineRead:
    timeline = AssemblyService.get_or_create_active_timeline(db, project_id)
    return AssemblyService.build_timeline_read_schema(db, timeline)


@router.post("/projects/{project_id}/assembly/auto-assemble", response_model=AssemblyTimelineRead)
def auto_assemble_timeline(
    project_id: str,
    actor: str = Query("system"),
    db: Session = Depends(get_db),
) -> AssemblyTimelineRead:
    timeline = AssemblyService.auto_assemble_timeline(db, project_id, actor=actor)
    return AssemblyService.build_timeline_read_schema(db, timeline)


@router.put("/projects/{project_id}/assembly/placements/{placement_id}", response_model=AssemblyShotPlacementRead)
def update_shot_placement(
    project_id: str,
    placement_id: str,
    payload: PlacementUpdate,
    actor: str = Query("USER"),
    db: Session = Depends(get_db),
) -> AssemblyShotPlacementRead:
    placement = AssemblyService.update_shot_placement(
        db=db,
        project_id=project_id,
        placement_id=placement_id,
        trim_in=payload.trim_in,
        trim_out=payload.trim_out,
        still_duration=payload.still_duration,
        transition_to_next=payload.transition_to_next,
        is_locked=payload.is_locked,
        reason=payload.reason,
        actor=actor,
    )
    # Refresh active timeline schema
    timeline = AssemblyService.get_active_timeline(db, project_id)
    read_schema = AssemblyService.build_timeline_read_schema(db, timeline)
    for sc in read_schema.scenes:
        for pl in sc.placements:
            if pl.id == placement.id:
                return pl
    raise HTTPException(status_code=404, detail="Updated placement read schema not found")


@router.post("/projects/{project_id}/assembly/reorder-scenes", response_model=AssemblyTimelineRead)
def reorder_scenes(
    project_id: str,
    payload: SceneReorderRequest,
    actor: str = Query("USER"),
    db: Session = Depends(get_db),
) -> AssemblyTimelineRead:
    orders = [(item.scene_id, item.order) for item in payload.orders]
    timeline = AssemblyService.reorder_scenes(db, project_id, orders, actor=actor)
    return AssemblyService.build_timeline_read_schema(db, timeline)


@router.post("/projects/{project_id}/assembly/reorder-shots", response_model=AssemblyTimelineRead)
def reorder_shots_in_scene(
    project_id: str,
    scene_id: str = Query(...),
    payload: ShotReorderRequest = None,
    actor: str = Query("USER"),
    db: Session = Depends(get_db),
) -> AssemblyTimelineRead:
    orders = [(item.shot_id, item.order) for item in payload.orders]
    timeline = AssemblyService.reorder_shots_in_scene(db, project_id, scene_id, orders, actor=actor)
    return AssemblyService.build_timeline_read_schema(db, timeline)


@router.post("/projects/{project_id}/assembly/move-shot", response_model=AssemblyTimelineRead)
def move_shot_to_scene(
    project_id: str,
    payload: CrossSceneMoveRequest,
    db: Session = Depends(get_db),
) -> AssemblyTimelineRead:
    timeline = AssemblyService.move_shot_to_scene(
        db=db,
        project_id=project_id,
        shot_id=payload.shot_id,
        target_scene_id=payload.target_scene_id,
        target_position=payload.target_position,
        actor=payload.actor or "USER",
        reason=payload.reason,
    )
    return AssemblyService.build_timeline_read_schema(db, timeline)


@router.post("/projects/{project_id}/assembly/checkpoints", response_model=CheckpointRead)
def create_checkpoint(
    project_id: str,
    payload: CheckpointCreate,
    db: Session = Depends(get_db),
) -> CheckpointRead:
    checkpoint = AssemblyService.create_checkpoint(
        db=db,
        project_id=project_id,
        label=payload.label,
        actor=payload.actor or "USER",
    )
    return CheckpointRead.model_validate(checkpoint)


@router.get("/projects/{project_id}/assembly/checkpoints", response_model=List[CheckpointRead])
def list_checkpoints(
    project_id: str,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> List[CheckpointRead]:
    ckpts = AssemblyService.list_checkpoints(db, project_id, limit=limit, offset=offset)
    return [CheckpointRead.model_validate(c) for c in ckpts]


@router.post("/projects/{project_id}/assembly/checkpoints/{checkpoint_id}/restore", response_model=AssemblyTimelineRead)
def restore_checkpoint(
    project_id: str,
    checkpoint_id: str,
    payload: CheckpointRestoreRequest = None,
    db: Session = Depends(get_db),
) -> AssemblyTimelineRead:
    actor = payload.actor if payload else "USER"
    reason = payload.reason if payload else None
    timeline = AssemblyService.restore_checkpoint(db, project_id, checkpoint_id, actor=actor, reason=reason)
    return AssemblyService.build_timeline_read_schema(db, timeline)


@router.get("/projects/{project_id}/assembly/blockers", response_model=List[AssemblyBlocker])
def get_timeline_blockers(
    project_id: str,
    db: Session = Depends(get_db),
) -> List[AssemblyBlocker]:
    return AssemblyService.get_timeline_blockers(db, project_id)


@router.post("/projects/{project_id}/assembly/blockers/apply-fix", response_model=Dict[str, Any])
def apply_recommended_fix(
    project_id: str,
    payload: ApplyFixRequest,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    return AssemblyService.apply_recommended_fix(
        db=db,
        project_id=project_id,
        blocker_code=payload.blocker_code,
        target_id=payload.target_id,
        fix_code=payload.fix_code,
    )


@router.get("/projects/{project_id}/assembly/audits", response_model=List[TimelineAuditRead])
def list_timeline_audits(
    project_id: str,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> List[TimelineAuditRead]:
    audits = db.query(TimelineAudit).filter(
        TimelineAudit.project_id == project_id
    ).order_by(TimelineAudit.created_at.desc()).offset(offset).limit(limit).all()
    return [TimelineAuditRead.model_validate(a) for a in audits]
