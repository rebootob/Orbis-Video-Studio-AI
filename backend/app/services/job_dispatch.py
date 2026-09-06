import logging
import uuid
import re
import httpx
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException, status

from app.models.shot import Shot
from app.models.generation_job import GenerationJob
from app.providers.base import VideoGenerationParams, ProviderJobResult
from app.providers.factory import ProviderFactory

logger = logging.getLogger(__name__)


def is_retryable_error(
    status_code: Optional[int] = None,
    exc: Optional[Exception] = None,
    error_message: Optional[str] = None,
) -> bool:
    """
    Retry classification:
    RETRY: network, timeout, 429, eligible 5xx
    NO RETRY: config/validation, 400, 401, 403, provider rejection, unsupported provider/config
    """
    if isinstance(exc, (ValueError, TypeError, KeyError)):
        return False

    if isinstance(
        exc,
        (
            httpx.TimeoutException,
            httpx.NetworkError,
            httpx.ConnectError,
            httpx.ConnectTimeout,
            httpx.ReadTimeout,
        ),
    ):
        return True

    if status_code is not None:
        if status_code == 429:
            return True
        if 500 <= status_code <= 599:
            return True
        if status_code in (400, 401, 403, 404, 422):
            return False

    if error_message:
        lower_msg = error_message.lower()
        non_retryable_markers = [
            "http 400",
            "http 401",
            "http 403",
            "http 404",
            "http 422",
            "unsupported provider",
            "unauthorized",
            "forbidden",
            "rejected",
            "moderation",
            "nsfw",
            "policy violation",
            "invalid configuration",
            "validation error",
            "bad request",
            "quota exceeded",
            "api key missing",
        ]
        for marker in non_retryable_markers:
            if marker in lower_msg:
                return False

        retryable_markers = [
            "timeout",
            "timed out",
            "rate limit",
            "429",
            "http 500",
            "http 502",
            "http 503",
            "http 504",
            "connection error",
            "connection reset",
            "network error",
        ]
        for marker in retryable_markers:
            if marker in lower_msg:
                return True

    return False


def sanitize_secret_text(text: Optional[str]) -> Optional[str]:
    if not text:
        return text
    sanitized = re.sub(
        r'(Token|Bearer|key|api_key|secret|password)\s*[:=]?\s*[A-Za-z0-9_\-\.]+',
        r'\1 [REDACTED]',
        text,
        flags=re.IGNORECASE,
    )
    return sanitized


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

        try:
            db.add(job)
            db.commit()
            db.refresh(job)
            return job
        except IntegrityError:
            db.rollback()
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
            raise

    @staticmethod
    def claim_next_job(db: Session, worker_id: Optional[str] = None) -> Optional[GenerationJob]:
        """Atomically claims the next eligible PENDING job using DB-level concurrency controls."""
        query = (
            db.query(GenerationJob)
            .filter(
                GenerationJob.status == "PENDING",
                GenerationJob.retry_count < GenerationJob.max_retries,
            )
            .order_by(GenerationJob.created_at.asc())
        )
        if db.bind and db.bind.dialect.name == "postgresql":
            job = query.with_for_update(skip_locked=True).first()
            if job:
                job.status = "CLAIMED"
                db.commit()
                db.refresh(job)
                return job
            return None
        else:
            candidates = query.limit(10).all()
            for cand in candidates:
                updated = (
                    db.query(GenerationJob)
                    .filter(
                        GenerationJob.id == cand.id,
                        GenerationJob.status == "PENDING",
                    )
                    .update({"status": "CLAIMED"}, synchronize_session=False)
                )
                if updated > 0:
                    db.commit()
                    db.refresh(cand)
                    return cand
            return None

    @staticmethod
    def recover_pending_jobs(db: Session) -> int:
        """
        Restart recovery for pending/recoverable jobs.
        - Jobs stuck in 'CLAIMED' without provider_job_id are recovered to 'PENDING'
          (or 'FAILED' if max_retries reached).
        - Jobs in 'PROCESSING' with provider_job_id are left intact for polling
          (preventing duplicate provider submission).
        """
        stuck_claimed = (
            db.query(GenerationJob)
            .filter(
                GenerationJob.status == "CLAIMED",
                GenerationJob.provider_job_id.is_(None),
            )
            .all()
        )
        recovered_count = 0
        for job in stuck_claimed:
            if job.retry_count < job.max_retries:
                job.status = "PENDING"
            else:
                job.status = "FAILED"
                job.error_message = "Max retries exceeded during recovery"
            recovered_count += 1

        db.commit()
        return recovered_count

    @staticmethod
    async def process_job(db: Session, job_id: uuid.UUID) -> GenerationJob:
        job = db.query(GenerationJob).filter(GenerationJob.id == job_id).first()
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"GenerationJob {job_id} not found",
            )

        if job.status == "COMPLETED":
            return job

        # Guard: If provider_job_id is already assigned, DO NOT re-submit to provider!
        if job.provider_job_id:
            logger.info(f"Job {job.id} already submitted (provider_job_id={job.provider_job_id}), skipping re-submission.")
            if job.status not in ("PROCESSING", "COMPLETED", "FAILED"):
                job.status = "PROCESSING"
                db.commit()
                db.refresh(job)
            return job

        # Unsupported provider / configuration check (NON-RETRYABLE)
        try:
            adapter = ProviderFactory.get_provider(job.provider_name)
        except Exception as exc:
            job.status = "FAILED"
            job.error_message = sanitize_secret_text(f"Unsupported provider: {str(exc)}")
            db.commit()
            db.refresh(job)
            return job

        gen_params = VideoGenerationParams(**(job.payload or {}))

        # Mark PROCESSING before submitting to prevent race/duplicate submissions
        job.status = "PROCESSING"
        db.commit()

        try:
            res: ProviderJobResult = await adapter.submit_generation_job(gen_params)
        except Exception as exc:
            err_msg = sanitize_secret_text(f"Submission exception: {str(exc)}")
            retryable = is_retryable_error(exc=exc, error_message=err_msg)
            if retryable:
                job.retry_count += 1
                if job.retry_count >= job.max_retries:
                    job.status = "FAILED"
                else:
                    job.status = "PENDING"
            else:
                job.status = "FAILED"
            job.error_message = err_msg
            job.result = {"error": err_msg}
            db.commit()
            db.refresh(job)
            return job

        if res.status == "FAILED":
            err_msg = sanitize_secret_text(res.error_message or "Submission failed")
            job.error_message = err_msg

            status_code = None
            if res.raw_response and isinstance(res.raw_response, dict):
                status_code = res.raw_response.get("status_code")

            retryable = is_retryable_error(status_code=status_code, error_message=err_msg)
            if retryable:
                job.retry_count += 1
                if job.retry_count >= job.max_retries:
                    job.status = "FAILED"
                else:
                    job.status = "PENDING"
            else:
                # Non-retryable: 400, 401, 403, validation, rejection
                job.status = "FAILED"

            job.result = res.raw_response or {"error": err_msg}
        else:
            job.provider_job_id = res.provider_job_id
            job.status = res.status
            if res.cost_usd is not None:
                job.cost_usd = res.cost_usd
            result_data = res.model_dump(exclude={"raw_response"})
            if res.raw_response:
                result_data["provider_data"] = res.raw_response
            job.result = result_data

        db.commit()
        db.refresh(job)
        return job

    @staticmethod
    async def poll_job_status(db: Session, job_id: uuid.UUID, max_polls: int = 60) -> GenerationJob:
        job = db.query(GenerationJob).filter(GenerationJob.id == job_id).first()
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"GenerationJob {job_id} not found",
            )

        if job.status in ("COMPLETED", "FAILED") or not job.provider_job_id:
            return job

        # Bounded polling enforcement
        curr_result = dict(job.result or {})
        poll_count = curr_result.get("_poll_count", 0) + 1
        curr_result["_poll_count"] = poll_count

        if poll_count > max_polls:
            job.status = "FAILED"
            job.error_message = f"Bounded polling limit exceeded ({max_polls} attempts)"
            job.result = curr_result
            db.commit()
            db.refresh(job)
            return job

        try:
            adapter = ProviderFactory.get_provider(job.provider_name)
        except Exception as exc:
            job.error_message = sanitize_secret_text(str(exc))
            job.status = "FAILED"
            db.commit()
            return job

        try:
            res: ProviderJobResult = await adapter.check_job_status(job.provider_job_id)
        except Exception as exc:
            err_msg = sanitize_secret_text(str(exc))
            retryable = is_retryable_error(exc=exc, error_message=err_msg)
            if retryable and job.retry_count + 1 < job.max_retries:
                job.retry_count += 1
                job.status = "PENDING"
            else:
                job.status = "FAILED"
            job.error_message = err_msg
            job.result = curr_result
            db.commit()
            db.refresh(job)
            return job

        job.status = res.status
        job_result = res.model_dump(exclude={"raw_response"})
        job_result["_poll_count"] = poll_count
        if res.raw_response:
            job_result["provider_data"] = res.raw_response
        job.result = job_result

        if res.cost_usd is not None:
            job.cost_usd = res.cost_usd

        if res.status == "FAILED":
            err_msg = sanitize_secret_text(res.error_message or "Job processing failed at provider")
            job.error_message = err_msg
            status_code = None
            if res.raw_response and isinstance(res.raw_response, dict):
                status_code = res.raw_response.get("status_code")

            retryable = is_retryable_error(status_code=status_code, error_message=err_msg)
            if retryable and job.retry_count + 1 < job.max_retries:
                job.retry_count += 1
                job.status = "PENDING"
            else:
                job.status = "FAILED"

        elif res.status == "COMPLETED":
            # Output Asset Safety:
            # - NO fake Asset record for external provider URL
            # - NO fake SHA256 / file size / storage metadata
            # - Provider video_url remains in job.result
            shot = db.query(Shot).filter(Shot.id == job.shot_id).first()
            if shot:
                shot.status = "COMPLETED"

        db.commit()
        db.refresh(job)
        return job
