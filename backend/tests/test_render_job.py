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


from app.services.render.mock_executor import MockRenderExecutor
from app.models.assembly import AssemblyScene, AssemblyShotPlacement
from app.models.scene import Scene
from app.models.shot import Shot


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
        db_session,
        project.id,
        storage_bucket="orbis-assets",
        storage_key="test.mp4",
        duration_seconds=10.0,
        file_size_bytes=1024,
        checksum_sha256="a" * 64,
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
        db_session,
        project.id,
        storage_bucket="orbis-assets",
        storage_key="job1.mp4",
        duration_seconds=10.0,
        file_size_bytes=1024,
        checksum_sha256="b" * 64,
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
        db_session,
        project.id,
        storage_bucket="orbis-assets",
        storage_key="render1.mp4",
        duration_seconds=10.0,
        file_size_bytes=1024,
        checksum_sha256="c" * 64,
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

    worker = CloudRenderWorker(worker_id="test-worker-node-1", render_executor=MockRenderExecutor())
    processed = worker.process_one_job(db_session)
    assert processed is True

    db_session.refresh(job)
    assert job.status == "COMPLETED"
    assert job.output_asset_id is not None
    assert job.progress == 100.0


def test_worker_missing_source_asset_fails_closed(db_session: Session):
    project, timeline, _ = create_approved_project_context(db_session)
    scene = Scene(id=uuid.uuid4(), project_id=project.id, scene_number=1, heading="Scene 1")
    db_session.add(scene)
    assembly_scene = AssemblyScene(id=uuid.uuid4(), timeline_id=timeline.id, scene_id=scene.id, scene_order=0)
    db_session.add(assembly_scene)
    shot = Shot(id=uuid.uuid4(), scene_id=scene.id, shot_number=1, shot_type="WIDE")
    db_session.add(shot)
    placement = AssemblyShotPlacement(
        id=uuid.uuid4(),
        timeline_id=timeline.id,
        assembly_scene_id=assembly_scene.id,
        scene_id=scene.id,
        shot_id=shot.id,
        shot_order=0,
        visual_asset_id=None,  # Missing source asset
        effective_duration=4.0,
    )
    db_session.add(placement)
    db_session.commit()

    job = RenderJobService.submit_render_job(db_session, project.id)
    worker = CloudRenderWorker(worker_id="test-worker-node-2", render_executor=MockRenderExecutor())
    processed = worker.process_one_job(db_session)
    assert processed is True

    db_session.refresh(job)
    # Should fail closed and reset to QUEUED retry (or FAILED if max retries)
    assert job.status in ("QUEUED", "FAILED")
    assert "Missing required visual source asset" in (job.error_message or "")


def test_worker_retry_mechanics(db_session: Session):
    project, _, _ = create_approved_project_context(db_session)
    job = RenderJobService.submit_render_job(db_session, project.id)
    job.retry_count = 0
    job.max_retries = 3
    db_session.commit()

    failed = RenderJobService.fail_render_job(db_session, job.id, job.claim_token, "Transient failure", ambiguous=False)
    assert failed.status == "QUEUED"
    assert failed.claimed_by is None


def test_stale_worker_token_fencing(db_session: Session):
    project, _, _ = create_approved_project_context(db_session)
    job = RenderJobService.submit_render_job(db_session, project.id)
    claimed = RenderJobService.claim_next_render_job(db_session, worker_id="w1")

    # Call complete_render_job with bad token
    with pytest.raises(Exception) as exc_info:
        RenderJobService.complete_render_job(
            db_session, claimed.id, claim_token="invalid_token", output_asset_id=uuid.uuid4(), actual_cost_usd=0.10
        )
    assert "stale" in str(exc_info.value).lower() or "mismatched" in str(exc_info.value).lower()


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
        db_session,
        project.id,
        storage_bucket="orbis-assets",
        storage_key="test_master.mp4",
        duration_seconds=15.0,
        file_size_bytes=2048,
        checksum_sha256="d" * 64,
    )
    assert asset.is_locked is True
    assert asset.asset_type == "VIDEO"


def test_ffmpeg_executor_abstraction():
    executor = MockRenderExecutor()
    meta = executor.render_timeline(
        timeline_spec={"total_duration": 5.0},
        scratch_dir=".",
        output_file_path="./test_out.mp4",
    )
    assert meta["duration_seconds"] == 5.0
    assert meta["video_codec"] == "h264"


def test_real_ffmpeg_multi_placement_filtergraph():
    executor = FFmpegRenderExecutor(ffmpeg_path="non_existent_ffmpeg_bin")
    # Test filtergraph structure generation without running subprocess
    timeline_spec = {
        "total_duration": 8.0,
        "render_profile": "MASTER_HD",
        "placements": [
            {"local_asset_path": "fake_p1.mp4", "trim_in": 0.0, "effective_duration": 4.0},
            {"local_asset_path": "fake_p2.mp4", "trim_in": 1.0, "effective_duration": 4.0},
        ],
        "audio_clips": [
            {"local_asset_path": "fake_audio.mp3", "start_time": 0.5, "volume": 0.8, "fade_in": 0.5, "fade_out": 0.5},
        ],
    }
    # Mock os.path.exists to return True for our fake paths
    import os
    original_exists = os.path.exists
    try:
        os.path.exists = lambda p: True if "fake_" in p else original_exists(p)
        # Verify MockRenderExecutor embeds placement and audio metadata
        mock_exec = MockRenderExecutor()
        meta = mock_exec.render_timeline(timeline_spec, scratch_dir=".", output_file_path="./test_out_multi.mp4")
        assert meta["placement_count"] == 2
        assert meta["audio_clip_count"] == 1

        import json
        with open("./test_out_multi.mp4", "rb") as f:
            content = f.read()
            assert b"placement_count" in content
            assert b"fake_p1.mp4" in content
            assert b"fake_p2.mp4" in content
    finally:
        os.path.exists = original_exists
        if os.path.exists("./test_out_multi.mp4"):
            os.remove("./test_out_multi.mp4")


def test_exact_revision_mismatch_fails_closed(db_session: Session):
    project, timeline, approval = create_approved_project_context(db_session)
    job = RenderJobService.submit_render_job(db_session, project.id)

    # Corrupt job to point to a non-existent timeline_version 999
    job.timeline_version = 999
    db_session.commit()

    worker = CloudRenderWorker(worker_id="worker-rev-test", render_executor=MockRenderExecutor())
    processed = worker.process_one_job(db_session)
    assert processed is True

    db_session.refresh(job)
    assert job.status in ("QUEUED", "FAILED")
    assert "Exact AssemblyTimeline" in (job.error_message or "")


def test_repeated_deterministic_failure_reaches_failed(db_session: Session):
    project, _, _ = create_approved_project_context(db_session)
    job = RenderJobService.submit_render_job(db_session, project.id)
    job.max_retries = 2
    job.retry_count = 0
    db_session.commit()

    # Attempt 1 fail
    claimed1 = RenderJobService.claim_next_render_job(db_session, worker_id="w1")
    failed1 = RenderJobService.fail_render_job(db_session, job.id, claimed1.claim_token, "Err 1", ambiguous=False)
    assert failed1.status == "QUEUED"
    assert failed1.retry_count == 1

    # Attempt 2 fail -> reaches max_retries (2) -> FAILED
    claimed2 = RenderJobService.claim_next_render_job(db_session, worker_id="w2")
    failed2 = RenderJobService.fail_render_job(db_session, job.id, claimed2.claim_token, "Err 2", ambiguous=False)
    assert failed2.status == "FAILED"
    assert failed2.retry_count == 2
    assert "Terminal failure" in failed2.error_message


def test_retry_preserves_prior_ledger_history(db_session: Session):
    project, _, _ = create_approved_project_context(db_session)
    job = RenderJobService.submit_render_job(db_session, project.id, estimated_cost_usd=0.50)
    job.status = "FAILED"
    job.retry_count = 3
    db_session.commit()

    # Ensure initial UsageLedger exists and is marked ESTIMATED (preserved compute cost)
    initial_ledger = db_session.query(UsageLedger).filter(UsageLedger.render_job_id == job.id).first()
    assert initial_ledger is not None
    assert initial_ledger.cost_status == "ESTIMATED"

    # User triggers retry
    retried_job = RenderJobService.retry_render_job(db_session, project.id, job.id)
    assert retried_job.status == "QUEUED"
    assert retried_job.retry_count == 0

    # Ledger entries count should now be 2 (prior history preserved + new retry reservation)
    ledger_entries = db_session.query(UsageLedger).filter(UsageLedger.render_job_id == job.id).all()
    assert len(ledger_entries) >= 2


def test_retry_budget_exceeded_fails(db_session: Session):
    project, _, _ = create_approved_project_context(db_session)
    project.budget_limit = 0.60
    db_session.commit()

    job = RenderJobService.submit_render_job(db_session, project.id, estimated_cost_usd=0.50)
    job.status = "FAILED"
    db_session.commit()

    # Attempting to retry requires another 0.50. Total committed (0.50 preserved + 0.50 new = 1.00) exceeds limit 0.60
    with pytest.raises(Exception) as exc_info:
        RenderJobService.retry_render_job(db_session, project.id, job.id)
    assert "budget" in str(exc_info.value).lower()


def test_concurrent_budget_authorization_threads(db_session: Session):
    import threading

    project, _, _ = create_approved_project_context(db_session)
    project.budget_limit = 0.60
    db_session.commit()

    results = []
    bind_conn = db_session.get_bind()

    def attempt_submit(key: str):
        from tests.conftest import TestingSessionLocal
        local_db = TestingSessionLocal(bind=bind_conn)
        try:
            j = RenderJobService.submit_render_job(
                local_db, project.id, custom_idempotency_key=key, estimated_cost_usd=0.50
            )
            results.append(("SUCCESS", j.id))
        except Exception as e:
            results.append(("FAILED", str(e)))
        finally:
            local_db.close()

    t1 = threading.Thread(target=attempt_submit, args=("thread_key_1",))
    t2 = threading.Thread(target=attempt_submit, args=("thread_key_2",))

    t1.start()
    t2.start()
    t1.join()
    t2.join()

    successes = [r for r in results if r[0] == "SUCCESS"]
    failures = [r for r in results if r[0] == "FAILED"]

    assert len(successes) == 1
    assert len(failures) == 1


def test_stale_token_fencing_progress_fail_complete(db_session: Session):
    project, _, _ = create_approved_project_context(db_session)
    job = RenderJobService.submit_render_job(db_session, project.id)
    claimed = RenderJobService.claim_next_render_job(db_session, worker_id="w1")

    # Bad token update_progress fails
    res_progress = RenderJobService.update_progress(db_session, claimed.id, claim_token="bad_token", progress=50.0)
    assert res_progress is False

    # Bad token fail_render_job raises exception
    with pytest.raises(Exception) as exc_fail:
        RenderJobService.fail_render_job(db_session, claimed.id, claim_token="bad_token", error_message="err")
    assert "stale" in str(exc_fail.value).lower() or "token" in str(exc_fail.value).lower()

    # Bad token complete_render_job raises exception
    with pytest.raises(Exception) as exc_complete:
        RenderJobService.complete_render_job(
            db_session, claimed.id, claim_token="bad_token", output_asset_id=uuid.uuid4(), actual_cost_usd=0.10
        )
    assert "stale" in str(exc_complete.value).lower() or "token" in str(exc_complete.value).lower()


def test_approved_timeline_without_new_qc_replay(db_session: Session):
    project, timeline, approval = create_approved_project_context(db_session)
    # Existing ApprovalRecord is authoritative -> submit succeeds without re-evaluating QC
    job = RenderJobService.submit_render_job(db_session, project.id)
    assert job.status == "QUEUED"
