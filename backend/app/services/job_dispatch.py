"""Durable queue operations. Every external operation is fenced by a DB lease.

Worker flow: recover -> claim -> dispatch(token); poll due jobs separately.
No provider identity after an ambiguous submit requires manual reconciliation.
"""
import threading
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any

import httpx
from fastapi import HTTPException
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.shot import Shot
from app.models.generation_job import GenerationJob as Job
from app.providers.base import VideoGenerationParams, ProviderJobResult
from app.providers.factory import ProviderFactory
from app.providers.safety import (
    contains_secret,
    safe_result,
    sanitize_secret_text,
    strip_secret_keys,
)

LEASE_SECONDS = 120
POLL_SECONDS = 10
RETRY_SECONDS = 5
MAX_BACKOFF_SECONDS = 300
TERMINAL = ("COMPLETED", "FAILED", "CANCELLED", "RECONCILIATION_REQUIRED")
ACTIVE = ("QUEUED", "PROCESSING")

_claim_lock = threading.Lock()


def utc_now():
    return datetime.now(timezone.utc)


def ensure_utc(dt):
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def backoff(attempt):
    return min(MAX_BACKOFF_SECONDS, RETRY_SECONDS * 2 ** min(max(attempt - 1, 0), 6))


def is_retryable_error(status_code=None, exc=None, error_message=None):
    if status_code is not None:
        return status_code == 429 or status_code in (500, 502, 503, 504)
    if exc is not None:
        return isinstance(exc, (httpx.TimeoutException, httpx.NetworkError))
    if error_message is not None:
        msg = error_message.lower()
        if any(w in msg for w in ("400", "401", "403", "unauthorized", "moderation", "policy", "unsupported", "invalid")):
            return False
        if any(w in msg for w in ("504", "503", "502", "500", "429", "timeout", "rate limit")):
            return True
        return False
    return False


def is_result_retryable(res: ProviderJobResult) -> bool:
    if res.status_code is not None:
        return is_retryable_error(status_code=res.status_code)
    if res.error_code == "TRANSPORT_ERROR":
        return True
    if res.error_code in ("PROVIDER_REJECTED", "INVALID_CONFIG", "PROVIDER_ERROR"):
        return False
    return bool(res.retryable)


def due(column, now):
    return or_(column.is_(None), column <= now)


def load(db: Session, job_id):
    job = db.query(Job).populate_existing().filter(Job.id == job_id).first()
    if job is None:
        raise HTTPException(404, "Generation job not found")
    return job


def change(db: Session, filters, values):
    changed = db.query(Job).filter(*filters).update(values, synchronize_session=False)
    db.commit()
    return changed


def released():
    return {"claimed_by": None, "claim_token": None, "claim_expires_at": None}


def failure(exc, submitting=False):
    transient = is_retryable_error(exc=exc)
    safe_before_send = isinstance(exc, (httpx.ConnectError, httpx.ConnectTimeout, httpx.PoolTimeout))
    return ProviderJobResult(
        provider_job_id="",
        status="FAILED",
        error_code="TRANSPORT_ERROR" if transient else "PROVIDER_ERROR",
        retryable=transient,
        submission_uncertain=submitting and not safe_before_send,
    )


class JobDispatchService:
    @staticmethod
    def create_and_dispatch_job(
        db: Session,
        shot_id,
        provider_name="vidu",
        idempotency_key=None,
        custom_params=None,
        max_retries=3,
        reference_images=None,
    ):
        if not 1 <= max_retries <= 10:
            raise HTTPException(400, "max_retries must be between 1 and 10")
        if contains_secret(custom_params or {}) or contains_secret(reference_images or []):
            raise HTTPException(400, "Secret-like generation parameters are not allowed")
        if not isinstance(provider_name, str) or len(provider_name) > 50 or contains_secret(provider_name):
            raise HTTPException(400, "Invalid provider name")
        if idempotency_key is not None and (not idempotency_key or len(idempotency_key) > 255 or contains_secret(idempotency_key)):
            raise HTTPException(400, "Invalid idempotency key")
        shot = db.get(Shot, shot_id)
        if not shot:
            raise HTTPException(404, "Shot not found")
        if idempotency_key:
            existing = db.query(Job).filter_by(shot_id=shot_id, idempotency_key=idempotency_key).first()
            if existing:
                return existing
        prompt = shot.video_prompt or shot.visual_prompt or shot.action or f"Shot {shot.shot_number}"
        if contains_secret(prompt):
            raise HTTPException(400, "Secret-like generation parameters are not allowed")

        clean_custom_params = strip_secret_keys(custom_params or {})
        clean_reference_images = strip_secret_keys(reference_images) if reference_images else None

        try:
            params = VideoGenerationParams(
                shot_id=str(shot_id),
                prompt=prompt,
                duration_seconds=shot.duration_seconds or 4.0,
                reference_images=clean_reference_images,
                provider_specific_params=clean_custom_params,
            )
        except ValueError:
            raise HTTPException(400, "Invalid generation parameters") from None

        job = Job(
            id=uuid.uuid4(),
            shot_id=shot_id,
            provider_name=provider_name,
            status="PENDING",
            idempotency_key=idempotency_key,
            retry_count=0,
            max_retries=max_retries,
            payload=params.model_dump(),
        )
        try:
            db.add(job)
            db.commit()
            return load(db, job.id)
        except IntegrityError:
            db.rollback()
            if idempotency_key:
                existing = db.query(Job).filter_by(shot_id=shot_id, idempotency_key=idempotency_key).first()
                if existing:
                    return existing
            raise

    @staticmethod
    def claim_next_job(
        db: Session,
        worker_id=None,
        lease_duration_seconds=LEASE_SECONDS,
        *,
        now=None,
        job_id=None,
    ):
        now = now or utc_now()
        worker_id = worker_id or "queue-worker"
        if len(worker_id) > 255 or contains_secret(worker_id):
            raise HTTPException(400, "Invalid worker identifier")
        lease_secs = lease_duration_seconds or LEASE_SECONDS
        eligible = [
            Job.status == "PENDING",
            Job.provider_job_id.is_(None),
            Job.submission_attempt_id.is_(None),
            Job.retry_count < Job.max_retries,
            due(Job.next_retry_at, now),
        ]
        if job_id is not None:
            eligible.append(Job.id == job_id)

        with _claim_lock:
            candidate_ids = [
                row[0] for row in db.query(Job.id).filter(*eligible).order_by(Job.created_at, Job.id).limit(100).all()
            ]
            for candidate in candidate_ids:
                claim_token = uuid.uuid4().hex
                if change(db, [Job.id == candidate, *eligible], {
                    "status": "CLAIMED",
                    "claimed_by": worker_id,
                    "claim_token": claim_token,
                    "claim_expires_at": now + timedelta(seconds=lease_secs),
                }):
                    return load(db, candidate)
            return None

    @staticmethod
    def recover_pending_jobs(db: Session, *, now=None):
        now = now or utc_now()
        expired = due(Job.claim_expires_at, now)
        count = 0
        for state, values in (
            ("CLAIMED", {"status": "PENDING"}),
            ("SUBMITTING", {"status": "RECONCILIATION_REQUIRED", "error_message": "Submission outcome unknown; manual reconciliation required"}),
            ("POLLING", {"status": "PROCESSING", "next_poll_at": now + timedelta(seconds=POLL_SECONDS)}),
            ("CANCELLING", {"status": "RECONCILIATION_REQUIRED", "error_message": "Cancellation outcome unknown; manual reconciliation required"}),
        ):
            count += change(db, [Job.status == state, expired], {**released(), **values})
        count += change(db, [Job.status.in_(ACTIVE), Job.provider_job_id.is_(None), expired], {
            **released(), "status": "RECONCILIATION_REQUIRED",
            "error_message": "Provider identity missing; manual reconciliation required",
        })
        return count

    @staticmethod
    async def process_job(db: Session, job_id, *, claim_token=None, worker_id=None, now=None):
        now = now or utc_now()
        job = load(db, job_id)
        if job.status in TERMINAL or job.provider_job_id:
            return job

        if not claim_token:
            raise HTTPException(409, "A valid queue claim is required")

        attempt = uuid.uuid4().hex
        if not change(db, [
            Job.id == job_id,
            Job.status == "CLAIMED",
            Job.claim_token == claim_token,
            Job.claim_expires_at > now,
            Job.provider_job_id.is_(None),
            Job.submission_attempt_id.is_(None),
            Job.retry_count < Job.max_retries,
            due(Job.next_retry_at, now),
        ], {
            "status": "SUBMITTING",
            "submission_attempt_id": attempt,
            "claim_expires_at": now + timedelta(seconds=LEASE_SECONDS),
        }):
            raise HTTPException(409, "Queue claim is invalid or expired")

        job = load(db, job_id)
        try:
            adapter = ProviderFactory.get_provider(job.provider_name)
            params = VideoGenerationParams(**(job.payload or {}))
            if contains_secret(params.model_dump()):
                raise ValueError("Unsafe payload")
            configured = adapter.validate_config({})
        except Exception:
            configured = False

        if not configured:
            res = ProviderJobResult(provider_job_id="", status="FAILED", error_code="INVALID_CONFIG", retryable=False)
        else:
            try:
                res = await adapter.submit_generation_job(params)
            except Exception as exc:
                res = failure(exc, submitting=True)

        values = released()
        values.update(result=safe_result(res), error_message=None, next_retry_at=None)

        retryable = is_result_retryable(res)

        if res.submission_uncertain or (res.status != "FAILED" and not res.provider_job_id):
            values.update(
                status="RECONCILIATION_REQUIRED",
                error_message="Submission outcome unknown; manual reconciliation required",
            )
        elif res.status == "FAILED":
            retries = job.retry_count + (1 if retryable else 0)
            retry = retryable and retries < job.max_retries
            values.update(
                status="PENDING" if retry else "FAILED",
                retry_count=retries,
                error_message=sanitize_secret_text(res.error_message) if res.error_message else ("Transient provider failure" if retryable else "Provider rejected submission"),
                submission_attempt_id=None if retry else attempt,
                next_retry_at=now + timedelta(seconds=backoff(retries)) if retry else None,
            )
        else:
            values.update(
                provider_job_id=res.provider_job_id,
                status=res.status,
                next_poll_at=now + timedelta(seconds=POLL_SECONDS) if res.status in ACTIVE else None,
            )

        change(db, [
            Job.id == job_id,
            Job.status == "SUBMITTING",
            Job.claim_token == claim_token,
            Job.submission_attempt_id == attempt,
        ], values)
        return load(db, job_id)

    @staticmethod
    async def poll_job_status(db: Session, job_id, *, now=None, max_polls=None):
        now = now or utc_now()
        job = load(db, job_id)
        if job.status not in ACTIVE or not job.provider_job_id:
            return job

        limit = min(job.max_polls, max_polls) if max_polls is not None else job.max_polls

        if job.next_poll_at and ensure_utc(job.next_poll_at) > ensure_utc(now):
            return job

        if job.poll_count >= limit:
            values = {
                **released(),
                "status": "FAILED",
                "error_message": "Bounded polling limit exceeded",
                "next_poll_at": None,
            }
            change(db, [Job.id == job_id, Job.status.in_(ACTIVE)], values)
            return load(db, job_id)

        token = uuid.uuid4().hex
        eligible = [Job.id == job_id, Job.status.in_(ACTIVE), due(Job.next_poll_at, now), Job.poll_count < limit]
        if not change(db, eligible, {
            "status": "POLLING",
            "claim_token": token,
            "claimed_by": "poller",
            "claim_expires_at": now + timedelta(seconds=LEASE_SECONDS),
            "poll_count": Job.poll_count + 1,
            "next_poll_at": now + timedelta(seconds=POLL_SECONDS),
        }):
            return load(db, job_id)

        job = load(db, job_id)
        try:
            adapter = ProviderFactory.get_provider(job.provider_name)
            res = await adapter.check_job_status(job.provider_job_id)
        except Exception as exc:
            res = failure(exc)

        values = {
            **released(),
            "result": safe_result(res),
            "error_message": sanitize_secret_text(res.error_message) if res.error_message else None,
            "status": res.status,
            "next_poll_at": now + timedelta(seconds=POLL_SECONDS),
        }
        if res.status == "FAILED":
            retryable = is_result_retryable(res)
            retries = job.retry_count + (1 if retryable else 0)
            retry = retryable and retries < job.max_retries
            values.update(
                status="PROCESSING" if retry else "FAILED",
                retry_count=retries,
                error_message=sanitize_secret_text(res.error_message) if res.error_message else ("Transient status failure" if retryable else "Provider job failed"),
                next_poll_at=now + timedelta(seconds=max(POLL_SECONDS, backoff(retries))) if retry else None,
            )
        elif values["status"] in TERMINAL:
            values["next_poll_at"] = None

        change(db, [Job.id == job_id, Job.status == "POLLING", Job.claim_token == token], values)
        return load(db, job_id)

    @staticmethod
    async def cancel_job(db: Session, job_id, *, now=None):
        now = now or utc_now()
        job = load(db, job_id)
        if job.status in TERMINAL or job.status == "SUBMITTING":
            return job

        if job.provider_job_id is None and job.submission_attempt_id is None:
            if change(db, [
                Job.id == job_id,
                Job.status.in_(("PENDING", "CLAIMED")),
                Job.provider_job_id.is_(None),
                Job.submission_attempt_id.is_(None),
            ], {
                **released(),
                "status": "CANCELLED",
                "next_retry_at": None,
                "next_poll_at": None,
            }):
                return load(db, job_id)
            return job

        if not job.provider_job_id:
            return job

        token = uuid.uuid4().hex
        if not change(db, [
            Job.id == job_id,
            Job.status.in_(ACTIVE),
            Job.provider_job_id.is_not(None),
            due(Job.next_retry_at, now),
        ], {
            "status": "CANCELLING",
            "claim_token": token,
            "claimed_by": "canceller",
            "claim_expires_at": now + timedelta(seconds=LEASE_SECONDS),
        }):
            return load(db, job_id)

        job = load(db, job_id)
        try:
            adapter = ProviderFactory.get_provider(job.provider_name)
            cancelled = await adapter.cancel_job(job.provider_job_id)
        except Exception as exc:
            cancelled = False
            err_text = sanitize_secret_text(str(exc))
        else:
            err_text = "Provider cancellation not confirmed"

        if cancelled:
            values = {
                **released(),
                "status": "CANCELLED",
                "error_message": None,
                "next_retry_at": None,
                "next_poll_at": None,
            }
        else:
            values = {
                **released(),
                "status": "PROCESSING",
                "error_message": sanitize_secret_text(err_text),
                "next_retry_at": now + timedelta(seconds=POLL_SECONDS),
                "next_poll_at": now + timedelta(seconds=POLL_SECONDS),
            }

        change(db, [Job.id == job_id, Job.status == "CANCELLING", Job.claim_token == token], values)
        return load(db, job_id)
