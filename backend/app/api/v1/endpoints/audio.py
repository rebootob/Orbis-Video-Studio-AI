"""Audio Production and Mixing API Endpoints."""
import uuid
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.audio_clip import AudioClip
from app.models.audio_plan import AudioPlan
from app.models.audio_history import AudioPlanVersion, AudioClipHistory
from app.services.audio_production import AudioProductionService

router = APIRouter()


class GenerateClipRequest(BaseModel):
    provider_name: Optional[str] = None
    cost_authorized: bool = False
    actor: str = "USER"
    provider_specific_params: Optional[Dict[str, Any]] = None


class BatchAudioRequest(BaseModel):
    action: str = Field(..., description="GENERATE_ALL_VO, ASSIGN_BGM, ASSIGN_SFX, ASSIGN_AMBIENCE, CONTINUE_INCOMPLETE_AUDIO, RETRY_FAILED_AUDIO")
    provider_name: Optional[str] = None
    cost_authorized: bool = False
    actor: str = "USER"


class LockActionRequest(BaseModel):
    actor: str = "USER"
    reason: Optional[str] = None


class UpdateClipRequest(BaseModel):
    name: Optional[str] = None
    prompt: Optional[str] = None
    volume: Optional[float] = None
    mute: Optional[bool] = None
    fade_in: Optional[float] = None
    fade_out: Optional[float] = None
    ducking_role: Optional[str] = None
    ducking_amount_db: Optional[float] = None
    is_locked: Optional[bool] = None
    speaker: Optional[str] = None
    language: Optional[str] = None
    source_type: Optional[str] = None
    generation_mode: Optional[str] = None
    scope: Optional[str] = None
    actor: Optional[str] = "USER"
    reason: Optional[str] = None


def serialize_clip(c: AudioClip) -> Dict[str, Any]:
    return {
        "id": str(c.id),
        "project_id": str(c.project_id),
        "scene_id": str(c.scene_id) if c.scene_id else None,
        "shot_id": str(c.shot_id) if c.shot_id else None,
        "video_asset_id": str(c.video_asset_id) if c.video_asset_id else None,
        "asset_id": str(c.asset_id) if c.asset_id else None,
        "audio_type": c.audio_type,
        "source_type": c.source_type,
        "generation_mode": c.generation_mode,
        "scope": c.scope,
        "name": c.name,
        "prompt": c.prompt,
        "start_time": c.start_time,
        "duration_seconds": c.duration_seconds,
        "volume": c.volume,
        "mute": c.mute,
        "fade_in": c.fade_in,
        "fade_out": c.fade_out,
        "ducking_role": c.ducking_role,
        "ducking_amount_db": c.ducking_amount_db,
        "speaker": c.speaker,
        "language": c.language,
        "is_locked": c.is_locked,
        "status": c.status,
        "version": c.version,
        "provenance": c.provenance,
        "updated_at": c.updated_at.isoformat() if c.updated_at else None,
    }


def serialize_clip_history(h: AudioClipHistory) -> Dict[str, Any]:
    return {
        "id": str(h.id),
        "clip_id": str(h.clip_id),
        "project_id": str(h.project_id),
        "version_number": h.version_number,
        "audio_type": h.audio_type,
        "source_type": h.source_type,
        "generation_mode": h.generation_mode,
        "scope": h.scope,
        "name": h.name,
        "prompt": h.prompt,
        "start_time": h.start_time,
        "duration_seconds": h.duration_seconds,
        "volume": h.volume,
        "mute": h.mute,
        "fade_in": h.fade_in,
        "fade_out": h.fade_out,
        "ducking_role": h.ducking_role,
        "ducking_amount_db": h.ducking_amount_db,
        "speaker": h.speaker,
        "language": h.language,
        "is_locked": h.is_locked,
        "status": h.status,
        "asset_id": str(h.asset_id) if h.asset_id else None,
        "provenance": h.provenance,
        "actor": h.actor,
        "action": h.action,
        "change_reason": h.change_reason,
        "created_at": h.created_at.isoformat() if h.created_at else None,
    }


def serialize_plan_version(v: AudioPlanVersion) -> Dict[str, Any]:
    return {
        "id": str(v.id),
        "audio_plan_id": str(v.audio_plan_id),
        "project_id": str(v.project_id),
        "version_number": v.version_number,
        "status": v.status,
        "plan_data": v.plan_data,
        "actor": v.actor,
        "action": v.action,
        "change_reason": v.change_reason,
        "created_at": v.created_at.isoformat() if v.created_at else None,
    }


@router.post("/projects/{project_id}/audio/plan")
def generate_audio_plan(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    """Generate or refresh structured AudioPlan for the project."""
    plan = AudioProductionService.generate_audio_plan(db, project_id)
    return {
        "id": str(plan.id),
        "project_id": str(plan.project_id),
        "status": plan.status,
        "version": plan.version,
        "plan_data": plan.plan_data,
        "updated_at": plan.updated_at.isoformat() if plan.updated_at else None,
    }


@router.get("/projects/{project_id}/audio/plan")
def get_audio_plan(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    """Get the latest AudioPlan for the project."""
    plan = db.query(AudioPlan).filter(AudioPlan.project_id == project_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail=f"No audio plan found for project '{project_id}'.")
    return {
        "id": str(plan.id),
        "project_id": str(plan.project_id),
        "status": plan.status,
        "version": plan.version,
        "plan_data": plan.plan_data,
        "updated_at": plan.updated_at.isoformat() if plan.updated_at else None,
    }


@router.post("/projects/{project_id}/audio/plan/approve")
def approve_audio_plan(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    """Approve the audio plan and transition stage to AUDIO_PLAN_APPROVED."""
    plan = AudioProductionService.approve_audio_plan(db, project_id)
    return {
        "id": str(plan.id),
        "project_id": str(plan.project_id),
        "status": plan.status,
        "version": plan.version,
    }


@router.get("/projects/{project_id}/audio/plan/history")
def get_audio_plan_history(
    project_id: uuid.UUID,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """Bounded paginated retrieval of AudioPlan version history."""
    items, total = AudioProductionService.get_plan_history(
        db=db,
        project_id=project_id,
        limit=limit,
        offset=offset,
    )
    return {
        "items": [serialize_plan_version(v) for v in items],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.post("/projects/{project_id}/audio/plan/restore/{version_number}")
def restore_audio_plan_version(
    project_id: uuid.UUID,
    version_number: int,
    db: Session = Depends(get_db),
):
    """Restore a prior approved/locked AudioPlan version."""
    plan = AudioProductionService.restore_plan_version(
        db=db,
        project_id=project_id,
        version_number=version_number,
        actor="USER",
    )
    return {
        "id": str(plan.id),
        "project_id": str(plan.project_id),
        "status": plan.status,
        "version": plan.version,
        "plan_data": plan.plan_data,
        "updated_at": plan.updated_at.isoformat() if plan.updated_at else None,
    }


@router.get("/projects/{project_id}/audio/clips")
def list_audio_clips(
    project_id: uuid.UUID,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    audio_type: Optional[str] = Query(None),
    scope: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """List audio clips associated with the project with bounded pagination."""
    clips, total = AudioProductionService.list_audio_clips(
        db=db,
        project_id=project_id,
        limit=limit,
        offset=offset,
        audio_type=audio_type,
        scope=scope,
    )
    return {
        "items": [serialize_clip(c) for c in clips],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.post("/projects/{project_id}/audio/clips/{clip_id}/lock")
def lock_clip(
    project_id: uuid.UUID,
    clip_id: uuid.UUID,
    payload: LockActionRequest = LockActionRequest(),
    db: Session = Depends(get_db),
):
    """Explicit isolated operation to lock an AudioClip against modification."""
    clip = AudioProductionService.lock_clip(
        db=db,
        project_id=project_id,
        clip_id=clip_id,
        actor=payload.actor,
        reason=payload.reason,
    )
    return serialize_clip(clip)


@router.post("/projects/{project_id}/audio/clips/{clip_id}/unlock")
def unlock_clip(
    project_id: uuid.UUID,
    clip_id: uuid.UUID,
    payload: LockActionRequest = LockActionRequest(),
    db: Session = Depends(get_db),
):
    """Explicit isolated operation to unlock an AudioClip."""
    clip = AudioProductionService.unlock_clip(
        db=db,
        project_id=project_id,
        clip_id=clip_id,
        actor=payload.actor,
        reason=payload.reason,
    )
    return serialize_clip(clip)


@router.get("/projects/{project_id}/audio/clips/{clip_id}/history")
def get_clip_history(
    project_id: uuid.UUID,
    clip_id: uuid.UUID,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """Bounded paginated retrieval of AudioClip audit and revision history."""
    items, total = AudioProductionService.get_clip_history(
        db=db,
        project_id=project_id,
        clip_id=clip_id,
        limit=limit,
        offset=offset,
    )
    return {
        "items": [serialize_clip_history(h) for h in items],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.post("/projects/{project_id}/audio/clips/{clip_id}/generate")
def generate_clip_audio(
    project_id: uuid.UUID,
    clip_id: uuid.UUID,
    payload: GenerateClipRequest,
    db: Session = Depends(get_db),
):
    """Generate audio asset for a single AudioClip."""
    clip = AudioProductionService.generate_clip_audio(
        db=db,
        project_id=project_id,
        clip_id=clip_id,
        provider_name=payload.provider_name,
        cost_authorized=payload.cost_authorized,
        actor=payload.actor,
        provider_specific_params=payload.provider_specific_params,
    )
    return {
        "id": str(clip.id),
        "status": clip.status,
        "asset_id": str(clip.asset_id) if clip.asset_id else None,
        "duration_seconds": clip.duration_seconds,
        "provenance": clip.provenance,
    }


@router.patch("/projects/{project_id}/audio/clips/{clip_id}")
def update_clip(
    project_id: uuid.UUID,
    clip_id: uuid.UUID,
    payload: UpdateClipRequest,
    db: Session = Depends(get_db),
):
    """Update AudioClip settings and volume/ducking properties with strict lock safety."""
    clip = db.query(AudioClip).filter(AudioClip.id == clip_id, AudioClip.project_id == project_id).first()
    if not clip:
        raise HTTPException(status_code=404, detail=f"AudioClip '{clip_id}' not found.")

    fields_to_update = payload.model_dump(exclude_unset=True)

    # Finding 2: LOCK SAFETY
    # Prevent a request from sending is_locked=false together with other field modifications.
    # Unlock must be a distinct explicit operation/gate, or equivalent fail-closed flow.
    if clip.is_locked:
        if payload.is_locked is False:
            other_fields = [k for k in fields_to_update.keys() if k not in ("is_locked", "actor", "reason")]
            if other_fields:
                raise HTTPException(
                    status_code=status.HTTP_423_LOCKED,
                    detail=f"Cannot modify fields ({', '.join(other_fields)}) while unlocking clip. Unlocking must be an explicit isolated operation.",
                )
            # Isolated unlock via PATCH
            unlocked = AudioProductionService.unlock_clip(
                db=db,
                project_id=project_id,
                clip_id=clip_id,
                actor=payload.actor or "USER",
                reason=payload.reason or "Explicit unlock via PATCH",
            )
            return serialize_clip(unlocked)
        else:
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail="Clip is locked against modification. Unlocking must be a distinct explicit operation.",
            )

    # If clip is currently unlocked but payload specifies is_locked=True
    if payload.is_locked is True:
        other_fields = {k: v for k, v in fields_to_update.items() if k not in ("is_locked", "actor", "reason")}
        for field, val in other_fields.items():
            setattr(clip, field, val)
        clip.is_locked = True
        clip.version += 1
        clip.updated_at = AudioProductionService.auto_classify_clip.__globals__["datetime"].now(AudioProductionService.auto_classify_clip.__globals__["timezone"].utc)
        AudioProductionService.record_clip_history(
            db, clip, actor=payload.actor or "USER", action="LOCK", change_reason=payload.reason or "Clip modified and locked"
        )
        db.commit()
        db.refresh(clip)
        return serialize_clip(clip)

    # Normal update on unlocked clip
    other_fields = {k: v for k, v in fields_to_update.items() if k not in ("is_locked", "actor", "reason")}
    if other_fields:
        for field, val in other_fields.items():
            setattr(clip, field, val)
        clip.version += 1
        clip.updated_at = AudioProductionService.auto_classify_clip.__globals__["datetime"].now(AudioProductionService.auto_classify_clip.__globals__["timezone"].utc)
        AudioProductionService.record_clip_history(
            db, clip, actor=payload.actor or "USER", action="UPDATE", change_reason=payload.reason or "Clip properties updated"
        )
        db.commit()
        db.refresh(clip)

    return serialize_clip(clip)


@router.post("/projects/{project_id}/audio/batch")
def execute_audio_batch(
    project_id: uuid.UUID,
    payload: BatchAudioRequest,
    db: Session = Depends(get_db),
):
    """Execute batch audio generation actions."""
    return AudioProductionService.execute_audio_batch(
        db=db,
        project_id=project_id,
        action=payload.action,
        cost_authorized=payload.cost_authorized,
        actor=payload.actor,
        provider_name=payload.provider_name,
    )


@router.post("/projects/{project_id}/audio/mix")
def compute_auto_mix(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    """Compute auto-ducking mixing metadata and store in AudioPlan."""
    return AudioProductionService.compute_auto_mix(db, project_id)
