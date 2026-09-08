"""P4-WP020-A deterministic zero-billing cross-module evidence.

External HTTP is forbidden. Known-bad integration truth is asserted explicitly
so green CI never masquerades as release readiness.
"""
import asyncio
import hashlib
import os
import shutil
import uuid
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.models.asset import Asset
from app.models.generation_job import GenerationJob
from app.models.project import Project
from app.models.render_job import RenderJob, RenderJobStatus
from app.models.scene import Scene
from app.models.shot import Shot
from app.models.story import Story
from app.providers.base import ProviderJobResult
from app.providers.factory import ProviderFactory
from app.services.archive.export_service import ProjectExportService
from app.services.archive.import_service import ProjectImportService, ProjectCollisionError
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
from app.services.video_materialization import VideoMaterializationService


@pytest.fixture(autouse=True)
def forbid_wp020a_external_http(monkeypatch):
    async def denied(*args, **kwargs):
        raise AssertionError("WP020-A forbids all unmocked external HTTP/provider calls")

    monkeypatch.setattr(httpx.AsyncClient, "request", denied)


class CompletedFakeVideoProvider:
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
    def burn_in(self, input_file_path, subtitle_file_path, output_file_path):
        assert os.path.exists(input_file_path)
        assert os.path.exists(subtitle_file_path)
        shutil.copyfile(input_file_path, output_file_path)


def _run_story_to_video_jobs(db):
    provider = FakeCreativeGenerationProvider()
    project = Project(
        id=uuid.uuid4(),
        title="WP020-A Deep Story",
        description="Deterministic zero-billing STORY fixture.",
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

    story = db.query(Story).filter(Story.project_id == project.id).one()
    jobs = (
        db.query(GenerationJob)
        .join(Shot, GenerationJob.shot_id == Shot.id)
        .join(Scene, Shot.scene_id == Scene.id)
        .filter(
            (Scene.project_id == project.id) | (Scene.story_id == story.id),
            GenerationJob.job_type == "VIDEO",
        )
        .all()
    )
    assert jobs
    assert all(job.status == "PENDING" for job in jobs)
    return project, story, jobs


def test_e2e_01_story_video_materialization_and_assembly_lineage_close(db_session, mock_storage):
    """Deep STORY path closes S1-A01/A03 without external provider/network use."""
    project, story, jobs = _run_story_to_video_jobs(db_session)

    async def fake_download(url, target_file_path):
        payload = ("WP020A_VIDEO:" + url).encode("utf-8")
        with open(target_file_path, "wb") as output:
            output.write(payload)
        return "video/mp4", len(payload), hashlib.sha256(payload).hexdigest()

    with (
        patch.object(ProviderFactory, "get_provider", return_value=CompletedFakeVideoProvider()),
        patch("app.services.video_materialization.get_storage_provider", return_value=mock_storage),
        patch.object(
            VideoMaterializationService,
            "_download_video_to_file",
            new=AsyncMock(side_effect=fake_download),
        ),
    ):
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
            assert completed.output_asset_id is not None
            asset = db_session.get(Asset, completed.output_asset_id)
            assert asset is not None
            assert asset.asset_type == "VIDEO"
            assert mock_storage.object_exists(asset.storage_bucket, asset.storage_key)

    state = ProductionOrchestrator.evaluate_state(db_session, project.id)
    assert state.current_stage == "VIDEO_IN_PROGRESS"
    assert state.recommended_action.action == "TRANSITION_TO_FINAL_REVIEW"
    assert ProductionOrchestrator.execute_action(
        db_session, project.id, "TRANSITION_TO_FINAL_REVIEW"
    ).to_stage == "FINAL_REVIEW"

    story_scenes = db_session.query(Scene).filter(Scene.story_id == story.id).all()
    assert story_scenes
    shots = (
        db_session.query(Shot)
        .join(Scene, Shot.scene_id == Scene.id)
        .filter(Scene.story_id == story.id)
        .all()
    )
    assert shots
    assert all(shot.source_asset_id is not None for shot in shots)

    timeline = AssemblyService.auto_assemble_timeline(db_session, str(project.id))
    assert len(timeline.shot_placements) == len(shots)
    assert all(p.source_type == "VIDEO" for p in timeline.shot_placements)
    assert all(p.visual_asset_id is not None for p in timeline.shot_placements)

    # S1-LIVE-01 regression: the same canonical STORY-linked scenes/shots must
    # continue into Core V1 AudioPlan without a noncanonical Scene.project_id fixture.
    audio_plan = AudioProductionService.generate_audio_plan(db_session, project.id)
    summary = audio_plan.plan_data["summary"]
    tracks = audio_plan.plan_data["tracks"]
    assert summary["total_scenes"] == len(story_scenes)
    assert summary["total_shots"] == len(shots)
    assert tracks["bgm_count"] == 1
    assert tracks["ambience_count"] == len(story_scenes)
    assert tracks["vo_count"] + tracks["dialogue_count"] >= 1


def _seed_materialized_video_project(db, mock_storage):
    project = Project(
        id=uuid.uuid4(),
        title="WP020-A Downstream Fixture",
        description="Materialized zero-billing downstream fixture.",
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
        visual_prompt="Safe deterministic test frame",
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
    return project, asset


def test_e2e_10_to_14_downstream_archive_roundtrip_closes_audio_history_gap(db_session, mock_storage):
    """Audio -> render -> multi-output -> FULL_SELF_CONTAINED CLONE is integrated and fenced."""
    project, source_asset = _seed_materialized_video_project(db_session, mock_storage)

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
    assert AudioProductionService.compute_auto_mix(db_session, project.id)["total_tracks"] >= 1

    project.status = "AUDIO_MIX_READY"
    db_session.commit()
    ProductionOrchestrator.approve_stage(db_session, project.id, stage="AUDIO_MIX_READY")
    ProductionOrchestrator.execute_action(db_session, project.id, "PROCEED_TO_ASSEMBLY")
    timeline = AssemblyService.auto_assemble_timeline(db_session, str(project.id))
    assert len(timeline.shot_placements) == 1
    assert timeline.shot_placements[0].source_type == "VIDEO"
    assert timeline.shot_placements[0].visual_asset_id == source_asset.id

    subtitle = SubtitleService.generate(db_session, project.id, timeline_id=str(timeline.id), language="th")
    assert subtitle["segments"]
    reviewed = SubtitleService.review(
        db_session, project.id, enabled=True, render_mode="BURN_IN", timeline_id=str(timeline.id)
    )
    assert reviewed["is_reviewed"] is True
    srt, srt_meta = SubtitleService.export_srt(db_session, project.id, str(timeline.id))
    assert "การทดสอบระบบแบบไม่เสียค่าใช้จ่าย" in srt
    assert srt_meta["sha256"] == hashlib.sha256(srt.encode("utf-8")).hexdigest()

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

    master = RenderJobService.submit_render_job(db_session, project.id)
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

    batch = RenderJobService.submit_export_batch(
        db_session,
        project.id,
        preset_ids=["YT_STANDARD_1080P", "TIKTOK_REELS_9X16", "INSTAGRAM_SQUARE"],
    )
    for _ in range(3):
        assert worker.process_one_job(db_session) is True
    variants = db_session.query(RenderJob).filter(RenderJob.batch_id == batch.id).all()
    assert len(variants) == 3
    assert all(job.status == RenderJobStatus.COMPLETED.value for job in variants)

    exporter = ProjectExportService(storage_provider=mock_storage)
    archive_path, manifest = exporter.export_project(db=db_session, project_id=project.id)
    try:
        assert manifest["archive_options"]["package_type"] == "FULL_SELF_CONTAINED"
        importer = ProjectImportService(storage_provider=mock_storage)
        validation = importer.validate_project_archive(archive_path, db_session)
        assert validation["valid"] is True
        clone = importer.execute_import(
            db=db_session,
            archive_path=archive_path,
            import_mode="CLONE",
            override_title="WP020-A Corrected Clone",
        )
        assert clone.id != project.id
        assert clone.source_project_id == project.id
        assert BudgetService.get_project_committed_cost(db_session, clone.id) == 0.0

        imported_jobs = db_session.query(RenderJob).filter(RenderJob.project_id == clone.id).all()
        assert imported_jobs
        assert all(job.imported_historical is True for job in imported_jobs)
        assert all(job.execution_disabled is True for job in imported_jobs)

        clone_timeline = AssemblyService.get_active_timeline(db_session, str(clone.id))
        assert clone_timeline is not None
        clone_subtitle = SubtitleService.get_active(
            db_session, clone.id, timeline_id=str(clone_timeline.id)
        )
        assert clone_subtitle is not None
        assert clone_subtitle["is_stale"] is False

        with pytest.raises(ProjectCollisionError):
            importer.execute_import(
                db=db_session,
                archive_path=archive_path,
                import_mode="RESTORE",
            )
    finally:
        if os.path.exists(archive_path):
            os.remove(archive_path)


def test_e2e_02_to_05_mode_routing_and_project_isolation(db_session):
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

    assert len({project.id for project, _ in projects}) == 4
    for project, action in projects:
        state = ProductionOrchestrator.evaluate_state(db_session, project.id)
        assert state.video_mode == project.video_mode
        assert state.recommended_action.action == action
        if project.video_mode != "STORY":
            assert db_session.query(Story).filter(Story.project_id == project.id).count() == 0

    first, _ = projects[0]
    second, _ = projects[1]
    db_session.add(Scene(id=uuid.uuid4(), project_id=first.id, scene_number=1, heading="Isolation"))
    db_session.commit()
    assert ProductionOrchestrator.evaluate_state(db_session, first.id).summary["scene_count"] == 1
    assert ProductionOrchestrator.evaluate_state(db_session, second.id).summary["scene_count"] == 0
