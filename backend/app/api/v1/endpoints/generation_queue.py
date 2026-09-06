import uuid
from typing import List, Optional, Literal
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from pydantic import BaseModel
from app.db.session import get_db
from app.schemas.generation_job import (
    JobCreateRequest,
    JobResponse,
    ClaimResponse,
    DispatchRequest,
    BatchRunResponse,
    BatchRunSummaryResponse,
    BatchRunDetailResponse,
    BatchResumeRequest,
    BatchResumeEstimateResponse,
)
from app.services.job_dispatch import JobDispatchService, ALLOWED_PRODUCTION_STATUSES, resolve_shot_project
from app.services.pricing import ProviderPricingService, CostStatus
from app.providers.factory import ProviderFactory
from app.models.generation_job import GenerationJob
from app.models.project import Project
from app.models.story import Story
from app.models.scene import Scene
from app.models.shot import Shot

router = APIRouter()


@router.post("/jobs", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
def create_job(
    request: JobCreateRequest,
    db: Session = Depends(get_db),
):
    shot = db.get(Shot, request.shot_id)
    if not shot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Shot '{request.shot_id}' not found",
        )
    project = resolve_shot_project(db, shot)

    if project and project.status not in ALLOWED_PRODUCTION_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Production generation requires 'SHOT_PLAN_APPROVED' stage, current project status is '{project.status}'.",
        )

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


class BatchJobCreateRequest(BaseModel):
    operation_type: Literal["CONTINUE_INCOMPLETE", "RETRY_FAILED", "GENERATE_SELECTED"] = "CONTINUE_INCOMPLETE"
    shot_ids: Optional[List[uuid.UUID]] = None
    provider_name: Optional[str] = None
    only_incomplete: bool = True


@router.post("/projects/{project_id}/jobs/estimate", response_model=BatchResumeEstimateResponse)
def estimate_project_batch_jobs(
    project_id: uuid.UUID,
    request: Optional[BatchJobCreateRequest] = None,
    db: Session = Depends(get_db),
):
    req = request or BatchJobCreateRequest()
    from app.services.batch_resume import BatchResumeService
    return BatchResumeService.estimate_batch(
        db=db,
        project_id=project_id,
        operation_type=req.operation_type,
        shot_ids=req.shot_ids,
        provider_name=req.provider_name,
        only_incomplete=req.only_incomplete,
    )


@router.post("/projects/{project_id}/jobs/batch", response_model=List[JobResponse])
def batch_generate_project_shots(
    project_id: uuid.UUID,
    request: Optional[BatchJobCreateRequest] = None,
    provider_name: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    req = request or BatchJobCreateRequest()
    eff_provider = req.provider_name or provider_name
    from app.services.batch_resume import BatchResumeService

    estimate = BatchResumeService.estimate_batch(
        db=db,
        project_id=project_id,
        operation_type=req.operation_type,
        shot_ids=req.shot_ids,
        provider_name=eff_provider,
        only_incomplete=req.only_incomplete,
    )
    if estimate.get("shot_count", 0) > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Batch operation exceeds legacy endpoint list capacity ({estimate['shot_count']} eligible shots > 100 limit). "
                "Use canonical 'POST /projects/{project_id}/jobs/resume' for large or unbounded batch runs."
            ),
        )

    batch_run, jobs = BatchResumeService.execute_batch(
        db=db,
        project_id=project_id,
        operation_type=req.operation_type,
        shot_ids=req.shot_ids,
        provider_name=eff_provider,
        only_incomplete=req.only_incomplete,
        max_queued_jobs=100,
    )
    return jobs


@router.post("/projects/{project_id}/jobs/resume", response_model=BatchRunSummaryResponse)
def resume_project_jobs(
    project_id: uuid.UUID,
    request: Optional[BatchResumeRequest] = None,
    db: Session = Depends(get_db),
):
    req = request or BatchResumeRequest()
    from app.services.batch_resume import BatchResumeService
    batch_run, jobs = BatchResumeService.execute_batch(
        db=db,
        project_id=project_id,
        operation_type=req.operation_type,
        shot_ids=req.shot_ids,
        provider_name=req.provider_name,
        only_incomplete=req.only_incomplete,
        accumulate_jobs=False,
    )
    return batch_run


@router.get("/projects/{project_id}/batch-runs", response_model=List[BatchRunSummaryResponse])
def list_project_batch_runs(
    project_id: uuid.UUID,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    from app.services.batch_resume import BatchResumeService
    return BatchResumeService.list_project_batch_runs(
        db=db,
        project_id=project_id,
        limit=limit,
        offset=offset,
    )


@router.get("/projects/{project_id}/batch-runs/{run_id}", response_model=BatchRunDetailResponse)
def get_batch_run_details(
    project_id: uuid.UUID,
    run_id: uuid.UUID,
    item_limit: int = Query(100, ge=1, le=500),
    item_offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    from app.services.batch_resume import BatchResumeService
    return BatchResumeService.get_batch_run_details(
        db=db,
        project_id=project_id,
        run_id=run_id,
        item_limit=item_limit,
        item_offset=item_offset,
    )
