import os
import uuid
import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models.project import Project
from app.models.assembly import AssemblyTimeline
from app.models.qc import QCRun, ApprovalRecord
from app.models.render_job import RenderJob, RenderJobStatus
from app.models.render_batch import RenderBatch
from app.models.usage_ledger import UsageLedger
from app.models.asset import Asset
from app.services.render_job import RenderJobService
from app.services.export_preset import ExportPresetService, SYSTEM_EXPORT_PRESETS
from app.services.render import FFmpegRenderExecutor
from app.services.render.mock_executor import MockRenderExecutor
from app.services.render_worker import CloudRenderWorker
from app.services.storage.mock import InMemoryObjectStorageProvider


def create_approved_project_context(db: Session) -> tuple[Project, AssemblyTimeline, ApprovalRecord]:
    project = Project(
        id=uuid.uuid4(),
        title="Export Preset Test Project",
        video_mode="STORY",
        status="FINAL_REVIEW",
        budget_limit=20.0,
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


def test_export_presets_registry():
    presets = ExportPresetService.list_presets()
    assert len(presets) == 5
    preset_ids = [p["preset_id"] for p in presets]
    assert "YT_MASTER_4K" in preset_ids
    assert "YT_STANDARD_1080P" in preset_ids
    assert "TIKTOK_REELS_9X16" in preset_ids
    assert "INSTAGRAM_SQUARE" in preset_ids
    assert "LMS_WEB_720P" in preset_ids


def test_preset_dimensions_and_aspect_ratios():
    yt_4k = ExportPresetService.get_preset("YT_MASTER_4K")
    assert yt_4k["width"] == 3840 and yt_4k["height"] == 2160 and yt_4k["aspect_ratio"] == "16:9"

    yt_1080 = ExportPresetService.get_preset("YT_STANDARD_1080P")
    assert yt_1080["width"] == 1920 and yt_1080["height"] == 1080 and yt_1080["aspect_ratio"] == "16:9"

    tiktok = ExportPresetService.get_preset("TIKTOK_REELS_9X16")
    assert tiktok["width"] == 1080 and tiktok["height"] == 1920 and tiktok["aspect_ratio"] == "9:16"

    insta = ExportPresetService.get_preset("INSTAGRAM_SQUARE")
    assert insta["width"] == 1080 and insta["height"] == 1080 and insta["aspect_ratio"] == "1:1"

    lms = ExportPresetService.get_preset("LMS_WEB_720P")
    assert lms["width"] == 1280 and lms["height"] == 720 and lms["aspect_ratio"] == "16:9"


def test_approval_gate_enforcement_for_export_batch(db_session: Session):
    project = Project(
        id=uuid.uuid4(),
        title="Unapproved Test",
        video_mode="STORY",
        status="DRAFT",
        budget_limit=10.0,
    )
    db_session.add(project)
    db_session.flush()

    timeline = AssemblyTimeline(
        id=uuid.uuid4(),
        project_id=project.id,
        version=1,
        status="DRAFT",
    )
    db_session.add(timeline)
    db_session.commit()

    with pytest.raises(Exception) as exc_info:
        RenderJobService.submit_export_batch(
            db=db_session,
            project_id=project.id,
            preset_ids=["YT_STANDARD_1080P"],
        )
    assert "APPROVED" in str(exc_info.value)


def test_atomic_batch_authorization(db_session: Session):
    project, timeline, approval = create_approved_project_context(db_session)
    preset_ids = ["YT_STANDARD_1080P", "TIKTOK_REELS_9X16", "INSTAGRAM_SQUARE"]

    batch = RenderJobService.submit_export_batch(
        db=db_session,
        project_id=project.id,
        preset_ids=preset_ids,
    )

    assert batch is not None
    assert batch.total_variants == 3
    assert batch.status == "PROCESSING"
    assert batch.estimated_total_cost_usd == 1.50

    jobs = db_session.query(RenderJob).filter(RenderJob.batch_id == batch.id).all()
    assert len(jobs) == 3

    for job in jobs:
        assert job.status == RenderJobStatus.QUEUED.value
        assert job.render_variant_key != "MASTER"
        assert job.current_usage_ledger_id is not None
        ledger = db_session.get(UsageLedger, job.current_usage_ledger_id)
        assert ledger is not None
        assert ledger.cost_status == "ESTIMATED"


def test_zero_partial_state_on_authorization_failure(db_session: Session):
    project, timeline, approval = create_approved_project_context(db_session)
    project_id = project.id
    project.budget_limit = 0.10  # Less than preset cost 0.50
    db_session.commit()

    with pytest.raises(Exception):
        RenderJobService.submit_export_batch(
            db=db_session,
            project_id=project_id,
            preset_ids=["YT_STANDARD_1080P", "TIKTOK_REELS_9X16"],
        )

    # Verify zero partial state
    batches = db_session.query(RenderBatch).filter(RenderBatch.project_id == project_id).all()
    assert len(batches) == 0

    jobs = db_session.query(RenderJob).filter(RenderJob.project_id == project_id).all()
    assert len(jobs) == 0

    export_ledgers = db_session.query(UsageLedger).filter(
        UsageLedger.project_id == project_id,
        UsageLedger.operation.like("EXPORT_PRESET_%"),
    ).all()
    assert len(export_ledgers) == 0


def test_concurrent_variant_submissions(db_session: Session):
    project, timeline, approval = create_approved_project_context(db_session)

    # Submit 3 distinct preset variants for the same timeline revision
    batch = RenderJobService.submit_export_batch(
        db=db_session,
        project_id=project.id,
        preset_ids=["YT_STANDARD_1080P", "TIKTOK_REELS_9X16", "INSTAGRAM_SQUARE"],
    )

    active_jobs = db_session.query(RenderJob).filter(
        RenderJob.project_id == project.id,
        RenderJob.timeline_id == timeline.id,
        RenderJob.status == RenderJobStatus.QUEUED.value,
    ).all()

    assert len(active_jobs) == 3
    variant_keys = {j.render_variant_key for j in active_jobs}
    assert len(variant_keys) == 3


def test_idempotent_variant_replay(db_session: Session):
    project, timeline, approval = create_approved_project_context(db_session)

    batch1 = RenderJobService.submit_export_batch(
        db=db_session,
        project_id=project.id,
        preset_ids=["YT_STANDARD_1080P"],
    )

    batch2 = RenderJobService.submit_export_batch(
        db=db_session,
        project_id=project.id,
        preset_ids=["YT_STANDARD_1080P"],
    )

    jobs = db_session.query(RenderJob).filter(RenderJob.project_id == project.id).all()
    # Re-submitting the same preset variant returns active existing job without creating duplicate
    assert len(jobs) == 1


def test_reconciliation_variant_isolation(db_session: Session):
    project, timeline, approval = create_approved_project_context(db_session)
    project_id = project.id

    batch = RenderJobService.submit_export_batch(
        db=db_session,
        project_id=project_id,
        preset_ids=["YT_STANDARD_1080P", "TIKTOK_REELS_9X16"],
    )

    jobs = db_session.query(RenderJob).filter(RenderJob.batch_id == batch.id).all()
    yt_job = next(j for j in jobs if j.render_profile == "YT_STANDARD_1080P")
    tiktok_job = next(j for j in jobs if j.render_profile == "TIKTOK_REELS_9X16")

    # Mark YT variant as RECONCILIATION_REQUIRED
    yt_job.status = RenderJobStatus.RECONCILIATION_REQUIRED.value
    db_session.commit()

    # Re-submitting YT variant fails closed
    with pytest.raises(Exception):
        RenderJobService.submit_export_batch(
            db=db_session,
            project_id=project_id,
            preset_ids=["YT_STANDARD_1080P"],
        )

    # Submitting sibling variant INSTAGRAM_SQUARE succeeds without block
    batch2 = RenderJobService.submit_export_batch(
        db=db_session,
        project_id=project_id,
        preset_ids=["INSTAGRAM_SQUARE"],
    )
    assert batch2 is not None


def test_wp017_master_protection_regression(db_session: Session):
    project, timeline, approval = create_approved_project_context(db_session)

    # Submit WP017 master render
    master_job = RenderJobService.submit_render_job(
        db=db_session,
        project_id=project.id,
        render_profile="MASTER_HD",
    )

    assert master_job.render_variant_key == "MASTER"

    # Re-submitting master render returns existing active master job idempotently
    master_job2 = RenderJobService.submit_render_job(
        db=db_session,
        project_id=project.id,
        render_profile="MASTER_HD",
    )

    assert master_job.id == master_job2.id

    # Master render coexists with export preset variants
    export_batch = RenderJobService.submit_export_batch(
        db=db_session,
        project_id=project.id,
        preset_ids=["TIKTOK_REELS_9X16"],
    )

    all_jobs = db_session.query(RenderJob).filter(RenderJob.project_id == project.id).all()
    assert len(all_jobs) == 2


def test_worker_execution_and_asset_lineage(db_session: Session):
    project, timeline, approval = create_approved_project_context(db_session)

    batch = RenderJobService.submit_export_batch(
        db=db_session,
        project_id=project.id,
        preset_ids=["TIKTOK_REELS_9X16"],
    )

    storage = InMemoryObjectStorageProvider()
    mock_exec = MockRenderExecutor()
    worker = CloudRenderWorker(
        worker_id="test_worker_1",
        storage_provider=storage,
        render_executor=mock_exec,
    )

    processed = worker.process_one_job(db=db_session)
    assert processed is True

    job = db_session.query(RenderJob).filter(RenderJob.batch_id == batch.id).first()
    assert job.status == RenderJobStatus.COMPLETED.value
    assert job.output_asset_id is not None

    asset = db_session.get(Asset, job.output_asset_id)
    assert asset is not None
    assert asset.asset_type == "EXPORT_VIDEO"
    assert "TIKTOK_REELS_9X16" in asset.name
    assert "exports" in asset.storage_key

    # Parent batch should be settled as COMPLETED
    db_session.refresh(batch)
    assert batch.status == "COMPLETED"
    assert batch.completed_variants == 1


def test_api_export_preset_endpoints(client: TestClient, db_session: Session):
    project, timeline, approval = create_approved_project_context(db_session)

    # GET /api/v1/projects/{project_id}/renders/presets
    res = client.get(f"/api/v1/projects/{project.id}/renders/presets")
    assert res.status_code == 200
    presets = res.json()
    assert len(presets) == 5

    # POST /api/v1/projects/{project_id}/renders/export-batch
    post_res = client.post(
        f"/api/v1/projects/{project.id}/renders/export-batch",
        json={"preset_ids": ["YT_STANDARD_1080P", "INSTAGRAM_SQUARE"]},
    )
    assert post_res.status_code == 200
    batch_data = post_res.json()
    assert batch_data["total_variants"] == 2
    batch_id = batch_data["id"]

    # GET /api/v1/projects/{project_id}/renders/batches/{batch_id}
    get_res = client.get(f"/api/v1/projects/{project.id}/renders/batches/{batch_id}")
    assert get_res.status_code == 200
    get_data = get_res.json()
    assert get_data["id"] == batch_id


def test_duplicate_preset_ids_deduplicated(db_session: Session):
    project, timeline, approval = create_approved_project_context(db_session)

    # Submitting duplicate preset IDs in the same request deduplicates them
    batch = RenderJobService.submit_export_batch(
        db=db_session,
        project_id=project.id,
        preset_ids=["YT_STANDARD_1080P", "YT_STANDARD_1080P", "yt_standard_1080p"],
    )

    assert batch is not None
    assert batch.total_variants == 1
    jobs = db_session.query(RenderJob).filter(RenderJob.batch_id == batch.id).all()
    assert len(jobs) == 1
    ledgers = db_session.query(UsageLedger).filter(UsageLedger.render_job_id == jobs[0].id).all()
    assert len(ledgers) == 1


def test_conflict_active_variant_raises_400(db_session: Session):
    project, timeline, approval = create_approved_project_context(db_session)

    # Create active batch with 1 preset
    batch1 = RenderJobService.submit_export_batch(
        db=db_session,
        project_id=project.id,
        preset_ids=["YT_STANDARD_1080P"],
    )
    assert batch1 is not None

    # Submitting active preset combined with a new preset raises exception (400 conflict)
    with pytest.raises(Exception) as exc_info:
        RenderJobService.submit_export_batch(
            db=db_session,
            project_id=project.id,
            preset_ids=["YT_STANDARD_1080P", "INSTAGRAM_SQUARE"],
        )
    assert "already exists in state" in str(exc_info.value)
