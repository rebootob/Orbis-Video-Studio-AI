"""P4-WP020-A deterministic zero-billing end-to-end evidence.

These tests intentionally cross module boundaries. External HTTP is forbidden.
A known-bad integration truth may be asserted explicitly so CI records the
release gap without disguising it as a passing product acceptance row.
"""
import asyncio
import hashlib
import os
import shutil
import uuid
from unittest.mock import patch

import httpx
import pytest

from app.models.asset import Asset
from app.models.audio_clip import AudioClip
from app.models.generation_job import GenerationJob
from app.models.project import Project
from app.models.qc import QCFinding
from app.models.render_job import RenderJob, RenderJobStatus
from app.models.scene import Scene
from app.models.shot import Shot
from app.models.story import Story
from app.models.usage_ledger import UsageLedger
from app.providers.base import ProviderJobResult
from app.providers.factory import ProviderFactory
from app.services.archive.export_service import ProjectExportService
from app.services.archive.import_service import ProjectImportService
from app.services.assembly import AssemblyService
from app.services.audio_production import AudioProductionService
from app.services.budget import BudgetService
from app.services.creative_generation.fake_provider import FakeCreativeGenerationProvider
from app.services.job_dispatch import JobDispatchService
from app.services.production_orchestrator import ProductionOrchestrator
from app.services.qc import QCService
from app.services.render.mock_executor import MockRenderExecutor
from app.services.render_job import RenderJobService
from app.services.render_worker import CloudRenderWorker
from app.services.subtitle_control import SubtitleService


@pytest.fixture(autouse=True)
def forbid_wp020a_external_http(monkeypatch):
    """WP020-A must never perform a real/paid provider request."""

    async def denied(*args, **kwargs):
        raise AssertionError("WP020-A forbids all unmocked external HTTP/provider calls")

    monkeypatch.setattr(httpx.AsyncClient, "request", denied)


class CompletedFakeVideoProvider:
    """Synchronous-completion VideoProvider test double; never performs HTTP."""

    @property
    def provider_id(self):
        return "vidu"

    def validate_config(self, config):
        return True

    async def submit_generation_job(self, params):
        return ProviderJobResult(
            provider_job_id=f"wp020a-{params.shot_id}",
            status="COMPLETED",
            video_url=f"https://zero-billing.invalid/{params.shot_id}.mp4",
            cost_usd=0.0,
        )

    async def check_job_status(self, provider_job_id):
        return ProviderJobResult(
            provider_job_id=provider_job_id,
            status="COMPLETED",
            video_url=f"https://zero-billing.invalid/{provider_job_id}.mp4",
            cost_usd=0.0,
        )

    async def cancel_job(self, provider_job_id):
        return True


class CopySubtitleBurnIn:
    """Zero-billing burn-in test double: proves wiring without invoking FFmpeg."""

    def burn_in(self, input_file_path, subtitle_file_path, output_file_path):
        assert os.path.exists(input_file_path)
        assert os.path.exists(subtitle_file_path)
        shutil.copyfile(input_file_path, output_file_path)


def _run_story_to_video_jobs(db):
    provider = FakeCreativeGenerationProvider()
    project = Project(
        id=uuid.uuid4(),
        title="WP020-A Deep Story",
        description="A deterministic corporate training story used only for zero-billing E2E evidence.",
        video_mode="STORY",
        status="DRAFT",
        automation_mode="MANUAL",
        budget_limit=100.0,
        budget_currency="USD",
    )
    db.add(project)
    db.commit()

    ProductionOrchestrator.execute_action(db, project.id, "GENERATE_STORY", provider=provider)
    ProductionOrchestrator.approve_stage(db, project.id, stage="STORY_GENERATED", provider=provider)
    ProductionOrchestrator.execute_action(db, project.id, "GENERATE_STORYBOARD", provider=provider)
    ProductionOrchestrator.approve_stage(db, project.id, stage="STORYBOARD_GENERATED", provider=provider)
    ProductionOrchestrator.execute_action(db, project.id, "GENERATE_SHOT_PLAN", provider=provider)
    ProductionOrchestrator.approve_stage(db, project.id, stage="SHOT_PLAN_GENERATED", provider=provider)
    ProductionOrchestrator.execute_action(
        db,
        project.id,
        "START_KEYFRAME_GENERATION",
        parameters={"cost_authorized": True},
        provider=provider,
    )
    ProductionOrchestrator.approve_stage(db, project.id, stage="IMAGES_GENERATED", provider=provider)
    ProductionOrchestrator.execute_action(db, project.id, "START_VIDEO_GENERATION", provider=provider)

    jobs = (
        db.query(GenerationJob)
        .join(Shot, GenerationJob.shot_id == Shot.id)
        .join(Scene, Shot.scene_id == Scene.id)
        .filter(Scene.project_id == project.id)
        .all()
    )
    if not jobs:
        story = db.query(Story).filter(Story.project_id == project.id).one()
        jobs = (
            db.query(GenerationJob)
            .join(Shot, GenerationJob.shot_id == Shot.id)
            .join(Scene, Shot.scene_id == Scene.id)
            .filter(Scene.story_id == story.id)
            .all()
        )
    assert jobs
    return project, jobs


def test_e2e_01_story_provider_completion_exposes_video_asset_materialization_gap(db_session):
    """Deep STORY path proves the current VideoProvider->Asset integration blocker.

    The queue truth can become COMPLETED and orchestration can advance to final
    review while the provider output URL has never become a durable Orbis VIDEO
    Asset bound to the Shot. Assembly therefore falls back to KEYFRAME instead
    of the generated video. This is intentionally asserted as current truth and
    classified as an S1 finding in P4_WP020_A_EVIDENCE.md.
    """
    project, jobs = _run_story_to_video_jobs(db_session)
    fake_video = CompletedFakeVideoProvider()

    with patch.object(ProviderFactory, "get_provider", return_value=fake_video):
        for job in jobs:
            claimed = JobDispatchService.claim_next_job(
                db_session,
                worker_id="wp020a-video-worker",
                job_id=job.id,
            )
            assert claimed is not None
            completed = asyncio.run(
                JobDispatchService.process_job(
                    db_session,
                    job.id,
                    claim_token=claimed.claim_token,
                )
            )
            assert completed.status == "COMPLETED"
            assert (completed.result or {}).get("video_url")

    state = ProductionOrchestrator.evaluate_state(db_session, project.id)
    assert state.current_stage == "VIDEO_IN_PROGRESS"
    assert state.recommended_action.action == "TRANSITION_TO_FINAL_REVIEW"

    transition = ProductionOrchestrator.execute_action(
        db_session,
        project.id,
        "TRANSITION_TO_FINAL_REVIEW",
    )
    assert transition.to_stage == "FINAL_REVIEW"

    story = db_session.query(Story).filter(Story.project_id == project.id).one()
    shots = (
        db_session.query(Shot)
        .join(Scene, Shot.scene_id == Scene.id)
        .filter((Scene.project_id == project.id) | (Scene.story_id == story.id))
        .all()
    )
    assert shots
    assert all(shot.source_asset_id is None for shot in shots)

    timeline = AssemblyService.auto_assemble_timeline(db_session, str(project.id))
    assert timeline.shot_placements
    assert all(p.source_type != "VIDEO" for p in timeline.shot_placements)
    assert any(p.source_type == "KEYFRAME" for p in timeline.shot_placements)


def _seed_materialized_video_project(db, mock_storage):
    project = Project(
        id=uuid.uuid4(),
        title="WP020-A Downstream Fixture",
        description="Durably materialized zero-billing fixture for downstream system integration.",
        video_mode="SHORT",
        status="FINAL_REVIEW",
        preferred_aspect_ratio="9:16",
        budget_limit=50.0,
        budget_currency="USD",
    )
    db.add(project)
    db.flush()

    scene = Scene(
        id=uuid.uuid4(),
        project_id=project.id,
        scene_number=1,
        heading="Short scene",
        narration="การทดสอบระบบแบบไม่เสียค่าใช้จ่าย",
    )
    db.add(scene)
    db.flush()

    shot = Shot(
        id=uuid.uuid4(),
        scene_id=scene.id,
        shot_number=1,
        shot_type="AI_GENERATED",
        status="COMPLETED",
        visual_prompt="A safe deterministic test frame",
        action="การทดสอบระบบแบบไม่เสียค่าใช้จ่าย",
        duration_seconds=4.0,
        source_metadata={"has_audio": False},
    )
    db.add(shot)
    db.flush()

    video_bytes = b"ORBIS_WP020A_SYNTHETIC_SOURCE_VIDEO"
    storage_key = f"projects/{project.id}/video/wp020a-source.mp4"
    mock_storage.put_object("default", storage_key, video_bytes, "video/mp4")
    asset = Asset(
        id=uuid.uuid4(),
        project_id=project.id,
        name="WP020-A materialized source video",
        original_filename="wp020a-source.mp4",
        asset_type="VIDEO",
        content_type="video/mp4",
        file_size_bytes=len(video_bytes),
        checksum_sha256=hashlib.sha256(video_bytes).hexdigest(),
        storage_bucket="default",
        storage_key=storage_key,
    )
    db.add(asset)
    db.flush()
    shot.source_asset_id = asset.id
    db.commit()
    return project, scene, shot, asset


def test_e2e_10_to_14_downstream_audio_subtitle_qc_render_multioutput_archive(
    db_session,
    mock_storage,
):
    """Cross-module zero-billing proof for the downstream half of Core V1."""
    project, scene, shot, source_asset = _seed_materialized_video_project(db_session, mock_storage)

    # Audio plan -> mock generation -> auto mix -> approval.
    audio_plan = AudioProductionService.generate_audio_plan(db_session, project.id)
    assert audio_plan.status == "DRAFT"
    AudioProductionService.approve_audio_plan(db_session, project.id)
    audio_result = AudioProductionService.execute_audio_batch(
        db=db_session,
        project_id=project.id,
        action="CONTINUE_INCOMPLETE_AUDIO",
        cost_authorized=True,
        actor="USER",
        provider_name="mock_audio",
    )
    assert audio_result["failed"] == 0
    assert audio_result["succeeded"] >= 1
    mix = AudioProductionService.compute_auto_mix(db_session, project.id)
    assert mix["total_tracks"] >= 1
    project.status = "AUDIO_MIX_READY"
    db_session.commit()
    ProductionOrchestrator.approve_stage(db_session, project.id, stage="AUDIO_MIX_READY")
    ProductionOrchestrator.execute_action(db_session, project.id, "PROCEED_TO_ASSEMBLY")
    assert project.status == "READY_FOR_ASSEMBLY"

    # Assembly uses the durable VIDEO Asset rather than a planning/keyframe fallback.
    timeline = AssemblyService.auto_assemble_timeline(db_session, str(project.id))
    assert len(timeline.shot_placements) == 1
    placement = timeline.shot_placements[0]
    assert placement.source_type == "VIDEO"
    assert placement.visual_asset_id == source_asset.id

    # Subtitle generation/review/SRT and burn-in snapshot are fully deterministic.
    subtitle = SubtitleService.generate(
        db_session,
        project.id,
        timeline_id=str(timeline.id),
        language="th",
    )
    assert subtitle["segments"]
    reviewed = SubtitleService.review(
        db_session,
        project.id,
        enabled=True,
        render_mode="BURN_IN",
        timeline_id=str(timeline.id),
    )
    assert reviewed["is_reviewed"] is True
    assert reviewed["render_mode"] == "BURN_IN"
    srt, srt_meta = SubtitleService.export_srt(db_session, project.id, str(timeline.id))
    assert "การทดสอบระบบแบบไม่เสียค่าใช้จ่าย" in srt
    assert srt_meta["sha256"] == hashlib.sha256(srt.encode("utf-8")).hexdigest()

    # QC + explicit human approval are bound to the exact timeline revision.
    qc_run = QCService.run_qc(db_session, project.id)
    for finding in list(qc_run.findings):
        if finding.severity == "WARNING":
            QCService.record_warning_decision(
                db_session,
                project.id,
                finding.id,
                decision="ACCEPTED_WITH_REASON",
                reason="WP020-A deterministic evidence fixture",
                actor="WP020-A",
            )
    db_session.refresh(qc_run)
    assert qc_run.blocker_count == 0
    approval = ProductionOrchestrator.approve_final_production(
        db_session,
        project.id,
        timeline_id=timeline.id,
        qc_run_id=qc_run.id,
        notes="WP020-A zero-billing approval evidence",
        actor="WP020-A",
    )
    assert approval.status == "APPROVED"
    assert project.status == "COMPLETED"

    # Master render through the production worker boundary + fake executor.
    master = RenderJobService.submit_render_job(db_session, project.id)
    assert master.status == RenderJobStatus.QUEUED.value
    worker = CloudRenderWorker(
        worker_id="wp020a-render-worker",
        storage_provider=mock_storage,
        render_executor=MockRenderExecutor(),
        subtitle_burnin=CopySubtitleBurnIn(),
    )
    assert worker.process_one_job(db_session) is True
    db_session.refresh(master)
    assert master.status == RenderJobStatus.COMPLETED.value
    assert master.output_asset_id is not None
    assert (master.render_metadata or {}).get("subtitle", {}).get("mode") == "BURN_IN"

    # Multi-output 16:9 / 9:16 / 1:1 from the same approved timeline.
    batch = RenderJobService.submit_export_batch(
        db_session,
        project.id,
        preset_ids=["YT_STANDARD_1080P", "TIKTOK_REELS_9X16", "INSTAGRAM_SQUARE"],
    )
    assert batch.total_variants == 3
    for _ in range(3):
        assert worker.process_one_job(db_session) is True
    variant_jobs = db_session.query(RenderJob).filter(RenderJob.batch_id == batch.id).all()
    assert len(variant_jobs) == 3
    assert all(job.status == RenderJobStatus.COMPLETED.value for job in variant_jobs)
    aspect_ratios = {
        (job.render_metadata or {}).get("preset_snapshot", {}).get("aspect_ratio")
        for job in variant_jobs
    }
    assert {"16:9", "9:16", "1:1"}.issubset(aspect_ratios)

    # FULL_SELF_CONTAINED .orbis round-trip keeps history/subtitles, while
    # imported historical jobs/ledgers remain fenced from live execution/budget.
    archive_path, manifest = ProjectExportService(storage_provider=mock_storage).export_project(
        db=db_session,
        project_id=project.id,
    )
    try:
        assert manifest["package_type"] == "FULL_SELF_CONTAINED"
        importer = ProjectImportService(storage_provider=mock_storage)
        validation = importer.validate_project_archive(archive_path, db_session)
        assert validation["valid"] is True
        clone = importer.execute_import(
            db=db_session,
            archive_path=archive_path,
            import_mode="CLONE",
            override_title="WP020-A Clone",
        )
        assert clone.id != project.id
        assert clone.source_project_id == project.id
        assert BudgetService.get_project_committed_cost(db_session, clone.id) == 0.0

        imported_render_jobs = db_session.query(RenderJob).filter(RenderJob.project_id == clone.id).all()
        assert imported_render_jobs
        assert all(job.imported_historical is True for job in imported_render_jobs)
        assert all(job.execution_disabled is True for job in imported_render_jobs)

        clone_timeline = AssemblyService.get_active_timeline(db_session, str(clone.id))
        assert clone_timeline is not None
        clone_subtitle = SubtitleService.get_active(
            db_session,
            clone.id,
            timeline_id=str(clone_timeline.id),
        )
        assert clone_subtitle is not None
        assert clone_subtitle["is_stale"] is False
    finally:
        if os.path.exists(archive_path):
            os.remove(archive_path)


def test_e2e_02_to_05_mode_routing_and_project_isolation_remain_bounded(db_session):
    """All four Core V1 modes keep their distinct creative entry contracts."""
    expected = {
        "STORY": "GENERATE_STORY",
        "SHORT": "GENERATE_STORYBOARD",
        "LOOP": "GENERATE_SHOT_PLAN",
        "SCENE": "GENERATE_STORYBOARD",
    }
    projects = []
    for mode, action in expected.items():
        project = Project(
            id=uuid.uuid4(),
            title=f"WP020-A {mode}",
            description=f"Isolated {mode} fixture",
            video_mode=mode,
            status="DRAFT",
        )
        db_session.add(project)
        projects.append((project, action))
    db_session.commit()

    ids = {project.id for project, _ in projects}
    assert len(ids) == 4
    for project, action in projects:
        state = ProductionOrchestrator.evaluate_state(db_session, project.id)
        assert state.video_mode == project.video_mode
        assert state.recommended_action.action == action
        if project.video_mode != "STORY":
            assert db_session.query(Story).filter(Story.project_id == project.id).count() == 0

    # A foreign project lookup never returns another project's production graph.
    first, _ = projects[0]
    second, _ = projects[1]
    scene = Scene(id=uuid.uuid4(), project_id=first.id, scene_number=1, heading="Isolation")
    db_session.add(scene)
    db_session.commit()
    first_state = ProductionOrchestrator.evaluate_state(db_session, first.id)
    second_state = ProductionOrchestrator.evaluate_state(db_session, second.id)
    assert first_state.summary["scene_count"] == 1
    assert second_state.summary["scene_count"] == 0
