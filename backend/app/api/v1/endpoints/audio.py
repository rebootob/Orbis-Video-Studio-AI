"""Audio Production and Mixing API Endpoints."""
import uuid
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.audio_clip import AudioClip
from app.models.audio_plan import AudioPlan
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


@router.get("/projects/{project_id}/audio/clips")
def list_audio_clips(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    """List all audio clips associated with the project."""
    clips = (
        db.query(AudioClip)
        .filter(AudioClip.project_id == project_id)
        .order_by(AudioClip.start_time.asc(), AudioClip.created_at.asc())
        .all()
    )
    return [
        {
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
        for c in clips
    ]


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
    """Update AudioClip settings and volume/ducking properties."""
    clip = db.query(AudioClip).filter(AudioClip.id == clip_id, AudioClip.project_id == project_id).first()
    if not clip:
        raise HTTPException(status_code=404, detail=f"AudioClip '{clip_id}' not found.")

    if clip.is_locked and payload.is_locked is not False:
        # Check if trying to edit locked clip
        fields_to_update = payload.model_dump(exclude_unset=True)
        if any(k != "is_locked" for k in fields_to_update):
            raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="Clip is locked against modification.")

    updates = payload.model_dump(exclude_unset=True)
    for field, val in updates.items():
        setattr(clip, field, val)

    db.commit()
    db.refresh(clip)
    return {
        "id": str(clip.id),
        "name": clip.name,
        "volume": clip.volume,
        "mute": clip.mute,
        "ducking_role": clip.ducking_role,
        "ducking_amount_db": clip.ducking_amount_db,
        "is_locked": clip.is_locked,
        "status": clip.status,
    }


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
