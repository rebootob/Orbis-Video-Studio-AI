import uuid
import time
import pytest
from typing import Tuple
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.project import Project
from app.models.assembly import AssemblyTimeline
from app.models.qc import QCRun, ApprovalRecord
from app.models.render_job import RenderJob, RenderJobStatus
from app.models.usage_ledger import UsageLedger
from app.models.asset import Asset
from app.services.render_job import RenderJobService
from app.services.render import FFmpegRenderExecutor
from app.services.render_worker import CloudRenderWorker


def create_approved_project_context(db: Session) -> Tuple[Project, AssemblyTimeline, ApprovalRecord]:
    project = Project(
        id=uuid.uuid4(),
        title="Render Test Movie",
        video_mode="STORY",
        status="FINAL_REVIEW",
        budget_limit=10.0,
        budget_currency="USD",
    )
    db.add(project)
    db.flush()

    timeline = AssemblyTimeline(
        id=uuid.uuid4(),
        project_id=project.id,
        version=1,
        status="APPROVED",
        is_active=True,
    )
    db.add(timeline)
    db.flush()

    qc_run = QCRun(
        id=uuid.uuid4(),
        project_id=project.id,
        timeline_id=timeline.id,
        timeline_version=1,
        status="PASSED",
        blocker_count=0,
        warning_count=0,
        actor="system",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(qc_run)
    db.flush()

    approval = ApprovalRecord(
        id=uuid.uuid4(),
        project_id=project.id,
        timeline_id=timeline.id,
        timeline_version=1,
        qc_run_id=qc_run.id,
        status="APPROVED",
        actor="user",
        approved_at=datetime.now(timezone.utc),
    )
    db.add(approval)
    db.commit()
    db.refresh(project)
    db.refresh(timeline)
    db.refresh(approval)
    return project, timeline, approval


def test_unapproved_timeline_fails(client: TestClient, db_session: Session):
    project = Project(id=uuid.uuid4(), title="Unapproved Project", video_mode="STORY")
    db_session.add(project)
    timeline = AssemblyTimeline(id=uuid.uuid4(), project_id=project.id, version=1, status="DRAFT")
    db_session.add(timeline)
    db_session.commit()

    res = client.post(f"/api/v1/projects/{project.id}/renders/submit")
    assert res.status_code == 400
    assert "not approved" in res.json()["detail"]


def test_approved_timeline_submits_queued_job(client: TestClient, db_session: Session):
    project, timeline, approval = create_approved_project_context(db_session)

    res = client.post(f"/api/v1/projects/{project.id}/renders/submit")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "QUEUED"
    assert data["project_id"] == str(project.id)
    assert data["timeline_id"] == str(timeline.id)
    assert data["timeline_version"] == 1
    assert data["approval_id"] == str(approval.id)
    assert data["estimated_cost_usd"] == 0.50


def test_exact_revision_binding(db_session: Session):
    project, timeline, approval = create_approved_project_context(db_session)
    job = RenderJobService.submit_render_job(db_session, project.id)
    assert job.timeline_id == timeline.id
    assert job.timeline_version == 1
    assert job.approval_id == approval.id


def test_idempotency_replay_active_job(client: TestClient, db_session: Session):
    project, timeline, _ = create_approved_project_context(db_session)

    res1 = client.post(f"/api/v1/projects/{project.id}/renders/submit")
    assert res1.status_code == 200
    job1_id = res1.json()["id"]

    res2 = client.post(f"/api/v1/projects/{project.id}/renders/submit")
    assert res2.status_code == 200
    job2_id = res2.json()["id"]

    assert job1_id == job2_id


def test_worker_claim_queued_job(db_session: Session):
    project, _, _ = create_approved_project_context(db_session)
    job = RenderJobService.submit_render_job(db_session, project.id)

    claimed_job = RenderJobService.claim_next_render_job(db_session, worker_id="test-worker-1")
    assert claimed_job is not None
    assert claimed_job.id == job.id
    assert claimed_job.status == "CLAIMED"
    assert claimed_job.claimed_by == "test-worker-1"
    assert claimed_job.claim_token is not None


def test_pre_compute_cost_reservation(db_session: Session):
    project, _, _ = create_approved_project_context(db_session)
    job = RenderJobService.submit_render_job(db_session, project.id, estimated_cost_usd=0.50)

    ledger_entry = db_session.query(UsageLedger).filter(UsageLedger.render_job_id == job.id).first()
    assert ledger_entry is not None
    assert ledger_entry.cost_status == "ESTIMATED"
    assert ledger_entry.estimated_cost == 0.50


def test_cost_reconciliation_on_completion(db_session: Session):
    project, _, _ = create_approved_project_context(db_session)
    job = RenderJobService.submit_render_job(db_session, project.id)
    claimed = RenderJobService.claim_next_render_job(db_session, worker_id="worker-1")

    asset = RenderJobService.create_render_output_asset(
        db_session, project.id, storage_key="test.mp4", duration_seconds=10.0, file_size_bytes=1024
    )
    db_session.commit()

    completed = RenderJobService.complete_render_job(
        db_session, claimed.id, claimed.claim_token, asset.id, actual_cost_usd=0.35
    )
    assert completed.status == "COMPLETED"
    assert completed.actual_cost_usd == 0.35

    ledger_entry = db_session.query(UsageLedger).filter(UsageLedger.render_job_id == job.id).first()
    assert ledger_entry.cost_status == "CONFIRMED"
    assert ledger_entry.actual_cost == 0.35


def test_cost_release_on_terminal_failure(db_session: Session):
    project, _, _ = create_approved_project_context(db_session)
    job = RenderJobService.submit_render_job(db_session, project.id)
    job.retry_count = 3  # Max retries reached
    db_session.commit()

    failed = RenderJobService.fail_render_job(db_session, job.id, job.claim_token, "Terminal error", ambiguous=False)
    assert failed.status == "FAILED"

    ledger_entry = db_session.query(UsageLedger).filter(UsageLedger.render_job_id == job.id).first()
    assert ledger_entry.cost_status == "ADJUSTED"
    assert ledger_entry.actual_cost == 0.0


def test_ambiguous_failure_preserves_estimated_cost(db_session: Session):
    project, _, _ = create_approved_project_context(db_session)
    job = RenderJobService.submit_render_job(db_session, project.id)

    failed = RenderJobService.fail_render_job(db_session, job.id, job.claim_token, "Upload timeout", ambiguous=True)
    assert failed.status == "RECONCILIATION_REQUIRED"

    ledger_entry = db_session.query(UsageLedger).filter(UsageLedger.render_job_id == job.id).first()
    assert ledger_entry.cost_status == "ESTIMATED"


def test_concurrent_budget_reservation_lock(db_session: Session):
    project, _, _ = create_approved_project_context(db_session)
    project.budget_limit = 0.80
    db_session.commit()

    # Job 1 (0.50) succeeds
    job1 = RenderJobService.submit_render_job(db_session, project.id, estimated_cost_usd=0.50)
    assert job1 is not None

    # Complete Job 1 so it is no longer in active (QUEUED/CLAIMED/RUNNING) status, but cost remains committed (0.50)
    claimed1 = RenderJobService.claim_next_render_job(db_session, worker_id="w1")
    asset1 = RenderJobService.create_render_output_asset(
        db_session, project.id, storage_key="job1.mp4", duration_seconds=10.0, file_size_bytes=1024
    )
    RenderJobService.complete_render_job(db_session, claimed1.id, claimed1.claim_token, asset1.id, actual_cost_usd=0.50)

    # Job 2 (0.50) against remaining 0.30 budget breaches limit and fails closed
    with pytest.raises(Exception) as exc_info:
        RenderJobService.submit_render_job(
            db_session, project.id, custom_idempotency_key="key2", estimated_cost_usd=0.50
        )
    assert "budget" in str(exc_info.value).lower()


def test_full_history_retention_re_render(db_session: Session):
    project, timeline, approval = create_approved_project_context(db_session)
    job1 = RenderJobService.submit_render_job(db_session, project.id, custom_idempotency_key="render_v1_key")
    claimed1 = RenderJobService.claim_next_render_job(db_session, worker_id="w1")

    asset1 = RenderJobService.create_render_output_asset(
        db_session, project.id, storage_key="render1.mp4", duration_seconds=10.0, file_size_bytes=1024
    )
    db_session.commit()
    RenderJobService.complete_render_job(db_session, claimed1.id, claimed1.claim_token, asset1.id, 0.10)

    # Re-render with new key
    job2 = RenderJobService.submit_render_job(db_session, project.id, custom_idempotency_key="render_v1_rerender_key")
    assert job2.id != job1.id


def test_hard_budget_lock(client: TestClient, db_session: Session):
    project, _, _ = create_approved_project_context(db_session)
    project.budget_limit = 0.10
    db_session.commit()

    res = client.post(f"/api/v1/projects/{project.id}/renders/submit")
    assert res.status_code == 400
    assert "budget" in res.json()["detail"].lower()


def test_cross_project_isolation(client: TestClient, db_session: Session):
    project1, _, _ = create_approved_project_context(db_session)
    project2 = Project(id=uuid.uuid4(), title="Project 2", video_mode="STORY")
    db_session.add(project2)
    db_session.commit()

    job1 = RenderJobService.submit_render_job(db_session, project1.id)

    # Attempt cross-project access via Project 2 URL
    res = client.get(f"/api/v1/projects/{project2.id}/renders/{job1.id}")
    assert res.status_code == 404


def test_lease_extension(db_session: Session):
    project, _, _ = create_approved_project_context(db_session)
    job = RenderJobService.submit_render_job(db_session, project.id)
    claimed = RenderJobService.claim_next_render_job(db_session, worker_id="w1")

    ok = RenderJobService.extend_lease(db_session, claimed.id, claimed.claim_token, extend_seconds=600)
    assert ok is True
    db_session.refresh(claimed)
    assert claimed.status == "RUNNING"


def test_worker_execution_flow(db_session: Session):
    project, _, _ = create_approved_project_context(db_session)
    job = RenderJobService.submit_render_job(db_session, project.id)

    worker = CloudRenderWorker(worker_id="test-worker-node-1")
    processed = worker.process_one_job(db_session)
    assert processed is True

    db_session.refresh(job)
    assert job.status == "COMPLETED"
    assert job.output_asset_id is not None
    assert job.progress == 100.0


def test_worker_retry_mechanics(db_session: Session):
    project, _, _ = create_approved_project_context(db_session)
    job = RenderJobService.submit_render_job(db_session, project.id)
    job.retry_count = 0
    job.max_retries = 3
    db_session.commit()

    failed = RenderJobService.fail_render_job(db_session, job.id, "token", "Transient failure", ambiguous=False)
    assert failed.status == "QUEUED"
    assert failed.claimed_by is None


def test_user_cancellation(client: TestClient, db_session: Session):
    project, _, _ = create_approved_project_context(db_session)
    job = RenderJobService.submit_render_job(db_session, project.id)

    res = client.post(f"/api/v1/projects/{project.id}/renders/{job.id}/cancel")
    assert res.status_code == 200
    assert res.json()["status"] == "CANCELLED"

    ledger_entry = db_session.query(UsageLedger).filter(UsageLedger.render_job_id == job.id).first()
    assert ledger_entry.cost_status == "ADJUSTED"


def test_terminal_cancellation_rejected(client: TestClient, db_session: Session):
    project, _, _ = create_approved_project_context(db_session)
    job = RenderJobService.submit_render_job(db_session, project.id)
    job.status = "COMPLETED"
    db_session.commit()

    res = client.post(f"/api/v1/projects/{project.id}/renders/{job.id}/cancel")
    assert res.status_code == 400


def test_job_retry_endpoint(client: TestClient, db_session: Session):
    project, _, _ = create_approved_project_context(db_session)
    job = RenderJobService.submit_render_job(db_session, project.id)
    job.status = "FAILED"
    db_session.commit()

    res = client.post(f"/api/v1/projects/{project.id}/renders/{job.id}/retry")
    assert res.status_code == 200
    assert res.json()["status"] == "QUEUED"


def test_paginated_render_history_list(client: TestClient, db_session: Session):
    project, _, _ = create_approved_project_context(db_session)
    RenderJobService.submit_render_job(db_session, project.id, custom_idempotency_key="k1")
    RenderJobService.submit_render_job(db_session, project.id, custom_idempotency_key="k2")

    res = client.get(f"/api/v1/projects/{project.id}/renders?offset=0&limit=1")
    assert res.status_code == 200
    data = res.json()
    assert len(data["renders"]) == 1
    assert data["total_count"] >= 1


def test_latest_render_endpoint(client: TestClient, db_session: Session):
    project, _, _ = create_approved_project_context(db_session)
    job = RenderJobService.submit_render_job(db_session, project.id)

    res = client.get(f"/api/v1/projects/{project.id}/renders/latest")
    assert res.status_code == 200
    assert res.json()["id"] == str(job.id)


def test_render_profile_preservation(db_session: Session):
    project, _, _ = create_approved_project_context(db_session)
    job = RenderJobService.submit_render_job(db_session, project.id, render_profile="VERTICAL_4K")
    assert job.render_profile == "VERTICAL_4K"


def test_output_asset_locking(db_session: Session):
    project, _, _ = create_approved_project_context(db_session)
    asset = RenderJobService.create_render_output_asset(
        db_session, project.id, storage_key="test_master.mp4", duration_seconds=15.0, file_size_bytes=2048
    )
    assert asset.is_locked is True
    assert asset.asset_type == "VIDEO"


def test_ffmpeg_executor_abstraction():
    executor = FFmpegRenderExecutor()
    meta = executor.render_timeline(
        timeline_spec={"total_duration": 5.0},
        scratch_dir=".",
        output_file_path="./test_out.mp4",
    )
    assert meta["duration_seconds"] == 5.0
    assert meta["video_codec"] == "h264"


def test_approved_timeline_without_new_qc_replay(db_session: Session):
    project, timeline, approval = create_approved_project_context(db_session)
    # Existing ApprovalRecord is authoritative -> submit succeeds without re-evaluating QC
    job = RenderJobService.submit_render_job(db_session, project.id)
    assert job.status == "QUEUED"
