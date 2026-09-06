import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from pydantic import BaseModel
from app.db.session import get_db
from app.schemas.generation_job import JobCreateRequest, JobResponse, ClaimResponse, DispatchRequest
from app.services.job_dispatch import JobDispatchService
from app.services.pricing import ProviderPricingService, CostStatus
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


class BatchJobCreateRequest(BaseModel):
    shot_ids: Optional[List[uuid.UUID]] = None
    provider_name: Optional[str] = None
    only_incomplete: bool = True


class BatchJobEstimateResponse(BaseModel):
    shot_count: int
    estimated_cost_total: Optional[float] = None
    currency: str = "USD"
    has_unknown_pricing: bool = False
    warning_messages: List[str] = []


@router.post("/projects/{project_id}/jobs/estimate", response_model=BatchJobEstimateResponse)
def estimate_project_batch_jobs(
    project_id: uuid.UUID,
    request: Optional[BatchJobCreateRequest] = None,
    db: Session = Depends(get_db),
):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found",
        )

    req = request or BatchJobCreateRequest()
    scenes = (
        db.query(Scene)
        .filter((Scene.project_id == project_id) | (Scene.story.has(project_id=project_id)))
        .all()
    )

    candidate_shots = []
    for scene in scenes:
        shots = db.query(Shot).filter(Shot.scene_id == scene.id).all()
        for shot in shots:
            if req.shot_ids is not None and shot.id not in req.shot_ids:
                continue
            if shot.is_locked:
                continue
            if shot.shot_type not in ("AI_GENERATED", "MIXED"):
                continue
            if req.only_incomplete:
                completed_job = (
                    db.query(GenerationJob)
                    .filter(
                        GenerationJob.shot_id == shot.id,
                        GenerationJob.status == "COMPLETED",
                    )
                    .first()
                )
                if completed_job:
                    continue
            candidate_shots.append(shot)

    total_cost = 0.0
    has_unknown = False
    provider = req.provider_name or "vidu"

    for shot in candidate_shots:
        cost, curr, status_flag = ProviderPricingService.estimate_cost(
            provider=provider,
            operation="VIDEO_GENERATION",
            params={"duration_seconds": shot.duration_seconds},
        )
        if status_flag == CostStatus.UNKNOWN or cost is None:
            has_unknown = True
        else:
            total_cost += cost

    warnings = []
    if has_unknown:
        warnings.append("Cost pricing is UNKNOWN for one or more candidate shots. Prices will not be fabricated.")
    if project.budget_limit is not None:
        from app.services.budget import BudgetService
        summary = BudgetService.get_project_budget_summary(db, project_id)
        if summary.hard_limit_exceeded:
            warnings.append("Project is currently over hard budget limit. Dispatch will be rejected by safety gates.")
        elif summary.soft_limit_exceeded:
            warnings.append(f"Project spend has exceeded soft threshold ({project.budget_threshold_percentage}%).")

    return BatchJobEstimateResponse(
        shot_count=len(candidate_shots),
        estimated_cost_total=round(total_cost, 4) if not has_unknown else None,
        currency="USD",
        has_unknown_pricing=has_unknown,
        warning_messages=warnings,
    )


@router.post("/projects/{project_id}/jobs/batch", response_model=List[JobResponse])
def batch_generate_project_shots(
    project_id: uuid.UUID,
    request: Optional[BatchJobCreateRequest] = None,
    provider_name: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found",
        )

    req = request or BatchJobCreateRequest()
    eff_provider = req.provider_name or provider_name or "vidu"

    scenes = (
        db.query(Scene)
        .filter((Scene.project_id == project_id) | (Scene.story.has(project_id=project_id)))
        .all()
    )
    created_jobs = []
    for scene in scenes:
        shots = db.query(Shot).filter(Shot.scene_id == scene.id).all()
        for shot in shots:
            if req.shot_ids is not None and shot.id not in req.shot_ids:
                continue
            if shot.is_locked:
                continue
            if shot.shot_type not in ("AI_GENERATED", "MIXED"):
                continue

            if req.only_incomplete:
                completed = (
                    db.query(GenerationJob)
                    .filter(
                        GenerationJob.shot_id == shot.id,
                        GenerationJob.status == "COMPLETED",
                    )
                    .first()
                )
                if completed:
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
                provider_name=eff_provider,
            )
            created_jobs.append(job)
    return created_jobs
