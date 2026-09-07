import os
import uuid
import secrets
import time
import threading
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Tuple, Dict, Any
from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.models.project import Project
from app.models.assembly import AssemblyTimeline
from app.models.qc import ApprovalRecord
from app.models.render_job import RenderJob, RenderJobStatus
from app.models.render_batch import RenderBatch
from app.models.usage_ledger import UsageLedger
from app.models.asset import Asset
from app.services.budget import BudgetService
from app.services.export_preset import ExportPresetService


from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.attributes import flag_modified

ALLOWED_WP017_RENDER_PROFILES = ("MASTER", "MASTER_HD")


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
        # Validate render_profile (WP017 supports MASTER render only)
        if render_profile.upper() not in ALLOWED_WP017_RENDER_PROFILES:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported render profile '{render_profile}'. WP017 supports MASTER render only. Aspect/platform variants are deferred to WP018.",
            )

        # 1. Lock Project Row under DB authority
        query = db.query(Project).filter(Project.id == project_id).with_for_update()
        project = query.first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        project.updated_at = datetime.now(timezone.utc)
        flag_modified(project, "updated_at")
        db.flush()

        # 2. Resolve Timeline for project
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

        # 3. Approval Gate Verification
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

        base_idempotency_key = f"{project_id}:{timeline.id}:{timeline.version}:{render_profile}"
        target_key = custom_idempotency_key or base_idempotency_key

        # 4. DB Authority Idempotency Check (under project lock) for MASTER variant
        blocking_job = (
            db.query(RenderJob)
            .filter(
                RenderJob.project_id == project_id,
                RenderJob.timeline_id == timeline.id,
                RenderJob.render_variant_key == "MASTER",
                RenderJob.status.in_([
                    RenderJobStatus.QUEUED.value,
                    RenderJobStatus.CLAIMED.value,
                    RenderJobStatus.RUNNING.value,
                    RenderJobStatus.RECONCILIATION_REQUIRED.value,
                ]),
            )
            .first()
        )
        if blocking_job:
            if blocking_job.status == RenderJobStatus.RECONCILIATION_REQUIRED.value:
                raise HTTPException(
                    status_code=400,
                    detail=f"Cannot submit new render job: prior render job {blocking_job.id} is in RECONCILIATION_REQUIRED state. Explicit reconciliation is required before submitting new renders for timeline v{timeline.version}.",
                )
            return blocking_job

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

        # 5. Check project budget before authorizing NEW render job reservation
        BudgetService.check_budget_before_dispatch(
            db=db,
            project_id=project_id,
            estimated_cost=estimated_cost_usd,
            lock_row=False,
        )

        # 6. Create RenderJob Entity with IntegrityError fallback for DB authority race conditions
        now = utc_now()
        render_job = RenderJob(
            project_id=project_id,
            timeline_id=timeline.id,
            timeline_version=timeline.version,
            approval_id=approval.id,
            render_profile=render_profile,
            render_variant_key="MASTER",
            status=RenderJobStatus.QUEUED.value,
            idempotency_key=target_key,
            progress=0.0,
            retry_count=0,
            max_retries=3,
            estimated_cost_usd=estimated_cost_usd,
            render_metadata={
                "timeline_version": timeline.version,
                "render_profile": render_profile,
                "render_variant_key": "MASTER",
                "approval_id": str(approval.id),
                "qc_run_id": str(approval.qc_run_id),
            },
            created_at=now,
            updated_at=now,
        )

        try:
            db.add(render_job)
            db.flush()
        except Exception:
            db.rollback()
            blocking_job = (
                db.query(RenderJob)
                .filter(
                    RenderJob.project_id == project_id,
                    RenderJob.timeline_id == timeline.id,
                    RenderJob.render_variant_key == "MASTER",
                    RenderJob.status.in_([
                        RenderJobStatus.QUEUED.value,
                        RenderJobStatus.CLAIMED.value,
                        RenderJobStatus.RUNNING.value,
                        RenderJobStatus.RECONCILIATION_REQUIRED.value,
                    ]),
                )
                .first()
            )
            if blocking_job:
                if blocking_job.status == RenderJobStatus.RECONCILIATION_REQUIRED.value:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Cannot submit new render job: prior render job {blocking_job.id} is in RECONCILIATION_REQUIRED state. Explicit reconciliation is required before submitting new renders for timeline v{timeline.version}.",
                    )
                return blocking_job
            raise

        # 7. Create UsageLedger Pre-Compute Cost Reservation (ESTIMATED) and bind current_usage_ledger_id
        ledger_entry = UsageLedger(
            project_id=project_id,
            render_job_id=render_job.id,
            provider="ORBIS_RENDER",
            operation="RENDER_VIDEO",
            estimated_cost=estimated_cost_usd,
            actual_cost=None,
            currency="USD",
            cost_status="ESTIMATED",
            idempotency_key=f"render_reserve_{render_job.id}_attempt_1",
            description=f"Pre-render compute cost reservation (attempt 1) for timeline v{timeline.version}",
            created_at=now,
            updated_at=now,
        )
        db.add(ledger_entry)
        db.flush()
        render_job.current_usage_ledger_id = ledger_entry.id
        db.commit()
        db.refresh(render_job)
        return render_job

    @classmethod
    def submit_export_batch(
        cls,
        db: Session,
        project_id: uuid.UUID,
        preset_ids: List[str],
        timeline_id: Optional[uuid.UUID] = None,
    ) -> RenderBatch:
        if not preset_ids:
            raise HTTPException(status_code=400, detail="At least one export preset_id is required")

        # Resolve requested presets and compute total estimated cost
        requested_presets = []
        total_estimated_cost = 0.0
        for pid in preset_ids:
            preset = ExportPresetService.get_preset(pid)
            requested_presets.append(preset)
            total_estimated_cost += float(preset.get("estimated_cost_usd", 0.50))

        # 1. Lock Project Row under DB authority
        query = db.query(Project).filter(Project.id == project_id).with_for_update()
        project = query.first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        project.updated_at = datetime.now(timezone.utc)
        flag_modified(project, "updated_at")
        db.flush()

        # 2. Resolve Timeline
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

        # 3. Approval Gate Verification
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
                detail=f"Timeline version {timeline.version} is not approved. Final approval is required before exporting.",
            )

        # 4. Check project budget for total batch estimated cost upfront
        BudgetService.check_budget_before_dispatch(
            db=db,
            project_id=project_id,
            estimated_cost=total_estimated_cost,
            lock_row=False,
        )

        now = utc_now()
        batch = RenderBatch(
            project_id=project_id,
            timeline_id=timeline.id,
            timeline_version=timeline.version,
            status="PROCESSING",
            total_variants=len(requested_presets),
            completed_variants=0,
            failed_variants=0,
            estimated_total_cost_usd=total_estimated_cost,
            created_at=now,
            updated_at=now,
        )

        try:
            db.add(batch)
            db.flush()

            child_jobs = []
            for preset in requested_presets:
                pid = preset["preset_id"]
                variant_key = ExportPresetService.compute_render_variant_key(pid, preset)
                base_idempotency_key = f"{project_id}:{timeline.id}:{timeline.version}:{variant_key}"

                # Check active blocking job for THIS SPECIFIC variant key
                blocking_job = (
                    db.query(RenderJob)
                    .filter(
                        RenderJob.project_id == project_id,
                        RenderJob.timeline_id == timeline.id,
                        RenderJob.render_variant_key == variant_key,
                        RenderJob.status.in_([
                            RenderJobStatus.QUEUED.value,
                            RenderJobStatus.CLAIMED.value,
                            RenderJobStatus.RUNNING.value,
                            RenderJobStatus.RECONCILIATION_REQUIRED.value,
                        ]),
                    )
                    .first()
                )
                if blocking_job:
                    if blocking_job.status == RenderJobStatus.RECONCILIATION_REQUIRED.value:
                        raise HTTPException(
                            status_code=400,
                            detail=f"Cannot submit export batch: variant '{pid}' is in RECONCILIATION_REQUIRED state. Explicit reconciliation is required.",
                        )
                    child_jobs.append(blocking_job)
                    continue

                # Check completed job for timestamping
                completed_job = (
                    db.query(RenderJob)
                    .filter(
                        RenderJob.project_id == project_id,
                        RenderJob.idempotency_key == base_idempotency_key,
                        RenderJob.status == RenderJobStatus.COMPLETED.value,
                    )
                    .first()
                )
                target_key = f"{base_idempotency_key}:{int(time.time())}" if completed_job else base_idempotency_key

                job_est_cost = float(preset.get("estimated_cost_usd", 0.50))
                render_job = RenderJob(
                    project_id=project_id,
                    timeline_id=timeline.id,
                    timeline_version=timeline.version,
                    approval_id=approval.id,
                    render_profile=pid,
                    render_variant_key=variant_key,
                    batch_id=batch.id,
                    status=RenderJobStatus.QUEUED.value,
                    idempotency_key=target_key,
                    progress=0.0,
                    retry_count=0,
                    max_retries=3,
                    estimated_cost_usd=job_est_cost,
                    render_metadata={
                        "preset_id": pid,
                        "render_variant_key": variant_key,
                        "timeline_version": timeline.version,
                        "approval_id": str(approval.id),
                        "qc_run_id": str(approval.qc_run_id),
                        "preset_snapshot": preset,
                    },
                    created_at=now,
                    updated_at=now,
                )
                db.add(render_job)
                db.flush()

                ledger_entry = UsageLedger(
                    project_id=project_id,
                    render_job_id=render_job.id,
                    provider="ORBIS_RENDER",
                    operation="EXPORT_VIDEO",
                    estimated_cost=job_est_cost,
                    actual_cost=None,
                    currency="USD",
                    cost_status="ESTIMATED",
                    idempotency_key=f"export_reserve_{render_job.id}_attempt_1",
                    description=f"Export compute reservation (attempt 1) for preset '{pid}' timeline v{timeline.version}",
                    created_at=now,
                    updated_at=now,
                )
                db.add(ledger_entry)
                db.flush()
                render_job.current_usage_ledger_id = ledger_entry.id
                child_jobs.append(render_job)

            db.commit()
            db.refresh(batch)
            return batch
        except Exception:
            db.rollback()
            raise

    @classmethod
    def get_render_batch(
        cls,
        db: Session,
        project_id: uuid.UUID,
        batch_id: uuid.UUID,
    ) -> Optional[RenderBatch]:
        return (
            db.query(RenderBatch)
            .filter(
                RenderBatch.project_id == project_id,
                RenderBatch.id == batch_id,
            )
            .first()
        )

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

        # Handle expired lease transition if candidate was previously CLAIMED/RUNNING under the exact same row lock
        if job.status in (RenderJobStatus.CLAIMED.value, RenderJobStatus.RUNNING.value):
            if not job.current_usage_ledger_id:
                job.status = RenderJobStatus.RECONCILIATION_REQUIRED.value
                job.error_message = "Expired lease missing current_usage_ledger_id reference"
                db.commit()
                db.refresh(job)
                return None

            target_ledger = db.get(UsageLedger, job.current_usage_ledger_id)
            if not target_ledger:
                job.status = RenderJobStatus.RECONCILIATION_REQUIRED.value
                job.error_message = f"Expired lease current_usage_ledger_id {job.current_usage_ledger_id} not found"
                db.commit()
                db.refresh(job)
                return None

            if target_ledger.cost_status == "ESTIMATED":
                target_ledger.cost_status = "ESTIMATED"
                target_ledger.updated_at = now

            job.retry_count += 1
            if job.retry_count >= job.max_retries:
                job.status = RenderJobStatus.FAILED.value
                job.claimed_by = None
                job.claim_token = None
                job.claim_expires_at = None
                job.error_message = f"Terminal failure after lease expiration ({job.retry_count}/{job.max_retries} attempts)"
                db.commit()
                db.refresh(job)
                return None

            # Verify project budget before creating NEW attempt reservation
            try:
                BudgetService.check_budget_before_dispatch(
                    db=db,
                    project_id=job.project_id,
                    estimated_cost=job.estimated_cost_usd,
                    lock_row=False,
                )
            except HTTPException as budget_err:
                job.status = RenderJobStatus.FAILED.value
                job.claimed_by = None
                job.claim_token = None
                job.claim_expires_at = None
                job.error_message = f"Automatic retry blocked: {budget_err.detail}"
                db.commit()
                db.refresh(job)
                return None

            attempt_number = db.query(UsageLedger).filter(UsageLedger.render_job_id == job.id).count() + 1
            operation_key = f"RENDER_RETRY_{job.id}_attempt_{attempt_number}"
            idempotency_key = f"render_reserve_{job.id}_attempt_{attempt_number}"

            new_ledger = UsageLedger(
                project_id=job.project_id,
                render_job_id=job.id,
                provider="ORBIS_RENDER",
                operation=operation_key,
                estimated_cost=job.estimated_cost_usd,
                actual_cost=None,
                currency="USD",
                cost_status="ESTIMATED",
                idempotency_key=idempotency_key,
                description=f"Pre-render compute cost reservation (attempt {attempt_number}) for timeline v{job.timeline_version}",
                created_at=now,
                updated_at=now,
            )
            try:
                db.add(new_ledger)
                db.flush()
                job.current_usage_ledger_id = new_ledger.id
            except IntegrityError:
                db.rollback()
                return None

        # Lock candidate and update claim token
        token = secrets.token_hex(16)
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

        # Require explicit current_usage_ledger_id binding without fallback guessing
        if not job.current_usage_ledger_id:
            job.status = RenderJobStatus.RECONCILIATION_REQUIRED.value
            job.error_message = "Missing current_usage_ledger_id reference: cost reconciliation required"
            db.commit()
            db.refresh(job)
            raise HTTPException(status_code=500, detail="Missing current_usage_ledger_id reference: cost reconciliation required")

        target_ledger = db.get(UsageLedger, job.current_usage_ledger_id)
        if not target_ledger or target_ledger.cost_status != "ESTIMATED":
            job.status = RenderJobStatus.RECONCILIATION_REQUIRED.value
            job.error_message = f"Invalid or non-ESTIMATED current usage ledger {job.current_usage_ledger_id}"
            db.commit()
            db.refresh(job)
            raise HTTPException(status_code=500, detail="Invalid current_usage_ledger_id reference: cost reconciliation required")

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

        target_ledger.cost_status = "CONFIRMED"
        target_ledger.actual_cost = actual_cost_usd
        target_ledger.updated_at = now

        db.commit()
        db.refresh(job)
        if job.batch_id:
            cls.settle_render_batch_progress(db, job.batch_id)
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
            db.commit()
            db.refresh(job)
            return job

        # Require explicit current_usage_ledger_id binding without fallback guessing
        if not job.current_usage_ledger_id:
            job.status = RenderJobStatus.RECONCILIATION_REQUIRED.value
            job.error_message = f"Missing current_usage_ledger_id reference: {error_message}"
            db.commit()
            db.refresh(job)
            return job

        target_ledger = db.get(UsageLedger, job.current_usage_ledger_id)
        if not target_ledger:
            job.status = RenderJobStatus.RECONCILIATION_REQUIRED.value
            job.error_message = f"Invalid current_usage_ledger_id reference {job.current_usage_ledger_id}: {error_message}"
            db.commit()
            db.refresh(job)
            return job

        if target_ledger.cost_status == "ESTIMATED":
            if not was_running_or_claimed:
                # Proven PRE-EXECUTION failure -> release cost to 0
                target_ledger.cost_status = "ADJUSTED"
                target_ledger.actual_cost = 0.0
            else:
                # Execution was in progress -> preserve ESTIMATED cost reservation
                target_ledger.cost_status = "ESTIMATED"
            target_ledger.updated_at = now

        job.retry_count += 1
        if job.retry_count < job.max_retries:
            # Verify project budget before creating NEW attempt reservation
            try:
                BudgetService.check_budget_before_dispatch(
                    db=db,
                    project_id=job.project_id,
                    estimated_cost=job.estimated_cost_usd,
                    lock_row=True,
                )
                attempt_number = db.query(UsageLedger).filter(UsageLedger.render_job_id == job.id).count() + 1
                operation_key = f"RENDER_RETRY_{job.id}_attempt_{attempt_number}"
                idempotency_key = f"render_reserve_{job.id}_attempt_{attempt_number}"

                new_ledger = UsageLedger(
                    project_id=job.project_id,
                    render_job_id=job.id,
                    provider="ORBIS_RENDER",
                    operation=operation_key,
                    estimated_cost=job.estimated_cost_usd,
                    actual_cost=None,
                    currency="USD",
                    cost_status="ESTIMATED",
                    idempotency_key=idempotency_key,
                    description=f"Pre-render compute cost reservation (attempt {attempt_number}) for timeline v{job.timeline_version}",
                    created_at=now,
                    updated_at=now,
                )
                db.add(new_ledger)
                db.flush()
                job.current_usage_ledger_id = new_ledger.id
                job.status = RenderJobStatus.QUEUED.value
                job.claimed_by = None
                job.claim_token = None
                job.claim_expires_at = None
                job.error_message = f"Retryable error (attempt {job.retry_count}/{job.max_retries}): {error_message}"
            except HTTPException as budget_err:
                # Automatic retry blocked by budget limit -> mark FAILED
                job.status = RenderJobStatus.FAILED.value
                job.claimed_by = None
                job.claim_token = None
                job.claim_expires_at = None
                job.error_message = f"Automatic retry blocked: {budget_err.detail}"
        else:
            # Terminal failure reached
            job.status = RenderJobStatus.FAILED.value
            job.claimed_by = None
            job.claim_token = None
            job.claim_expires_at = None
            job.error_message = f"Terminal failure after {job.retry_count}/{job.max_retries} attempts: {error_message}"

        db.commit()
        db.refresh(job)
        if job.batch_id:
            cls.settle_render_batch_progress(db, job.batch_id)
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
        was_running = job.status in (RenderJobStatus.CLAIMED.value, RenderJobStatus.RUNNING.value)
        job.status = RenderJobStatus.CANCELLED.value
        job.claimed_by = None
        job.claim_token = None
        job.claim_expires_at = None
        job.error_message = "Cancelled by user"
        job.updated_at = now

        if not job.current_usage_ledger_id:
            job.status = RenderJobStatus.RECONCILIATION_REQUIRED.value
            job.error_message = "Cancelled job missing current_usage_ledger_id reference: reconciliation required"
            db.commit()
            db.refresh(job)
            raise HTTPException(status_code=500, detail="Missing current_usage_ledger_id reference: reconciliation required")

        target_ledger = db.get(UsageLedger, job.current_usage_ledger_id)
        if not target_ledger:
            job.status = RenderJobStatus.RECONCILIATION_REQUIRED.value
            job.error_message = f"Cancelled job current_usage_ledger_id {job.current_usage_ledger_id} not found"
            db.commit()
            db.refresh(job)
            raise HTTPException(status_code=500, detail="Invalid current_usage_ledger_id reference")

        if target_ledger.cost_status == "ESTIMATED":
            if not was_running:
                # Pre-execution cancellation -> release cost to 0
                target_ledger.cost_status = "ADJUSTED"
                target_ledger.actual_cost = 0.0
            else:
                # Running cancellation -> preserve ESTIMATED cost reservation
                target_ledger.cost_status = "ESTIMATED"
            target_ledger.updated_at = now

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
        # Concurrency-safe project budget check under row lock before authorizing new retry reservation
        BudgetService.check_budget_before_dispatch(
            db=db,
            project_id=project_id,
            estimated_cost=None,
            lock_row=True,
        )

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

        db.refresh(job)
        # Idempotent replay check: if job is already active for retry, return without duplicate reservation
        if job.status in (
            RenderJobStatus.QUEUED.value,
            RenderJobStatus.CLAIMED.value,
            RenderJobStatus.RUNNING.value,
        ):
            return job

        if job.status not in (RenderJobStatus.FAILED.value, RenderJobStatus.CANCELLED.value):
            raise HTTPException(
                status_code=400,
                detail=f"Cannot retry render job in status {job.status}. Explicit owner reconciliation is required first if in RECONCILIATION_REQUIRED state.",
            )

        recon_job = (
            db.query(RenderJob)
            .filter(
                RenderJob.project_id == project_id,
                RenderJob.timeline_id == job.timeline_id,
                RenderJob.status == RenderJobStatus.RECONCILIATION_REQUIRED.value,
            )
            .first()
        )
        if recon_job:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot retry render job: timeline has prior job {recon_job.id} in RECONCILIATION_REQUIRED state.",
            )

        # Verify estimated cost against budget limit under project lock
        BudgetService.check_budget_before_dispatch(
            db=db,
            project_id=project_id,
            estimated_cost=job.estimated_cost_usd,
            lock_row=False,
        )

        attempt_number = db.query(UsageLedger).filter(UsageLedger.render_job_id == job.id).count() + 1
        operation_key = f"RENDER_RETRY_{job.id}_attempt_{attempt_number}"
        idempotency_key = f"render_reserve_{job.id}_attempt_{attempt_number}"

        now = utc_now()
        # Create exactly ONE new attempt reservation in UsageLedger and bind current_usage_ledger_id atomically
        new_ledger_entry = UsageLedger(
            project_id=project_id,
            render_job_id=job.id,
            provider="ORBIS_RENDER",
            operation=operation_key,
            estimated_cost=job.estimated_cost_usd,
            actual_cost=None,
            currency="USD",
            cost_status="ESTIMATED",
            idempotency_key=idempotency_key,
            description=f"Pre-render compute cost reservation (attempt {attempt_number}) for timeline v{job.timeline_version}",
            created_at=now,
            updated_at=now,
        )
        from sqlalchemy.exc import IntegrityError
        try:
            db.add(new_ledger_entry)
            db.flush()
            job.current_usage_ledger_id = new_ledger_entry.id
            job.status = RenderJobStatus.QUEUED.value
            job.retry_count = 0
            job.claimed_by = None
            job.claim_token = None
            job.claim_expires_at = None
            job.error_message = None
            job.updated_at = now
            db.commit()
        except IntegrityError as e:
            db.rollback()
            job = db.get(RenderJob, render_job_id)
            if job:
                existing_ledger = (
                    db.query(UsageLedger)
                    .filter(
                        UsageLedger.render_job_id == render_job_id,
                        UsageLedger.idempotency_key == idempotency_key,
                    )
                    .first()
                )
                if existing_ledger:
                    job.status = RenderJobStatus.QUEUED.value
                    job.current_usage_ledger_id = existing_ledger.id
                    db.commit()
                    db.refresh(job)
                    return job
            raise
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
        name: Optional[str] = None,
        asset_type: str = "VIDEO",
        original_filename: Optional[str] = None,
    ) -> Asset:
        filename = original_filename or os.path.basename(storage_key)
        asset_name = name or f"Render Master Output ({filename})"
        asset = Asset(
            project_id=project_id,
            name=asset_name,
            original_filename=filename,
            asset_type=asset_type,
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

    @classmethod
    def submit_export_batch(
        cls,
        db: Session,
        project_id: uuid.UUID,
        preset_ids: List[str],
        timeline_id: Optional[uuid.UUID] = None,
    ) -> RenderBatch:
        if not preset_ids:
            raise HTTPException(status_code=400, detail="Must specify at least one export preset ID")

        # Single atomic DB transaction / savepoint for batch authorization
        sp = db.begin_nested()
        try:
            # 1. Acquire DB lock on Project row
            project = db.query(Project).filter(Project.id == project_id).with_for_update().first()
            if not project:
                raise HTTPException(status_code=404, detail="Project not found")

            # 2. Get active/latest timeline & verify approval gate
            if timeline_id:
                timeline = db.query(AssemblyTimeline).filter(
                    AssemblyTimeline.id == timeline_id,
                    AssemblyTimeline.project_id == project_id,
                ).first()
            else:
                timeline = db.query(AssemblyTimeline).filter(
                    AssemblyTimeline.project_id == project_id,
                ).order_by(AssemblyTimeline.version.desc()).first()

            if not timeline:
                raise HTTPException(status_code=404, detail="No timeline found for project")

            approval = db.query(ApprovalRecord).filter(
                ApprovalRecord.project_id == project_id,
                ApprovalRecord.timeline_id == timeline.id,
                ApprovalRecord.timeline_version == timeline.version,
                ApprovalRecord.status == "APPROVED",
            ).first()

            if not approval:
                raise HTTPException(
                    status_code=400,
                    detail=f"Cannot render export presets for timeline v{timeline.version} without an APPROVED production approval gate.",
                )

            # 3. Resolve preset specifications and compute total cost
            presets = [ExportPresetService.get_preset(pid) for pid in preset_ids]
            total_estimated_cost = sum(float(p["estimated_cost_usd"]) for p in presets)

            # 4. Concurrency-safe budget verification for total batch cost
            BudgetService.check_budget_before_dispatch(
                db=db,
                project_id=project_id,
                estimated_cost=total_estimated_cost,
                lock_row=False,
            )

            # 5. Create RenderBatch parent record
            now = utc_now()
            batch = RenderBatch(
                project_id=project_id,
                timeline_id=timeline.id,
                timeline_version=timeline.version,
                status="PROCESSING",
                total_variants=len(presets),
                completed_variants=0,
                failed_variants=0,
                estimated_total_cost_usd=total_estimated_cost,
                created_at=now,
                updated_at=now,
            )
            db.add(batch)
            db.flush()

            # 6. Create child RenderJobs and UsageLedger reservations
            child_jobs = []
            for preset in presets:
                preset_id = preset["preset_id"]
                variant_key = ExportPresetService.compute_render_variant_key(preset_id, preset)
                idempotency_key = f"export_batch_{batch.id}_{preset_id}"

                # Check if identical active variant job already exists
                active_job = db.query(RenderJob).filter(
                    RenderJob.project_id == project_id,
                    RenderJob.timeline_id == timeline.id,
                    RenderJob.render_variant_key == variant_key,
                    RenderJob.status.in_([
                        RenderJobStatus.QUEUED.value,
                        RenderJobStatus.CLAIMED.value,
                        RenderJobStatus.RUNNING.value,
                        RenderJobStatus.RECONCILIATION_REQUIRED.value,
                    ]),
                ).first()

                if active_job:
                    if active_job.status == RenderJobStatus.RECONCILIATION_REQUIRED.value:
                        raise HTTPException(
                            status_code=400,
                            detail=f"Active render variant '{variant_key}' is in RECONCILIATION_REQUIRED state. Reconciliation required before re-submitting.",
                        )
                    child_jobs.append(active_job)
                    continue

                job = RenderJob(
                    project_id=project_id,
                    timeline_id=timeline.id,
                    timeline_version=timeline.version,
                    approval_id=approval.id,
                    render_profile=preset_id,
                    render_variant_key=variant_key,
                    batch_id=batch.id,
                    status=RenderJobStatus.QUEUED.value,
                    idempotency_key=idempotency_key,
                    estimated_cost_usd=float(preset["estimated_cost_usd"]),
                    render_metadata={
                        "preset_id": preset_id,
                        "render_variant_key": variant_key,
                        "aspect_ratio": preset["aspect_ratio"],
                        "resolution": f"{preset['width']}x{preset['height']}",
                        "bitrate_kbps": preset["video_bitrate_kbps"],
                        "timeline_version": timeline.version,
                        "preset_snapshot": preset,
                    },
                    created_at=now,
                    updated_at=now,
                )
                db.add(job)
                db.flush()

                # Pre-execution UsageLedger reservation
                attempt_key = f"render_reserve_{job.id}_attempt_1"
                ledger = UsageLedger(
                    project_id=project_id,
                    render_job_id=job.id,
                    provider="ORBIS_RENDER",
                    operation=f"EXPORT_PRESET_{preset_id}_attempt_1",
                    estimated_cost=job.estimated_cost_usd,
                    actual_cost=None,
                    currency="USD",
                    cost_status="ESTIMATED",
                    idempotency_key=attempt_key,
                    description=f"Pre-render compute cost reservation (attempt 1) for export preset {preset_id} (timeline v{timeline.version})",
                    created_at=now,
                    updated_at=now,
                )
                db.add(ledger)
                db.flush()

                job.current_usage_ledger_id = ledger.id
                child_jobs.append(job)

            sp.commit()
            db.commit()
            db.refresh(batch)
            return batch

        except Exception:
            sp.rollback()
            raise

    @classmethod
    def get_render_batch(cls, db: Session, project_id: uuid.UUID, batch_id: uuid.UUID) -> RenderBatch:
        batch = db.query(RenderBatch).filter(
            RenderBatch.id == batch_id,
            RenderBatch.project_id == project_id,
        ).first()
        if not batch:
            raise HTTPException(status_code=404, detail="Render batch not found")
        return batch

    @classmethod
    def settle_render_batch_progress(cls, db: Session, batch_id: uuid.UUID) -> Optional[RenderBatch]:
        batch = db.get(RenderBatch, batch_id)
        if not batch:
            return None

        jobs = db.query(RenderJob).filter(RenderJob.batch_id == batch_id).all()
        completed = sum(1 for j in jobs if j.status == RenderJobStatus.COMPLETED.value)
        failed = sum(1 for j in jobs if j.status in (
            RenderJobStatus.FAILED.value,
            RenderJobStatus.CANCELLED.value,
            RenderJobStatus.RECONCILIATION_REQUIRED.value,
        ))

        batch.completed_variants = completed
        batch.failed_variants = failed

        if completed + failed >= batch.total_variants:
            if failed == 0:
                batch.status = "COMPLETED"
            elif completed == 0:
                batch.status = "FAILED"
            else:
                batch.status = "COMPLETED_WITH_ERRORS"
        else:
            batch.status = "PROCESSING"

        batch.updated_at = utc_now()
        db.commit()
        db.refresh(batch)
        return batch
