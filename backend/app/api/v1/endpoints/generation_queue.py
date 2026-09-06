import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.generation_job import JobCreateRequest, JobResponse, ClaimResponse, DispatchRequest
from app.services.job_dispatch import JobDispatchService
from app.models.generation_job import GenerationJob
from app.models.project import Project
from app.models.scene import Scene
from app.models.shot import Shot

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
        reference_images=request.reference_images,
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
    request: DispatchRequest,
    db: Session = Depends(get_db),
):
    claim_token = request.claim_token
    job = await JobDispatchService.process_job(
        db=db, job_id=job_id, claim_token=claim_token
    )
    return job


@router.post("/jobs/{job_id}/poll", response_model=JobResponse)
async def poll_job(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    job = await JobDispatchService.poll_job_status(db=db, job_id=job_id)
    return job


@router.post("/jobs/{job_id}/cancel", response_model=JobResponse)
async def cancel_job(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    job = await JobDispatchService.cancel_job(db=db, job_id=job_id)
    return job


@router.post("/queue/claim", response_model=Optional[ClaimResponse])
def claim_next_job(
    worker_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    job = JobDispatchService.claim_next_job(db=db, worker_id=worker_id)
    return job


@router.post("/queue/recover")
def recover_jobs(
    db: Session = Depends(get_db),
):
    count = JobDispatchService.recover_pending_jobs(db=db)
    return {"recovered_count": count}


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


@router.get("/projects/{project_id}/jobs", response_model=List[JobResponse])
def list_project_jobs(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found",
        )
    jobs = (
        db.query(GenerationJob)
        .join(Shot, GenerationJob.shot_id == Shot.id)
        .join(Scene, Shot.scene_id == Scene.id)
        .filter((Scene.project_id == project_id) | (Scene.story.has(project_id=project_id)))
        .order_by(GenerationJob.created_at.desc())
        .all()
    )
    return jobs


@router.post("/projects/{project_id}/jobs/batch", response_model=List[JobResponse])
def batch_generate_project_shots(
    project_id: uuid.UUID,
    provider_name: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found",
        )
    scenes = (
        db.query(Scene)
        .filter((Scene.project_id == project_id) | (Scene.story.has(project_id=project_id)))
        .all()
    )
    created_jobs = []
    for scene in scenes:
        shots = db.query(Shot).filter(Shot.scene_id == scene.id).all()
        for shot in shots:
            if shot.is_locked:
                continue
            if shot.shot_type not in ("AI_GENERATED", "MIXED"):
                continue
            active_job = (
                db.query(GenerationJob)
                .filter(
                    GenerationJob.shot_id == shot.id,
                    GenerationJob.status.in_(["PENDING", "CLAIMED", "SUBMITTED", "POLLING"]),
                )
                .first()
            )
            if active_job:
                continue

            job = JobDispatchService.create_and_dispatch_job(
                db=db,
                shot_id=shot.id,
                provider_name=provider_name or "vidu",
            )
            created_jobs.append(job)
    return created_jobs
