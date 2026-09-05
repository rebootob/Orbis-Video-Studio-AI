import logging
import uuid
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.shot import Shot
from app.models.generation_job import GenerationJob
from app.models.asset import Asset
from app.models.project import Project
from app.models.scene import Scene
from app.models.story import Story
from app.providers.base import VideoGenerationParams, ProviderJobResult
from app.providers.factory import ProviderFactory

logger = logging.getLogger(__name__)


class JobDispatchService:
    @staticmethod
    def create_and_dispatch_job(
        db: Session,
        shot_id: uuid.UUID,
        provider_name: str = "vidu",
        idempotency_key: Optional[str] = None,
        custom_params: Optional[Dict[str, Any]] = None,
        max_retries: int = 3,
    ) -> GenerationJob:
        shot = db.query(Shot).filter(Shot.id == shot_id).first()
        if not shot:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Shot {shot_id} not found",
            )

        if idempotency_key:
            existing_job = (
                db.query(GenerationJob)
                .filter(
                    GenerationJob.shot_id == shot_id,
                    GenerationJob.idempotency_key == idempotency_key,
                )
                .first()
            )
            if existing_job:
                return existing_job

        prompt_text = shot.video_prompt or shot.visual_prompt or shot.action or f"Shot {shot.shot_number}"
        
        gen_params = VideoGenerationParams(
            shot_id=str(shot.id),
            prompt=prompt_text,
            duration_seconds=shot.duration_seconds or 4.0,
            provider_specific_params=custom_params or {},
        )

        job = GenerationJob(
            id=uuid.uuid4(),
            shot_id=shot.id,
            provider_name=provider_name,
            status="PENDING",
            idempotency_key=idempotency_key,
            max_retries=max_retries,
            retry_count=0,
            payload=gen_params.model_dump(),
        )

        db.add(job)
        db.commit()
        db.refresh(job)

        return job

    @staticmethod
    async def process_job(db: Session, job_id: uuid.UUID) -> GenerationJob:
        job = db.query(GenerationJob).filter(GenerationJob.id == job_id).first()
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"GenerationJob {job_id} not found",
            )

        if job.status in ("COMPLETED", "PROCESSING"):
            return job

        try:
            adapter = ProviderFactory.get_provider(job.provider_name)
        except Exception as exc:
            job.status = "FAILED"
            job.error_message = str(exc)
            db.commit()
            db.refresh(job)
            return job

        gen_params = VideoGenerationParams(**(job.payload or {}))
        
        job.status = "PROCESSING"
        db.commit()

        res: ProviderJobResult = await adapter.submit_generation_job(gen_params)

        if res.status == "FAILED":
            job.retry_count += 1
            job.error_message = res.error_message or "Submission failed"
            if job.retry_count >= job.max_retries:
                job.status = "FAILED"
            else:
                job.status = "PENDING"
            job.result = res.model_dump()
        else:
            job.provider_job_id = res.provider_job_id
            job.status = res.status
            if res.cost_usd is not None:
                job.cost_usd = res.cost_usd
            job.result = res.model_dump()

        db.commit()
        db.refresh(job)
        return job

    @staticmethod
    async def poll_job_status(db: Session, job_id: uuid.UUID) -> GenerationJob:
        job = db.query(GenerationJob).filter(GenerationJob.id == job_id).first()
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"GenerationJob {job_id} not found",
            )

        if job.status in ("COMPLETED", "FAILED") or not job.provider_job_id:
            return job

        try:
            adapter = ProviderFactory.get_provider(job.provider_name)
        except Exception as exc:
            job.error_message = str(exc)
            db.commit()
            return job

        res: ProviderJobResult = await adapter.check_job_status(job.provider_job_id)

        job.status = res.status
        job.result = res.model_dump()
        if res.cost_usd is not None:
            job.cost_usd = res.cost_usd

        if res.status == "FAILED":
            job.retry_count += 1
            job.error_message = res.error_message or "Job processing failed at provider"
            if job.retry_count < job.max_retries:
                job.status = "PENDING"

        elif res.status == "COMPLETED" and res.video_url:
            shot = db.query(Shot).filter(Shot.id == job.shot_id).first()
            if shot and shot.scene and shot.scene.story:
                project_id = shot.scene.story.project_id
                asset = Asset(
                    id=uuid.uuid4(),
                    project_id=project_id,
                    name=f"Generated Video - Shot {shot.shot_number}",
                    original_filename=f"shot_{shot.shot_number}_video.mp4",
                    asset_type="VIDEO",
                    content_type="video/mp4",
                    file_size_bytes=0,
                    checksum_sha256="0000000000000000000000000000000000000000000000000000000000000000",
                    storage_bucket="orbis-generated",
                    storage_key=res.video_url,
                    is_locked=False,
                )
                db.add(asset)
                db.flush()
                job.output_asset_id = asset.id
                shot.status = "COMPLETED"

        db.commit()
        db.refresh(job)
        return job
