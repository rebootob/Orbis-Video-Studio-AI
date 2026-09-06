"""Comprehensive Test Suite for P3-WP014 Core V1 Audio Production Automation."""
import uuid
import pytest
import struct
from unittest.mock import patch
from fastapi import HTTPException
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from app.models.project import Project
from app.models.scene import Scene
from app.models.shot import Shot
from app.models.asset import Asset
from app.models.usage_ledger import UsageLedger
from app.models.audio_clip import (
    AudioClip,
    AudioSourceType,
    AudioType,
    AudioGenerationMode,
    AudioScope,
    DuckingRole,
)
from app.models.audio_plan import AudioPlan
from app.models.audio_history import AudioPlanVersion, AudioClipHistory
from app.schemas.audio_spec import AudioSpec
from app.providers.audio.base import AudioGenerationParams, AudioJobResult
from app.providers.audio.mock_adapter import MockAudioProviderAdapter
from app.providers.audio.factory import AudioProviderFactory
from app.services.audio_production import AudioProductionService
from app.services.production_orchestrator import ProductionOrchestrator
from app.services.pricing import CostStatus


# ----------------- 1. Provider Neutral Contract & Mock Adapter Tests -----------------

def test_mock_audio_provider_wav_header_and_costs():
    """Verify mock audio provider generates deterministic 44-byte WAV header and calculates costs."""
    adapter = MockAudioProviderAdapter(provider_id="mock_audio")
    caps = adapter.get_capabilities()
    assert "VO" in caps.supported_audio_types
    assert "BGM" in caps.supported_audio_types
    assert caps.supports_tts is True
    assert caps.supports_music is True

    # Test VO Generation (cost = $0.02)
    import asyncio
    vo_params = AudioGenerationParams(
        clip_id="test-vo-1",
        audio_type="VO",
        prompt="Voiceover narration test",
        duration_seconds=3.0,
    )
    vo_result = asyncio.run(adapter.generate_audio(vo_params))
    assert vo_result.status == "COMPLETED"
    assert vo_result.cost_usd == 0.02
    assert vo_result.content_type == "audio/wav"
    assert len(vo_result.audio_data) >= 44
    assert vo_result.audio_data[:4] == b"RIFF"
    assert vo_result.audio_data[8:12] == b"WAVE"

    # Test BGM Generation (cost = $0.05)
    bgm_params = AudioGenerationParams(
        clip_id="test-bgm-1",
        audio_type="BGM",
        prompt="Orchestral film score",
        duration_seconds=10.0,
    )
    bgm_result = asyncio.run(adapter.generate_audio(bgm_params))
    assert bgm_result.status == "COMPLETED"
    assert bgm_result.cost_usd == 0.05


# ----------------- 2. Three-Dimensional Audio Model & Orthogonality -----------------

def test_locked_three_dimensional_model_and_overrides():
    """Verify source_type, audio_type, and generation_mode are strictly orthogonal."""
    # Default VO classification
    vo_cls = AudioProductionService.auto_classify_clip(AudioType.VO)
    assert vo_cls["source_type"] == AudioSourceType.GENERATED_AUDIO.value
    assert vo_cls["generation_mode"] == AudioGenerationMode.SEPARATE_AUDIO.value
    assert vo_cls["scope"] == AudioScope.SHOT.value
    assert vo_cls["ducking_role"] == DuckingRole.FOREGROUND.value

    # Default BGM classification
    bgm_cls = AudioProductionService.auto_classify_clip(AudioType.BGM)
    assert bgm_cls["source_type"] == AudioSourceType.GENERATED_AUDIO.value
    assert bgm_cls["generation_mode"] == AudioGenerationMode.SEPARATE_AUDIO.value
    assert bgm_cls["scope"] == AudioScope.PROJECT.value
    assert bgm_cls["ducking_role"] == DuckingRole.BACKGROUND.value
    assert bgm_cls["ducking_amount_db"] == -12.0

    # Human Override is preserved
    override_cls = AudioProductionService.auto_classify_clip(
        audio_type=AudioType.BGM,
        source_type=AudioSourceType.IMPORTED_AUDIO,
        generation_mode=AudioGenerationMode.EMBEDDED_EXISTING,
        scope=AudioScope.SCENE,
    )
    assert override_cls["source_type"] == AudioSourceType.IMPORTED_AUDIO.value
    assert override_cls["generation_mode"] == AudioGenerationMode.EMBEDDED_EXISTING.value
    assert override_cls["scope"] == AudioScope.SCENE.value


def test_voice_generation_policy():
    """Verify VO defaults to SEPARATE_AUDIO; Dialogue defaults to SEPARATE_AUDIO unless native video audio is supported."""
    # VO is always SEPARATE_AUDIO
    vo = AudioProductionService.auto_classify_clip(AudioType.VO, video_supports_native_audio=True)
    assert vo["generation_mode"] == AudioGenerationMode.SEPARATE_AUDIO.value

    # Dialogue without native audio support -> SEPARATE_AUDIO
    diag_sep = AudioProductionService.auto_classify_clip(AudioType.DIALOGUE, video_supports_native_audio=False)
    assert diag_sep["generation_mode"] == AudioGenerationMode.SEPARATE_AUDIO.value

    # Dialogue with native video provider audio support -> WITH_VIDEO
    diag_native = AudioProductionService.auto_classify_clip(AudioType.DIALOGUE, video_supports_native_audio=True)
    assert diag_native["generation_mode"] == AudioGenerationMode.WITH_VIDEO.value


# ----------------- 3. Canonical AudioSpec Rendering -----------------

def test_audio_spec_rendering():
    """Verify structured AudioSpec renders into various provider formats."""
    spec = AudioSpec(
        clip_id="c-1",
        audio_type=AudioType.VO,
        source_type=AudioSourceType.GENERATED_AUDIO,
        generation_mode=AudioGenerationMode.SEPARATE_AUDIO,
        scope=AudioScope.SHOT,
        prompt="A young hero embarks on a great journey.",
        speaker="Narrator",
        language="en",
        duration_seconds=5.0,
    )

    # Video prompt
    v_prompt = spec.to_video_prompt()
    assert "[Native Audio / Dialogue]" in v_prompt
    assert "Narrator:" in v_prompt

    # TTS request
    tts_req = spec.to_tts_request()
    assert tts_req["text"] == "A young hero embarks on a great journey."
    assert tts_req["voice_id"] == "Narrator"
    assert tts_req["language"] == "en"

    # Copy prompt
    copy = spec.to_copy_prompt()
    assert "=== Audio Spec: VO (SHOT) ===" in copy
    assert "Generation Mode: SEPARATE_AUDIO" in copy


# ----------------- 4. Audio Plan Generation & Approval -----------------

def test_generate_and_approve_audio_plan(db_session: Session):
    """Test generating a structured AudioPlan and approving it."""
    # Create test project, scene, shot
    project = Project(
        id=uuid.uuid4(),
        title="Audio Adventure",
        video_mode="STORY",
        status="VIDEO_IN_PROGRESS",
    )
    db_session.add(project)
    db_session.flush()

    scene = Scene(
        id=uuid.uuid4(),
        project_id=project.id,
        scene_number=1,
        heading="Forest Glade",
    )
    db_session.add(scene)
    db_session.flush()

    shot = Shot(
        id=uuid.uuid4(),
        scene_id=scene.id,
        shot_number=1,
        shot_type="AI_GENERATED",
        visual_prompt="Hero steps into the trees",
        action="The woods were quiet.",
        subject="Hero",
        duration_seconds=4.0,
    )
    db_session.add(shot)
    db_session.commit()

    # 1. Generate plan
    plan = AudioProductionService.generate_audio_plan(db_session, project.id)
    assert plan.status == "DRAFT"
    assert plan.plan_data["summary"]["total_audio_clips"] >= 3  # BGM, Ambience, VO
    assert project.status == "AUDIO_PLAN_GENERATED"

    # Verify created clips
    clips = db_session.query(AudioClip).filter(AudioClip.project_id == project.id).all()
    clip_types = {c.audio_type for c in clips}
    assert AudioType.BGM.value in clip_types
    assert AudioType.AMBIENCE.value in clip_types
    assert AudioType.VO.value in clip_types

    # 2. Approve plan
    approved_plan = AudioProductionService.approve_audio_plan(db_session, project.id)
    assert approved_plan.status == "APPROVED"
    assert project.status == "AUDIO_PLAN_APPROVED"


# ----------------- 5. Atomic Pre-Provider Claim & UsageLedger Reservation -----------------

def test_atomic_pre_provider_claim_and_cost_confirmation(db_session: Session):
    """Test that clip generation atomically claims SUBMITTING and creates in-flight UsageLedger reservation."""
    project = Project(
        id=uuid.uuid4(),
        title="Audio Claim Test",
        video_mode="STORY",
        status="AUDIO_PLAN_APPROVED",
        budget_limit=10.0,
    )
    db_session.add(project)
    db_session.flush()

    clip = AudioClip(
        id=uuid.uuid4(),
        project_id=project.id,
        name="Shot 1 VO",
        audio_type=AudioType.VO.value,
        source_type=AudioSourceType.GENERATED_AUDIO.value,
        generation_mode=AudioGenerationMode.SEPARATE_AUDIO.value,
        scope=AudioScope.SHOT.value,
        ducking_role=DuckingRole.FOREGROUND.value,
        prompt="Voiceover test",
        duration_seconds=4.0,
        status="PENDING",
    )
    db_session.add(clip)
    db_session.commit()

    # Generate clip
    ready_clip = AudioProductionService.generate_clip_audio(
        db=db_session,
        project_id=project.id,
        clip_id=clip.id,
        cost_authorized=True,
    )

    assert ready_clip.status == "READY"
    assert ready_clip.asset_id is not None

    # Check asset created in storage
    asset = db_session.get(Asset, ready_clip.asset_id)
    assert asset is not None
    assert asset.asset_type == "AUDIO"
    assert asset.file_size_bytes > 0

    # Verify UsageLedger was confirmed
    ledger = (
        db_session.query(UsageLedger)
        .filter(UsageLedger.project_id == project.id)
        .first()
    )
    assert ledger is not None
    assert ledger.cost_status == CostStatus.CONFIRMED
    assert ledger.actual_cost == 0.02


def test_concurrency_and_active_clip_conflict(db_session: Session):
    """Test that attempting to generate an active or submitting clip raises 409 Conflict."""
    project = Project(
        id=uuid.uuid4(),
        title="Audio Concurrency Test",
        video_mode="STORY",
        status="AUDIO_PLAN_APPROVED",
    )
    db_session.add(project)
    db_session.flush()

    clip = AudioClip(
        id=uuid.uuid4(),
        project_id=project.id,
        name="Submitting Clip",
        audio_type=AudioType.VO.value,
        source_type=AudioSourceType.GENERATED_AUDIO.value,
        generation_mode=AudioGenerationMode.SEPARATE_AUDIO.value,
        scope=AudioScope.SHOT.value,
        ducking_role=DuckingRole.FOREGROUND.value,
        status="SUBMITTING",
    )
    db_session.add(clip)
    db_session.commit()

    with pytest.raises(HTTPException) as exc:
        AudioProductionService.generate_clip_audio(
            db=db_session,
            project_id=project.id,
            clip_id=clip.id,
        )
    assert exc.value.status_code == 409
    assert "active generation in progress" in str(exc.value.detail)


def test_ambiguous_provider_exception_fails_closed(db_session: Session):
    """Test that ambiguous provider exceptions transition clip to RECONCILIATION_REQUIRED and preserve reservation."""
    project = Project(
        id=uuid.uuid4(),
        title="Ambiguous Audio Test",
        video_mode="STORY",
        status="AUDIO_PLAN_APPROVED",
    )
    db_session.add(project)
    db_session.flush()

    clip = AudioClip(
        id=uuid.uuid4(),
        project_id=project.id,
        name="Ambiguous Clip",
        audio_type=AudioType.BGM.value,
        source_type=AudioSourceType.GENERATED_AUDIO.value,
        generation_mode=AudioGenerationMode.SEPARATE_AUDIO.value,
        scope=AudioScope.PROJECT.value,
        ducking_role=DuckingRole.BACKGROUND.value,
        status="PENDING",
    )
    db_session.add(clip)
    db_session.commit()

    # Mock provider throwing transport error
    mock_prov = AudioProviderFactory.get_provider("mock_audio")
    with patch.object(mock_prov, "generate_audio", side_effect=ConnectionResetError("Socket reset")):
        with pytest.raises(HTTPException) as exc:
            AudioProductionService.generate_clip_audio(
                db=db_session,
                project_id=project.id,
                clip_id=clip.id,
            )
        assert exc.value.status_code == 502
        assert "RECONCILIATION_REQUIRED" in str(exc.value.detail)

    # Verify clip status is RECONCILIATION_REQUIRED
    db_session.refresh(clip)
    assert clip.status == "RECONCILIATION_REQUIRED"

    # Verify UsageLedger reservation is NOT zeroed out (preserved as ESTIMATED)
    ledger = (
        db_session.query(UsageLedger)
        .filter(UsageLedger.project_id == project.id)
        .first()
    )
    assert ledger is not None
    assert ledger.cost_status == CostStatus.ESTIMATED
    assert ledger.estimated_cost == 0.05


# ----------------- 6. Budget & Cost Authorization Safety -----------------

def test_hard_budget_limit_blocks_audio_generation(db_session: Session):
    """Verify that hard budget cap blocks audio generation dispatch with 402."""
    project = Project(
        id=uuid.uuid4(),
        title="Budget Capped Audio",
        video_mode="STORY",
        status="AUDIO_PLAN_APPROVED",
        budget_limit=0.01,  # limit is $0.01, clip cost is $0.02
    )
    db_session.add(project)
    db_session.flush()

    clip = AudioClip(
        id=uuid.uuid4(),
        project_id=project.id,
        name="Blocked VO",
        audio_type=AudioType.VO.value,
        source_type=AudioSourceType.GENERATED_AUDIO.value,
        generation_mode=AudioGenerationMode.SEPARATE_AUDIO.value,
        scope=AudioScope.SHOT.value,
        ducking_role=DuckingRole.FOREGROUND.value,
        status="PENDING",
    )
    db_session.add(clip)
    db_session.commit()

    with pytest.raises(HTTPException) as exc:
        AudioProductionService.generate_clip_audio(
            db=db_session,
            project_id=project.id,
            clip_id=clip.id,
        )
    assert exc.value.status_code == 402
    assert "hard budget limit exceeded" in str(exc.value.detail)


def test_auto_mode_requires_cost_authorization(db_session: Session):
    """Verify that in AUTO mode, audio generation requires explicit cost authorization."""
    project = Project(
        id=uuid.uuid4(),
        title="Auto Mode Audio",
        video_mode="STORY",
        status="AUDIO_PLAN_APPROVED",
        automation_mode="AUTO",
    )
    db_session.add(project)
    db_session.flush()

    clip = AudioClip(
        id=uuid.uuid4(),
        project_id=project.id,
        name="Auto VO",
        audio_type=AudioType.VO.value,
        source_type=AudioSourceType.GENERATED_AUDIO.value,
        generation_mode=AudioGenerationMode.SEPARATE_AUDIO.value,
        scope=AudioScope.SHOT.value,
        ducking_role=DuckingRole.FOREGROUND.value,
        status="PENDING",
    )
    db_session.add(clip)
    db_session.commit()

    with pytest.raises(HTTPException) as exc:
        AudioProductionService.generate_clip_audio(
            db=db_session,
            project_id=project.id,
            clip_id=clip.id,
            cost_authorized=False,
            actor="AUTO",
        )
    assert exc.value.status_code == 402
    assert "Explicit cost authorization required in AUTO mode" in str(exc.value.detail)


# ----------------- 7. Embedded Video Audio Non-Destructive Handling -----------------

def test_embedded_original_audio_preservation(db_session: Session):
    """Verify that embedded video audio clips are marked READY non-destructively without paid external calls."""
    project = Project(
        id=uuid.uuid4(),
        title="Embedded Audio Test",
        video_mode="STORY",
        status="AUDIO_PLAN_APPROVED",
    )
    db_session.add(project)
    db_session.flush()

    video_asset = Asset(
        id=uuid.uuid4(),
        project_id=project.id,
        name="Source Video Clip",
        original_filename="clip.mp4",
        asset_type="VIDEO",
        content_type="video/mp4",
        file_size_bytes=1000,
        checksum_sha256="abc123",
        storage_bucket="test-bucket",
        storage_key="test-key.mp4",
    )
    db_session.add(video_asset)
    db_session.flush()

    clip = AudioClip(
        id=uuid.uuid4(),
        project_id=project.id,
        video_asset_id=video_asset.id,
        name="Embedded Track",
        audio_type=AudioType.ORIGINAL_AUDIO.value,
        source_type=AudioSourceType.EMBEDDED_VIDEO_AUDIO.value,
        generation_mode=AudioGenerationMode.EMBEDDED_EXISTING.value,
        scope=AudioScope.VIDEO_CLIP.value,
        ducking_role=DuckingRole.EMBEDDED.value,
        status="PENDING",
    )
    db_session.add(clip)
    db_session.commit()

    ready_clip = AudioProductionService.generate_clip_audio(
        db=db_session,
        project_id=project.id,
        clip_id=clip.id,
    )
    assert ready_clip.status == "READY"

    # Verify no paid UsageLedger row was created
    ledgers = db_session.query(UsageLedger).filter(UsageLedger.project_id == project.id).all()
    assert len(ledgers) == 0


# ----------------- 8. Auto-Ducking Mixing Metadata -----------------

def test_auto_ducking_mixing_metadata(db_session: Session):
    """Verify compute_auto_mix calculates speech intervals and ducking attenuation."""
    project = Project(
        id=uuid.uuid4(),
        title="Ducking Mix Test",
        video_mode="STORY",
        status="AUDIO_IN_PROGRESS",
    )
    db_session.add(project)
    db_session.flush()

    plan = AudioPlan(
        id=uuid.uuid4(),
        project_id=project.id,
        status="DRAFT",
        version=1,
    )
    db_session.add(plan)

    # Add BGM (Background, start 0, duration 30)
    bgm = AudioClip(
        id=uuid.uuid4(),
        project_id=project.id,
        name="Score",
        audio_type=AudioType.BGM.value,
        source_type=AudioSourceType.GENERATED_AUDIO.value,
        generation_mode=AudioGenerationMode.SEPARATE_AUDIO.value,
        scope=AudioScope.PROJECT.value,
        ducking_role=DuckingRole.BACKGROUND.value,
        ducking_amount_db=-12.0,
        start_time=0.0,
        duration_seconds=30.0,
        status="READY",
    )
    db_session.add(bgm)

    # Add VO (Foreground, start 2.0, duration 5.0)
    vo = AudioClip(
        id=uuid.uuid4(),
        project_id=project.id,
        name="Dialogue",
        audio_type=AudioType.VO.value,
        source_type=AudioSourceType.GENERATED_AUDIO.value,
        generation_mode=AudioGenerationMode.SEPARATE_AUDIO.value,
        scope=AudioScope.SHOT.value,
        ducking_role=DuckingRole.FOREGROUND.value,
        ducking_amount_db=0.0,
        start_time=2.0,
        duration_seconds=5.0,
        status="READY",
    )
    db_session.add(vo)
    db_session.commit()

    mix = AudioProductionService.compute_auto_mix(db_session, project.id)
    assert len(mix["speech_intervals"]) == 1
    assert mix["speech_intervals"][0]["start"] == 2.0
    assert mix["speech_intervals"][0]["end"] == 7.0

    # Background track receives ducking attenuation
    bgm_track = next(t for t in mix["tracks"] if t["audio_type"] == "BGM")
    assert bgm_track["ducking_attenuation_db"] == -12.0


# ----------------- 9. Orchestrator Audio Stage Progression -----------------

def test_production_orchestrator_audio_workflow(db_session: Session):
    """Test end-to-end stage progression through orchestrator audio actions."""
    project = Project(
        id=uuid.uuid4(),
        title="Orchestrator Audio Workflow",
        video_mode="STORY",
        status="FINAL_REVIEW",
    )
    db_session.add(project)
    db_session.commit()

    # 1. GENERATE_AUDIO_PLAN
    resp1 = ProductionOrchestrator.execute_action(
        db=db_session,
        project_id=project.id,
        action="GENERATE_AUDIO_PLAN",
    )
    assert resp1.to_stage == "AUDIO_PLAN_GENERATED"
    assert project.status == "AUDIO_PLAN_GENERATED"

    # 2. APPROVE_AUDIO_PLAN
    resp2 = ProductionOrchestrator.execute_action(
        db=db_session,
        project_id=project.id,
        action="APPROVE_AUDIO_PLAN",
    )
    assert resp2.to_stage == "AUDIO_PLAN_APPROVED"
    assert project.status == "AUDIO_PLAN_APPROVED"

    # 3. START_AUDIO_GENERATION
    resp3 = ProductionOrchestrator.execute_action(
        db=db_session,
        project_id=project.id,
        action="START_AUDIO_GENERATION",
        parameters={"cost_authorized": True},
    )
    assert resp3.to_stage == "AUDIO_IN_PROGRESS"
    assert project.status == "AUDIO_IN_PROGRESS"

    # 4. AUTO_MIX_AUDIO
    resp4 = ProductionOrchestrator.execute_action(
        db=db_session,
        project_id=project.id,
        action="AUTO_MIX_AUDIO",
    )
    assert resp4.to_stage == "AUDIO_MIX_READY"
    assert project.status == "AUDIO_MIX_READY"

    # 5. APPROVE_AUDIO_MIX
    resp5 = ProductionOrchestrator.execute_action(
        db=db_session,
        project_id=project.id,
        action="APPROVE_AUDIO_MIX",
    )
    assert resp5.to_stage == "AUDIO_APPROVED"
    assert project.status == "AUDIO_APPROVED"

    # 6. PROCEED_TO_ASSEMBLY
    resp6 = ProductionOrchestrator.execute_action(
        db=db_session,
        project_id=project.id,
        action="PROCEED_TO_ASSEMBLY",
    )
    assert resp6.to_stage == "READY_FOR_ASSEMBLY"
    assert project.status == "READY_FOR_ASSEMBLY"


# ----------------- 10. Direct PATCH Bypass Prevention -----------------

def test_patch_project_status_bypass_prevention(client: TestClient, db_session: Session):
    """Verify that attempting to patch project status directly is blocked with 400."""
    project = Project(
        id=uuid.uuid4(),
        title="Status Patch Test",
        video_mode="STORY",
        status="DRAFT",
    )
    db_session.add(project)
    db_session.commit()

    resp = client.patch(
        f"/api/v1/projects/{project.id}",
        json={"status": "AUDIO_APPROVED"},
    )
    assert resp.status_code == 400
    assert "Direct modification of project status via generic PATCH /projects is disallowed" in resp.json()["detail"]


# ----------------- 11. Review Fix 1: Audio History / Version Retention -----------------

def test_audio_history_retention_and_restoration(db_session: Session, client: TestClient):
    """Verify full history retention for AudioPlan and AudioClip without silent overwrite."""
    project = Project(
        id=uuid.uuid4(),
        title="History Retention Project",
        video_mode="STORY",
        status="FINAL_REVIEW",
    )
    db_session.add(project)
    db_session.commit()

    # 1. Generate initial AudioPlan
    plan1 = AudioProductionService.generate_audio_plan(db_session, project.id)
    assert plan1.version == 1
    versions = db_session.query(AudioPlanVersion).filter(AudioPlanVersion.project_id == project.id).all()
    assert len(versions) == 1
    assert versions[0].version_number == 1
    assert versions[0].action == "CREATE_PLAN"

    # 2. Approve AudioPlan
    AudioProductionService.approve_audio_plan(db_session, project.id)
    versions_after_approve = db_session.query(AudioPlanVersion).filter(AudioPlanVersion.project_id == project.id).all()
    assert len(versions_after_approve) == 2
    assert any(v.action == "APPROVE_PLAN" for v in versions_after_approve)

    # 3. Regenerate / modify plan -> new version
    plan2 = AudioProductionService.generate_audio_plan(db_session, project.id)
    assert plan2.version == 2
    versions_after_regen = db_session.query(AudioPlanVersion).filter(AudioPlanVersion.project_id == project.id).all()
    assert len(versions_after_regen) >= 3

    # 4. API History endpoint bounded retrieval
    resp = client.get(f"/api/v1/projects/{project.id}/audio/plan/history?limit=10&offset=0")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert data["total"] >= 3
    assert len(data["items"]) >= 3
    # Check reverse chronological ordering
    assert data["items"][0]["version_number"] >= data["items"][1]["version_number"]

    # 5. Restore prior plan version
    restore_resp = client.post(f"/api/v1/projects/{project.id}/audio/plan/restore/1")
    assert restore_resp.status_code == 200
    restored_plan = restore_resp.json()
    assert restored_plan["version"] == 3  # increments version upon restore

    # 6. AudioClip revision history tracking
    clips = db_session.query(AudioClip).filter(AudioClip.project_id == project.id).all()
    assert len(clips) > 0
    test_clip = clips[0]

    # Verify initial creation history exists
    clip_hist = db_session.query(AudioClipHistory).filter(AudioClipHistory.clip_id == test_clip.id).all()
    assert len(clip_hist) >= 1
    assert clip_hist[0].action == "CREATE"

    # Update clip via PATCH
    patch_resp = client.patch(
        f"/api/v1/projects/{project.id}/audio/clips/{test_clip.id}",
        json={"volume": 0.45, "ducking_amount_db": -15.0, "reason": "Adjust volume for mix"},
    )
    assert patch_resp.status_code == 200
    clip_hist_after_patch = (
        db_session.query(AudioClipHistory)
        .filter(AudioClipHistory.clip_id == test_clip.id)
        .order_by(AudioClipHistory.version_number.desc())
        .all()
    )
    assert len(clip_hist_after_patch) >= 2
    assert clip_hist_after_patch[0].volume == 0.45
    assert clip_hist_after_patch[0].action == "UPDATE"
    assert clip_hist_after_patch[0].change_reason == "Adjust volume for mix"

    # History endpoint for clip
    clip_hist_resp = client.get(f"/api/v1/projects/{project.id}/audio/clips/{test_clip.id}/history?limit=5")
    assert clip_hist_resp.status_code == 200
    assert clip_hist_resp.json()["total"] >= 2


# ----------------- 12. Review Fix 2: Lock Safety -----------------

def test_lock_safety_isolated_unlock_and_rejection(db_session: Session, client: TestClient):
    """Verify that unlocking must be an explicit isolated operation and cannot be combined with modifications."""
    project = Project(
        id=uuid.uuid4(),
        title="Lock Safety Project",
        video_mode="STORY",
        status="AUDIO_IN_PROGRESS",
    )
    db_session.add(project)
    db_session.flush()

    clip = AudioClip(
        id=uuid.uuid4(),
        project_id=project.id,
        name="Locked Test Clip",
        audio_type=AudioType.VO.value,
        source_type=AudioSourceType.GENERATED_AUDIO.value,
        generation_mode=AudioGenerationMode.SEPARATE_AUDIO.value,
        scope=AudioScope.SHOT.value,
        ducking_role=DuckingRole.FOREGROUND.value,
        volume=1.0,
        is_locked=False,
        status="PENDING",
    )
    db_session.add(clip)
    db_session.commit()

    # 1. Lock clip via dedicated lock endpoint
    lock_resp = client.post(
        f"/api/v1/projects/{project.id}/audio/clips/{clip.id}/lock",
        json={"actor": "LEAD_EDITOR", "reason": "Voice approved by client"},
    )
    assert lock_resp.status_code == 200
    assert lock_resp.json()["is_locked"] is True

    # 2. Attempt to modify fields on locked clip -> 423 Locked
    edit_resp = client.patch(
        f"/api/v1/projects/{project.id}/audio/clips/{clip.id}",
        json={"volume": 0.2},
    )
    assert edit_resp.status_code == 423
    assert "locked" in edit_resp.json()["detail"].lower()

    # 3. CRITICAL: Attempt to send is_locked=false TOGETHER with other field modifications -> 423 / 400 Fail-Closed!
    exploit_resp = client.patch(
        f"/api/v1/projects/{project.id}/audio/clips/{clip.id}",
        json={"is_locked": False, "volume": 0.2, "name": "Hacked Name"},
    )
    assert exploit_resp.status_code == 423
    assert "Cannot modify fields" in exploit_resp.json()["detail"]
    assert "Unlocking must be an explicit isolated operation" in exploit_resp.json()["detail"]

    # Verify clip is STILL locked and unchanged in DB
    db_session.refresh(clip)
    assert clip.is_locked is True
    assert clip.volume == 1.0

    # 4. Isolated explicit unlock via dedicated unlock endpoint
    unlock_resp = client.post(
        f"/api/v1/projects/{project.id}/audio/clips/{clip.id}/unlock",
        json={"actor": "LEAD_EDITOR", "reason": "Client requested change"},
    )
    assert unlock_resp.status_code == 200
    assert unlock_resp.json()["is_locked"] is False

    # Verify audit history captured the lock and unlock actions
    hist = (
        db_session.query(AudioClipHistory)
        .filter(AudioClipHistory.clip_id == clip.id)
        .order_by(AudioClipHistory.version_number.desc())
        .all()
    )
    actions = [h.action for h in hist]
    assert "LOCK" in actions
    assert "UNLOCK" in actions

    # 5. Now modification succeeds on unlocked clip
    valid_edit_resp = client.patch(
        f"/api/v1/projects/{project.id}/audio/clips/{clip.id}",
        json={"volume": 0.75},
    )
    assert valid_edit_resp.status_code == 200
    assert valid_edit_resp.json()["volume"] == 0.75


# ----------------- 13. Review Fix 3: Bounded Audio Listing -----------------

def test_bounded_audio_listing_pagination(db_session: Session, client: TestClient):
    """Verify that GET /projects/{project_id}/audio/clips is bounded with limit/offset."""
    project = Project(
        id=uuid.uuid4(),
        title="Pagination Project",
        video_mode="STORY",
        status="AUDIO_PLAN_APPROVED",
    )
    db_session.add(project)
    db_session.flush()

    # Create 12 clips
    for i in range(12):
        c = AudioClip(
            id=uuid.uuid4(),
            project_id=project.id,
            name=f"Clip {i}",
            audio_type=AudioType.SFX.value if i % 2 == 0 else AudioType.VO.value,
            source_type=AudioSourceType.GENERATED_AUDIO.value,
            generation_mode=AudioGenerationMode.SEPARATE_AUDIO.value,
            scope=AudioScope.SHOT.value,
            ducking_role=DuckingRole.EVENT.value,
            start_time=float(i * 2),
            status="PENDING",
        )
        db_session.add(c)
    db_session.commit()

    # Page 1: limit 5, offset 0
    resp_p1 = client.get(f"/api/v1/projects/{project.id}/audio/clips?limit=5&offset=0")
    assert resp_p1.status_code == 200
    p1_data = resp_p1.json()
    assert p1_data["total"] == 12
    assert len(p1_data["items"]) == 5
    assert p1_data["limit"] == 5
    assert p1_data["offset"] == 0
    p1_ids = [item["id"] for item in p1_data["items"]]

    # Page 2: limit 5, offset 5
    resp_p2 = client.get(f"/api/v1/projects/{project.id}/audio/clips?limit=5&offset=5")
    assert resp_p2.status_code == 200
    p2_data = resp_p2.json()
    assert len(p2_data["items"]) == 5
    p2_ids = [item["id"] for item in p2_data["items"]]

    # Ensure no overlap between pages
    assert set(p1_ids).isdisjoint(set(p2_ids))

    # Page 3: limit 5, offset 10
    resp_p3 = client.get(f"/api/v1/projects/{project.id}/audio/clips?limit=5&offset=10")
    assert resp_p3.status_code == 200
    p3_data = resp_p3.json()
    assert len(p3_data["items"]) == 2

    # Filtering by audio_type
    filter_resp = client.get(f"/api/v1/projects/{project.id}/audio/clips?audio_type=SFX")
    assert filter_resp.status_code == 200
    assert filter_resp.json()["total"] == 6


# ----------------- 14. Review Fix 4: Embedded Audio Truth -----------------

def test_embedded_audio_truth_verification(db_session: Session, client: TestClient):
    """Verify that ORIGINAL_AUDIO is never invented from image/non-video assets, and truthful metadata is preserved."""
    project = Project(
        id=uuid.uuid4(),
        title="Embedded Truth Project",
        video_mode="STORY",
        status="VIDEO_APPROVED",
    )
    db_session.add(project)
    db_session.flush()

    scene = Scene(
        id=uuid.uuid4(),
        project_id=project.id,
        scene_number=1,
        heading="INT. TRUTH LAB",
    )
    db_session.add(scene)
    db_session.flush()

    # Asset 1: IMAGE (keyframe) -> MUST NOT produce ORIGINAL_AUDIO clip
    image_asset = Asset(
        id=uuid.uuid4(),
        project_id=project.id,
        name="Keyframe Image",
        original_filename="keyframe.png",
        asset_type="IMAGE",
        content_type="image/png",
        file_size_bytes=50000,
        checksum_sha256="img_hash",
        storage_bucket="bucket",
        storage_key="keyframe.png",
    )
    db_session.add(image_asset)

    # Asset 2: VIDEO without audio
    video_no_audio = Asset(
        id=uuid.uuid4(),
        project_id=project.id,
        name="Silent Video",
        original_filename="silent.mp4",
        asset_type="VIDEO",
        content_type="video/mp4",
        file_size_bytes=100000,
        checksum_sha256="silent_hash",
        storage_bucket="bucket",
        storage_key="silent.mp4",
    )
    db_session.add(video_no_audio)

    # Asset 3: VIDEO with verified audio stream
    video_with_audio = Asset(
        id=uuid.uuid4(),
        project_id=project.id,
        name="Audio Video",
        original_filename="audio.mp4",
        asset_type="VIDEO",
        content_type="video/mp4",
        file_size_bytes=200000,
        checksum_sha256="audio_hash",
        storage_bucket="bucket",
        storage_key="audio.mp4",
    )
    db_session.add(video_with_audio)

    # Asset 4: VIDEO with unknown audio metadata
    video_unknown_audio = Asset(
        id=uuid.uuid4(),
        project_id=project.id,
        name="Unknown Audio Video",
        original_filename="unknown.mp4",
        asset_type="VIDEO",
        content_type="video/mp4",
        file_size_bytes=150000,
        checksum_sha256="unknown_hash",
        storage_bucket="bucket",
        storage_key="unknown.mp4",
    )
    db_session.add(video_unknown_audio)
    db_session.flush()

    # Shot 1: references image asset
    shot1 = Shot(
        id=uuid.uuid4(),
        scene_id=scene.id,
        shot_number=1,
        shot_type="AI_GENERATED",
        source_asset_id=image_asset.id,
        duration_seconds=4.0,
    )
    db_session.add(shot1)

    # Shot 2: references silent video asset
    shot2 = Shot(
        id=uuid.uuid4(),
        scene_id=scene.id,
        shot_number=2,
        shot_type="AI_GENERATED",
        source_asset_id=video_no_audio.id,
        source_metadata={"has_audio": False, "audio_channels": 0},
        duration_seconds=4.0,
    )
    db_session.add(shot2)

    # Shot 3: references video with verified audio
    shot3 = Shot(
        id=uuid.uuid4(),
        scene_id=scene.id,
        shot_number=3,
        shot_type="AI_GENERATED",
        source_asset_id=video_with_audio.id,
        source_metadata={"has_audio": True, "audio_channels": 2, "audio_stream_count": 1},
        duration_seconds=4.0,
    )
    db_session.add(shot3)

    # Shot 4: references video with unknown audio metadata
    shot4 = Shot(
        id=uuid.uuid4(),
        scene_id=scene.id,
        shot_number=4,
        shot_type="AI_GENERATED",
        source_asset_id=video_unknown_audio.id,
        duration_seconds=4.0,
    )
    db_session.add(shot4)
    db_session.commit()

    # Generate plan
    plan = AudioProductionService.generate_audio_plan(db_session, project.id)

    # Check clips created
    all_clips = db_session.query(AudioClip).filter(AudioClip.project_id == project.id).all()
    orig_clips = [c for c in all_clips if c.audio_type == AudioType.ORIGINAL_AUDIO.value]

    # Verify Shot 1 (Image) did NOT produce any ORIGINAL_AUDIO clip
    assert not any(c.shot_id == shot1.id for c in orig_clips), "Image asset must never invent ORIGINAL_AUDIO"

    # Verify Shot 2 (Silent Video) did NOT produce any ORIGINAL_AUDIO clip
    assert not any(c.shot_id == shot2.id for c in orig_clips), "Silent video must truthfully omit ORIGINAL_AUDIO"

    # Verify Shot 3 (Verified Audio) produced a READY clip with VERIFIED presence
    shot3_orig = next(c for c in orig_clips if c.shot_id == shot3.id)
    assert shot3_orig.status == "READY"
    assert shot3_orig.provenance["audio_presence"] == "VERIFIED"

    # Verify Shot 4 (Unknown Audio) produced an UNKNOWN clip truthfully
    shot4_orig = next(c for c in orig_clips if c.shot_id == shot4.id)
    assert shot4_orig.status == "UNKNOWN"
    assert shot4_orig.provenance["audio_presence"] == "UNKNOWN"

    # Attempting to generate on an UNKNOWN clip without verified audio probe raises 400
    with pytest.raises(HTTPException) as exc:
        AudioProductionService.generate_clip_audio(
            db=db_session,
            project_id=project.id,
            clip_id=shot4_orig.id,
        )
    assert exc.value.status_code == 400
    assert "audio stream probe required" in str(exc.value.detail)


# ----------------- 15. Review Fix: Canonical Provider-Capability Routing & WITH_VIDEO Safety -----------------

from app.providers.base import IVideoGenerationProviderAdapter, VideoGenerationParams, ProviderJobResult
from app.providers.factory import ProviderFactory

class MockNativeAudioVideoAdapter(IVideoGenerationProviderAdapter):
    @property
    def provider_id(self) -> str:
        return "mock_native_video"

    async def submit_generation_job(self, params: VideoGenerationParams) -> ProviderJobResult:
        return ProviderJobResult(provider_job_id="job123", status="COMPLETED", video_url="http://vid.mp4")

    async def check_job_status(self, provider_job_id: str) -> ProviderJobResult:
        return ProviderJobResult(provider_job_id=provider_job_id, status="COMPLETED")

    async def cancel_job(self, provider_job_id: str) -> bool:
        return True

    def validate_config(self, config: dict) -> bool:
        return True

    @property
    def supports_native_audio(self) -> bool:
        return True

    @property
    def supports_dialogue(self) -> bool:
        return True


def test_provider_capability_routing_dialogue_and_vo(db_session: Session):
    """Test A & B: Prove Dialogue recommends WITH_VIDEO when provider supports native audio, and SEPARATE_AUDIO when provider lacks capability."""
    # Register mock native video provider
    ProviderFactory.register("mock_native_video", MockNativeAudioVideoAdapter)

    project1 = Project(id=uuid.uuid4(), title="Native Audio Project", video_mode="STORY")
    db_session.add(project1)
    db_session.flush()

    scene1 = Scene(id=uuid.uuid4(), project_id=project1.id, scene_number=1, heading="INT. SCENE")
    db_session.add(scene1)
    db_session.flush()

    shot1 = Shot(
        id=uuid.uuid4(),
        scene_id=scene1.id,
        shot_number=1,
        shot_type="AI_GENERATED",
        source_metadata={"is_dialogue": True, "dialogue_text": "Hello world native dialogue!", "speaker_name": "Hero"},
        duration_seconds=4.0,
    )
    db_session.add(shot1)
    db_session.commit()

    # Test A: Provider with native audio capability -> Dialogue receives WITH_VIDEO
    plan1 = AudioProductionService.generate_audio_plan(db_session, project1.id, video_provider_name="mock_native_video")
    clips1 = db_session.query(AudioClip).filter(AudioClip.project_id == project1.id).all()
    dialogue_clip1 = next(c for c in clips1 if c.audio_type == AudioType.DIALOGUE.value)
    assert dialogue_clip1.generation_mode == AudioGenerationMode.WITH_VIDEO.value

    # Test B: Provider without native audio capability (default Vidu) -> Dialogue receives SEPARATE_AUDIO
    project2 = Project(id=uuid.uuid4(), title="Non-Native Audio Project", video_mode="STORY")
    db_session.add(project2)
    db_session.flush()

    scene2 = Scene(id=uuid.uuid4(), project_id=project2.id, scene_number=1, heading="INT. SCENE 2")
    db_session.add(scene2)
    db_session.flush()

    shot2 = Shot(
        id=uuid.uuid4(),
        scene_id=scene2.id,
        shot_number=1,
        shot_type="AI_GENERATED",
        source_metadata={"is_dialogue": True, "dialogue_text": "Hello world separate dialogue!", "speaker_name": "Hero"},
        duration_seconds=4.0,
    )
    db_session.add(shot2)
    db_session.commit()

    plan2 = AudioProductionService.generate_audio_plan(db_session, project2.id, video_provider_name="vidu")
    clips2 = db_session.query(AudioClip).filter(AudioClip.project_id == project2.id).all()
    dialogue_clip2 = next(c for c in clips2 if c.audio_type == AudioType.DIALOGUE.value)
    assert dialogue_clip2.generation_mode == AudioGenerationMode.SEPARATE_AUDIO.value


def test_with_video_generation_mode_safety_and_blocker(db_session: Session):
    """Test C, D & E: Prove WITH_VIDEO clip NEVER calls AudioProvider, fails closed with blocker string, and enforces cost authorization."""
    project = Project(
        id=uuid.uuid4(),
        title="WITH_VIDEO Safety Project",
        video_mode="STORY",
        status="AUDIO_PLAN_APPROVED",
        automation_mode="AUTO",
    )
    db_session.add(project)
    db_session.flush()

    clip = AudioClip(
        id=uuid.uuid4(),
        project_id=project.id,
        name="Native Dialogue Clip",
        audio_type=AudioType.DIALOGUE.value,
        source_type=AudioSourceType.GENERATED_AUDIO.value,
        generation_mode=AudioGenerationMode.WITH_VIDEO.value,
        scope=AudioScope.SHOT.value,
        ducking_role=DuckingRole.FOREGROUND.value,
        status="PENDING",
    )
    db_session.add(clip)
    db_session.commit()

    # Test E: Cost authorization required before any paid video regeneration attempt
    with pytest.raises(HTTPException) as exc_e:
        AudioProductionService.generate_clip_audio(
            db=db_session,
            project_id=project.id,
            clip_id=clip.id,
            cost_authorized=False,
            actor="AUTO",
        )
    assert exc_e.value.status_code == 402
    assert "cost authorization required" in str(exc_e.value.detail).lower()

    # Test C & D: Generate on WITH_VIDEO clip with cost_authorized=True MUST NEVER call AudioProvider and MUST fail closed with WITH_VIDEO_REQUIRES_VIDEO_REGENERATION
    with patch("app.providers.audio.factory.AudioProviderFactory.get_provider") as mock_get_audio_provider:
        with pytest.raises(HTTPException) as exc_d:
            AudioProductionService.generate_clip_audio(
                db=db_session,
                project_id=project.id,
                clip_id=clip.id,
                cost_authorized=True,
                actor="USER",
            )
        assert exc_d.value.status_code == 422
        assert "WITH_VIDEO_REQUIRES_VIDEO_REGENERATION" in exc_d.value.detail
        # Prove AudioProvider was NEVER called!
        assert mock_get_audio_provider.call_count == 0
