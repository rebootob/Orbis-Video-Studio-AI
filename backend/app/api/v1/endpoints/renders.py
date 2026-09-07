import uuid
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.render_job import (
    RenderJobSubmitRequest,
    RenderJobRead,
    RenderJobListResponse,
    ExportBatchSubmitRequest,
    RenderBatchRead,
    ExportPresetRead,
)
from app.services.render_job import RenderJobService
from app.services.export_preset import ExportPresetService
from app.models.render_job import RenderJobStatus

router = APIRouter()


@router.get("/presets", response_model=List[ExportPresetRead])
def list_export_presets():
    """List system export presets with dimensions, codecs, and cost estimates."""
    return ExportPresetService.list_presets()


@router.post("/export-batch", response_model=RenderBatchRead)
def submit_export_batch(
    project_id: uuid.UUID,
    payload: ExportBatchSubmitRequest,
    db: Session = Depends(get_db),
):
    """Submit a multi-variant export batch for an approved timeline revision."""
    return RenderJobService.submit_export_batch(
        db=db,
        project_id=project_id,
        preset_ids=payload.preset_ids,
        timeline_id=payload.timeline_id,
    )


@router.get("/batches/{batch_id}", response_model=RenderBatchRead)
def get_render_batch(
    project_id: uuid.UUID,
    batch_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    """Get render batch status and child variant progress."""
    return RenderJobService.get_render_batch(db=db, project_id=project_id, batch_id=batch_id)


@router.post("/submit", response_model=RenderJobRead)
@router.post("", response_model=RenderJobRead)
def submit_render_job(
    project_id: uuid.UUID,
    payload: RenderJobSubmitRequest = RenderJobSubmitRequest(),
    db: Session = Depends(get_db),
):
    """Submit a timeline render job for an approved timeline revision."""
    return RenderJobService.submit_render_job(
        db=db,
        project_id=project_id,
        timeline_id=payload.timeline_id,
        render_profile=payload.render_profile,
        custom_idempotency_key=payload.idempotency_key,
    )


@router.get("/latest", response_model=RenderJobRead)
def get_latest_render_job(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    """Fetch status and progress of the latest render job for project."""
    job = RenderJobService.get_latest_render_job(db=db, project_id=project_id)
    if not job:
        raise HTTPException(status_code=404, detail="No render jobs found for project")
    return job


@router.get("/{render_id}", response_model=RenderJobRead)
def get_render_job(
    project_id: uuid.UUID,
    render_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    """Fetch detailed render job state by ID."""
    return RenderJobService.get_render_job(db=db, project_id=project_id, render_job_id=render_id)


@router.get("", response_model=RenderJobListResponse)
def list_render_jobs(
    project_id: uuid.UUID,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Get paginated list of render job history."""
    renders, total_count = RenderJobService.list_render_jobs(
        db=db, project_id=project_id, offset=offset, limit=limit
    )
    return RenderJobListResponse(
        renders=renders,
        total_count=total_count,
        offset=offset,
        limit=limit,
    )


@router.post("/{render_id}/cancel", response_model=RenderJobRead)
def cancel_render_job(
    project_id: uuid.UUID,
    render_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    """Cancel a queued or running render job."""
    return RenderJobService.cancel_render_job(db=db, project_id=project_id, render_job_id=render_id)


@router.post("/{render_id}/retry", response_model=RenderJobRead)
def retry_render_job(
    project_id: uuid.UUID,
    render_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    """Retry a failed render job."""
    return RenderJobService.retry_render_job(db=db, project_id=project_id, render_job_id=render_id)
