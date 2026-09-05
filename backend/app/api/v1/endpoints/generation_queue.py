import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.generation_job import JobCreateRequest, JobResponse
from app.services.job_dispatch import JobDispatchService
from app.models.generation_job import GenerationJob

router = APIRouter()


@router.post("/jobs", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
def create_job(
    request: JobCreateRequest,
    db: Session = Depends(get_db),
):
    job = JobDispatchService.create_and_dispatch_job(
        db=db,
        shot_id=request.shot_id,
        provider_name=request.provider_name,
        idempotency_key=request.idempotency_key,
        custom_params=request.custom_params,
        max_retries=request.max_retries,
    )
    return job


@router.get("/jobs/{job_id}", response_model=JobResponse)
def get_job(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    job = db.query(GenerationJob).filter(GenerationJob.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"GenerationJob {job_id} not found",
        )
    return job


@router.post("/jobs/{job_id}/dispatch", response_model=JobResponse)
async def dispatch_job(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    job = await JobDispatchService.process_job(db=db, job_id=job_id)
    return job


@router.post("/jobs/{job_id}/poll", response_model=JobResponse)
async def poll_job(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    job = await JobDispatchService.poll_job_status(db=db, job_id=job_id)
    return job


@router.get("/shots/{shot_id}/jobs", response_model=List[JobResponse])
def list_shot_jobs(
    shot_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    jobs = (
        db.query(GenerationJob)
        .filter(GenerationJob.shot_id == shot_id)
        .order_by(GenerationJob.created_at.desc())
        .all()
    )
    return jobs
