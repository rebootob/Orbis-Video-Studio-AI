import os
import uuid
import secrets
import time
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Tuple, Dict, Any
from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.models.project import Project
from app.models.assembly import AssemblyTimeline
from app.models.qc import ApprovalRecord
from app.models.render_job import RenderJob, RenderJobStatus
from app.models.usage_ledger import UsageLedger
from app.models.asset import Asset
from app.services.budget import BudgetService


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class RenderJobService:
    @classmethod
    def submit_render_job(
        cls,
        db: Session,
        project_id: uuid.UUID,
        timeline_id: Optional[uuid.UUID] = None,
        render_profile: str = "MASTER_HD",
        custom_idempotency_key: Optional[str] = None,
        estimated_cost_usd: float = 0.50,
    ) -> RenderJob:
        # 1. Resolve Timeline for project
        if timeline_id:
            timeline = (
                db.query(AssemblyTimeline)
                .filter(
                    AssemblyTimeline.project_id == project_id,
                    AssemblyTimeline.id == timeline_id,
                )
                .first()
            )
            if not timeline:
                raise HTTPException(status_code=404, detail="Specified timeline not found for project")
        else:
            timeline = (
                db.query(AssemblyTimeline)
                .filter(AssemblyTimeline.project_id == project_id)
                .order_by(AssemblyTimeline.version.desc())
                .first()
            )
            if not timeline:
                raise HTTPException(status_code=404, detail="No active timeline found for project")

        # 2. Approval Gate Verification
        approval = (
            db.query(ApprovalRecord)
            .filter(
                ApprovalRecord.project_id == project_id,
                ApprovalRecord.timeline_id == timeline.id,
                ApprovalRecord.timeline_version == timeline.version,
                ApprovalRecord.status == "APPROVED",
            )
            .first()
        )
        if not approval:
            raise HTTPException(
                status_code=400,
                detail=f"Timeline version {timeline.version} is not approved. Final approval is required before rendering.",
            )

        # 3. Idempotency Check
        base_idempotency_key = f"{project_id}:{timeline.id}:{timeline.version}:{render_profile}"
        target_key = custom_idempotency_key or base_idempotency_key

        # Check for active render job (QUEUED, CLAIMED, RUNNING) for this project + timeline
        active_job = (
            db.query(RenderJob)
            .filter(
                RenderJob.project_id == project_id,
                RenderJob.timeline_id == timeline.id,
                RenderJob.status.in_([
                    RenderJobStatus.QUEUED.value,
                    RenderJobStatus.CLAIMED.value,
                    RenderJobStatus.RUNNING.value,
                ]),
            )
            .first()
        )
        if active_job:
            # Active render job exists -> Return existing job (Idempotent NO_OP replay)
            return active_job

        # Check if completed job exists with identical idempotency key
        completed_job = (
            db.query(RenderJob)
            .filter(
                RenderJob.project_id == project_id,
                RenderJob.idempotency_key == target_key,
                RenderJob.status == RenderJobStatus.COMPLETED.value,
            )
            .first()
        )
        if completed_job and custom_idempotency_key:
            return completed_job
        elif completed_job and not custom_idempotency_key:
            # User triggers new render for approved timeline without custom key -> generate timestamped key
            target_key = f"{base_idempotency_key}:{int(time.time())}"

        # 4. Atomic Budget Check with Row Locking
        BudgetService.check_budget_before_dispatch(
            db=db,
            project_id=project_id,
            estimated_cost=estimated_cost_usd,
            lock_row=True,
        )

        # 5. Create RenderJob Entity
        now = utc_now()
        render_job = RenderJob(
            project_id=project_id,
            timeline_id=timeline.id,
            timeline_version=timeline.version,
            approval_id=approval.id,
            render_profile=render_profile,
            status=RenderJobStatus.QUEUED.value,
            idempotency_key=target_key,
            progress=0.0,
            retry_count=0,
            max_retries=3,
            estimated_cost_usd=estimated_cost_usd,
            render_metadata={
                "timeline_version": timeline.version,
                "render_profile": render_profile,
                "approval_id": str(approval.id),
                "qc_run_id": str(approval.qc_run_id),
            },
            created_at=now,
            updated_at=now,
        )
        db.add(render_job)
        db.flush()

        # 6. Create UsageLedger Pre-Compute Cost Reservation (ESTIMATED)
        ledger_entry = UsageLedger(
            project_id=project_id,
            render_job_id=render_job.id,
            provider="ORBIS_RENDER",
            operation="RENDER_VIDEO",
            estimated_cost=estimated_cost_usd,
            actual_cost=None,
            currency="USD",
            cost_status="ESTIMATED",
            idempotency_key=f"render_reserve_{render_job.id}",
            description=f"Pre-render compute cost reservation for timeline v{timeline.version}",
            created_at=now,
            updated_at=now,
        )
        db.add(ledger_entry)
        db.commit()
        db.refresh(render_job)
        return render_job

    @classmethod
    def claim_next_render_job(
        cls,
        db: Session,
        worker_id: str,
        lease_duration_seconds: int = 300,
    ) -> Optional[RenderJob]:
        now = utc_now()

        # Candidate query: QUEUED or expired lease CLAIMED/RUNNING with remaining retries
        query = (
            db.query(RenderJob)
            .filter(
                (RenderJob.status == RenderJobStatus.QUEUED.value)
                | (
                    (RenderJob.status.in_([RenderJobStatus.CLAIMED.value, RenderJobStatus.RUNNING.value]))
                    & (RenderJob.claim_expires_at <= now)
                    & (RenderJob.retry_count < RenderJob.max_retries)
                )
            )
            .order_by(RenderJob.created_at.asc())
        )

        try:
            query = query.with_for_update(skip_locked=True)
        except Exception:
            pass

        job = query.first()
        if not job:
            return None

        # Lock candidate and update claim token
        token = secrets.token_hex(16)
        if job.status in (RenderJobStatus.CLAIMED.value, RenderJobStatus.RUNNING.value):
            job.retry_count += 1

        job.status = RenderJobStatus.CLAIMED.value
        job.claimed_by = worker_id
        job.claim_token = token
        job.claim_expires_at = now + timedelta(seconds=lease_duration_seconds)
        if not job.started_at:
            job.started_at = now
        job.updated_at = now

        db.commit()
        db.refresh(job)
        return job

    @classmethod
    def extend_lease(
        cls,
        db: Session,
        render_job_id: uuid.UUID,
        claim_token: str,
        extend_seconds: int = 300,
    ) -> bool:
        job = db.get(RenderJob, render_job_id)
        if not job or job.claim_token != claim_token:
            return False
        if job.status not in (RenderJobStatus.CLAIMED.value, RenderJobStatus.RUNNING.value):
            return False
        now = utc_now()
        expires_at = job.claim_expires_at.replace(tzinfo=timezone.utc) if (job.claim_expires_at and job.claim_expires_at.tzinfo is None) else job.claim_expires_at
        if expires_at and expires_at <= now:
            # Lease has already expired and may have been reclaimed by another worker -> Fenced out
            return False

        job.claim_expires_at = now + timedelta(seconds=extend_seconds)
        job.status = RenderJobStatus.RUNNING.value
        job.updated_at = now
        db.commit()
        return True

    @classmethod
    def update_progress(
        cls,
        db: Session,
        render_job_id: uuid.UUID,
        claim_token: str,
        progress: float,
    ) -> bool:
        job = db.get(RenderJob, render_job_id)
        if not job or job.claim_token != claim_token:
            return False

        now = utc_now()
        expires_at = job.claim_expires_at.replace(tzinfo=timezone.utc) if (job.claim_expires_at and job.claim_expires_at.tzinfo is None) else job.claim_expires_at
        if expires_at and expires_at <= now:
            # Lease expired -> Fenced out
            return False

        job.progress = max(0.0, min(100.0, progress))
        job.status = RenderJobStatus.RUNNING.value
        job.updated_at = now
        db.commit()
        return True

    @classmethod
    def complete_render_job(
        cls,
        db: Session,
        render_job_id: uuid.UUID,
        claim_token: str,
        output_asset_id: uuid.UUID,
        actual_cost_usd: float,
        render_metadata: Optional[Dict[str, Any]] = None,
    ) -> RenderJob:
        job = db.get(RenderJob, render_job_id)
        if not job or job.claim_token != claim_token:
            raise HTTPException(status_code=400, detail="Stale worker claim token: job not found or claim token mismatched")

        now = utc_now()
        expires_at = job.claim_expires_at.replace(tzinfo=timezone.utc) if (job.claim_expires_at and job.claim_expires_at.tzinfo is None) else job.claim_expires_at
        if expires_at and expires_at <= now:
            raise HTTPException(status_code=400, detail="Stale worker lease: claim lease has expired")

        job.status = RenderJobStatus.COMPLETED.value
        job.progress = 100.0
        job.output_asset_id = output_asset_id
        job.actual_cost_usd = actual_cost_usd
        job.completed_at = now
        job.updated_at = now

        if render_metadata:
            meta = dict(job.render_metadata or {})
            meta.update(render_metadata)
            job.render_metadata = meta

        # Reconcile UsageLedger: ESTIMATED -> CONFIRMED
        ledger_entry = (
            db.query(UsageLedger)
            .filter(UsageLedger.render_job_id == job.id)
            .first()
        )
        if ledger_entry:
            ledger_entry.cost_status = "CONFIRMED"
            ledger_entry.actual_cost = actual_cost_usd
            ledger_entry.updated_at = now

        db.commit()
        db.refresh(job)
        return job

    @classmethod
    def fail_render_job(
        cls,
        db: Session,
        render_job_id: uuid.UUID,
        claim_token: Optional[str],
        error_message: str,
        ambiguous: bool = False,
    ) -> RenderJob:
        job = db.get(RenderJob, render_job_id)
        if not job:
            raise HTTPException(status_code=404, detail="RenderJob not found")

        # Stale worker fencing: verify token if token was supplied
        now = utc_now()
        expires_at = job.claim_expires_at.replace(tzinfo=timezone.utc) if (job.claim_expires_at and job.claim_expires_at.tzinfo is None) else job.claim_expires_at
        if claim_token and job.claim_token and (job.claim_token != claim_token or (expires_at and expires_at <= now)):
            raise HTTPException(status_code=400, detail="Stale worker token: claim ownership was lost or lease expired")

        now = utc_now()
        was_running_or_claimed = job.status in (RenderJobStatus.CLAIMED.value, RenderJobStatus.RUNNING.value)
        job.updated_at = now

        if ambiguous:
            # Ambiguous failure (e.g. S3 succeeded but DB crashed) -> RECONCILIATION_REQUIRED
            job.status = RenderJobStatus.RECONCILIATION_REQUIRED.value
            job.error_message = error_message
            # Reserved ESTIMATED cost MUST NOT be released!
        else:
            if job.retry_count < job.max_retries:
                # Reset to QUEUED for worker retry
                job.status = RenderJobStatus.QUEUED.value
                job.claimed_by = None
                job.claim_token = None
                job.claim_expires_at = None
                job.error_message = f"Retryable error: {error_message}"
            else:
                # Terminal failure
                job.status = RenderJobStatus.FAILED.value
                job.error_message = error_message

                ledger_entry = (
                    db.query(UsageLedger)
                    .filter(UsageLedger.render_job_id == job.id)
                    .first()
                )
                if ledger_entry:
                    if not was_running_or_claimed:
                        # Proven PRE-EXECUTION failure -> release cost to 0
                        ledger_entry.cost_status = "ADJUSTED"
                        ledger_entry.actual_cost = 0.0
                    else:
                        # Execution was in progress -> preserve ESTIMATED cost reservation
                        ledger_entry.cost_status = "ESTIMATED"
                    ledger_entry.updated_at = now

        db.commit()
        db.refresh(job)
        return job

    @classmethod
    def cancel_render_job(
        cls,
        db: Session,
        project_id: uuid.UUID,
        render_job_id: uuid.UUID,
    ) -> RenderJob:
        job = (
            db.query(RenderJob)
            .filter(
                RenderJob.id == render_job_id,
                RenderJob.project_id == project_id,
            )
            .first()
        )
        if not job:
            raise HTTPException(status_code=404, detail="RenderJob not found for project")

        if job.status in (
            RenderJobStatus.COMPLETED.value,
            RenderJobStatus.FAILED.value,
            RenderJobStatus.CANCELLED.value,
        ):
            raise HTTPException(
                status_code=400,
                detail=f"Cannot cancel render job in terminal status {job.status}",
            )

        now = utc_now()
        was_queued = (job.status == RenderJobStatus.QUEUED.value)

        job.status = RenderJobStatus.CANCELLED.value
        job.error_message = "Cancelled by user"
        job.updated_at = now

        ledger_entry = (
            db.query(UsageLedger)
            .filter(UsageLedger.render_job_id == job.id)
            .first()
        )
        if ledger_entry:
            if was_queued:
                # Pre-execution cancellation -> release cost to 0
                ledger_entry.cost_status = "ADJUSTED"
                ledger_entry.actual_cost = 0.0
            else:
                # Compute was in progress (RUNNING / CLAIMED) -> preserve ESTIMATED cost reservation
                ledger_entry.cost_status = "ESTIMATED"
            ledger_entry.updated_at = now

        db.commit()
        db.refresh(job)
        return job

    @classmethod
    def retry_render_job(
        cls,
        db: Session,
        project_id: uuid.UUID,
        render_job_id: uuid.UUID,
    ) -> RenderJob:
        job = (
            db.query(RenderJob)
            .filter(
                RenderJob.id == render_job_id,
                RenderJob.project_id == project_id,
            )
            .first()
        )
        if not job:
            raise HTTPException(status_code=404, detail="RenderJob not found for project")

        if job.status not in (RenderJobStatus.FAILED.value, RenderJobStatus.CANCELLED.value):
            raise HTTPException(
                status_code=400,
                detail=f"Cannot retry render job in status {job.status}",
            )

        # Concurrency-safe project budget check before re-reserving budget
        BudgetService.check_budget_before_dispatch(
            db=db,
            project_id=project_id,
            estimated_cost=job.estimated_cost_usd,
            lock_row=True,
        )

        now = utc_now()
        job.status = RenderJobStatus.QUEUED.value
        job.retry_count = 0
        job.claimed_by = None
        job.claim_token = None
        job.claim_expires_at = None
        job.error_message = None
        job.updated_at = now

        # Ensure active ESTIMATED reservation exists in UsageLedger
        ledger_entry = (
            db.query(UsageLedger)
            .filter(UsageLedger.render_job_id == job.id)
            .first()
        )
        if ledger_entry:
            ledger_entry.cost_status = "ESTIMATED"
            ledger_entry.estimated_cost = job.estimated_cost_usd
            ledger_entry.updated_at = now
        else:
            ledger_entry = UsageLedger(
                project_id=project_id,
                render_job_id=job.id,
                provider="ORBIS_RENDER",
                operation="RENDER_VIDEO",
                estimated_cost=job.estimated_cost_usd,
                actual_cost=None,
                currency="USD",
                cost_status="ESTIMATED",
                idempotency_key=f"render_reserve_{job.id}",
                description=f"Pre-render compute cost reservation (retry) for timeline v{job.timeline_version}",
                created_at=now,
                updated_at=now,
            )
            db.add(ledger_entry)

        db.commit()
        db.refresh(job)
        return job

    @classmethod
    def get_latest_render_job(
        cls,
        db: Session,
        project_id: uuid.UUID,
    ) -> Optional[RenderJob]:
        return (
            db.query(RenderJob)
            .filter(RenderJob.project_id == project_id)
            .order_by(RenderJob.created_at.desc())
            .first()
        )

    @classmethod
    def get_render_job(
        cls,
        db: Session,
        project_id: uuid.UUID,
        render_job_id: uuid.UUID,
    ) -> RenderJob:
        job = (
            db.query(RenderJob)
            .filter(
                RenderJob.id == render_job_id,
                RenderJob.project_id == project_id,
            )
            .first()
        )
        if not job:
            raise HTTPException(status_code=404, detail="RenderJob not found for project")
        return job

    @classmethod
    def list_render_jobs(
        cls,
        db: Session,
        project_id: uuid.UUID,
        offset: int = 0,
        limit: int = 50,
    ) -> Tuple[List[RenderJob], int]:
        limit = min(max(1, limit), 100)
        query = db.query(RenderJob).filter(RenderJob.project_id == project_id)
        total_count = query.count()
        renders = (
            query.order_by(RenderJob.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        return renders, total_count

    @classmethod
    def create_render_output_asset(
        cls,
        db: Session,
        project_id: uuid.UUID,
        storage_bucket: str,
        storage_key: str,
        duration_seconds: float,
        file_size_bytes: int,
        checksum_sha256: str,
    ) -> Asset:
        filename = os.path.basename(storage_key)
        asset = Asset(
            project_id=project_id,
            name=f"Render Master Output ({filename})",
            original_filename=filename,
            asset_type="VIDEO",
            content_type="video/mp4",
            storage_bucket=storage_bucket,
            storage_key=storage_key,
            file_size_bytes=file_size_bytes,
            checksum_sha256=checksum_sha256,
            is_locked=True,
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        db.add(asset)
        db.flush()
        return asset
