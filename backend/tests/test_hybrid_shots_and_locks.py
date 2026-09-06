import uuid
from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models.project import Project
from app.models.story import Story
from app.models.scene import Scene
from app.models.shot import Shot
from app.models.asset import Asset
from app.models.asset_lock import AssetLock
from app.services.lock_machine import LockMachineService
from app.services.hybrid_shot import HybridShotService
from app.services.video_modes import (
    validate_video_mode,
    validate_shot_type,
    validate_lock_target,
    ALLOWED_SHOT_TYPES,
    CORE_V1_VIDEO_MODES,
    ARCHITECTURE_READY_VIDEO_MODES,
)
from app.services.job_dispatch import JobDispatchService
from app.providers.base import IVideoGenerationProviderAdapter, ProviderJobResult


@pytest.fixture
def client(db_session: Session):
    from app.db.session import get_db

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def sample_project(db_session: Session) -> Project:
    project = Project(
        id=uuid.uuid4(),
        title="Test Production Project",
        video_mode="STORY",
        purpose="MARKETING",
        target_platform="YOUTUBE",
        target_duration_seconds=60.0,
        preferred_aspect_ratio="16:9",
        mode_config={"preset": "cinematic_trailer"},
        default_config={"fps": 24, "resolution": "1080p"},
        status="DRAFT",
    )
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    return project


@pytest.fixture
def foreign_project(db_session: Session) -> Project:
    project = Project(
        id=uuid.uuid4(),
        title="Foreign Unrelated Project",
        video_mode="STORY",
        status="DRAFT",
    )
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    return project


@pytest.fixture
def sample_asset(db_session: Session, sample_project: Project) -> Asset:
    asset = Asset(
        id=uuid.uuid4(),
        project_id=sample_project.id,
        name="test_footage.mp4",
        original_filename="test_footage.mp4",
        asset_type="VIDEO",
        content_type="video/mp4",
        file_size_bytes=102400,
        checksum_sha256="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        storage_bucket="test-bucket",
        storage_key=f"projects/{sample_project.id}/videos/test_footage.mp4",
        is_locked=False,
    )
    db_session.add(asset)
    db_session.commit()
    db_session.refresh(asset)
    return asset


@pytest.fixture
def foreign_asset(db_session: Session, foreign_project: Project) -> Asset:
    asset = Asset(
        id=uuid.uuid4(),
        project_id=foreign_project.id,
        name="foreign_clip.mp4",
        original_filename="foreign_clip.mp4",
        asset_type="VIDEO",
        content_type="video/mp4",
        file_size_bytes=204800,
        checksum_sha256="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        storage_bucket="foreign-bucket",
        storage_key=f"projects/{foreign_project.id}/videos/foreign_clip.mp4",
        is_locked=False,
    )
    db_session.add(asset)
    db_session.commit()
    db_session.refresh(asset)
    return asset


@pytest.fixture
def sample_scene(db_session: Session, sample_project: Project) -> Scene:
    scene = Scene(
        id=uuid.uuid4(),
        project_id=sample_project.id,
        story_id=None,
        scene_number=1,
        heading="EXT. CITY STREET - DAY",
        description="Busy street with morning commuters.",
        scene_config={"aspect_ratio": "16:9", "color_grade": "cool_blue"},
        is_locked=False,
    )
    db_session.add(scene)
    db_session.commit()
    db_session.refresh(scene)
    return scene


# ==============================================================================
# 1. SCOPE A — HYBRID SHOT ENGINE & ASSET OWNERSHIP TESTS
# ==============================================================================

def test_all_hybrid_source_types_validate_correctly(client, sample_scene, sample_asset):
    for shot_type in ALLOWED_SHOT_TYPES:
        payload = {
            "shot_number": 1,
            "shot_type": shot_type,
            "visual_prompt": f"Test prompt for {shot_type}",
            "duration_seconds": 4.0,
        }
        if shot_type in ("IMPORTED_VIDEO", "IMPORTED_IMAGE", "RECORDED_FOOTAGE", "STOCK_ASSET", "MIXED"):
            payload["source_asset_id"] = str(sample_asset.id)
            payload["source_metadata"] = {"in_point_ms": 0, "out_point_ms": 4000}

        resp = client.post(f"/api/v1/scenes/{sample_scene.id}/shots", json=payload)
        assert resp.status_code == 201, f"Failed for {shot_type}: {resp.text}"
        data = resp.json()
        assert data["shot_type"] == shot_type
        if "source_asset_id" in payload:
            assert data["source_asset_id"] == str(sample_asset.id)
            assert data["source_metadata"]["in_point_ms"] == 0


def test_invalid_shot_source_type_rejected(client, sample_scene):
    resp = client.post(
        f"/api/v1/scenes/{sample_scene.id}/shots",
        json={"shot_number": 1, "shot_type": "HAND_DRAWN_ANIMATION"},
    )
    assert resp.status_code == 400
    assert "Unsupported shot type" in resp.json()["detail"]


def test_imported_asset_project_ownership_validation(client, sample_scene, foreign_asset, sample_asset):
    # Foreign asset from another project must fail closed with 400
    resp = client.post(
        f"/api/v1/scenes/{sample_scene.id}/shots",
        json={
            "shot_number": 1,
            "shot_type": "IMPORTED_VIDEO",
            "source_asset_id": str(foreign_asset.id),
        },
    )
    assert resp.status_code == 400
    assert "belongs to Project" in resp.json()["detail"]

    # Same project asset succeeds
    resp_ok = client.post(
        f"/api/v1/scenes/{sample_scene.id}/shots",
        json={
            "shot_number": 1,
            "shot_type": "IMPORTED_VIDEO",
            "source_asset_id": str(sample_asset.id),
        },
    )
    assert resp_ok.status_code == 201


def test_ai_generated_shot_dispatches_only_through_generation_queue(db_session, sample_scene, monkeypatch):
    shot = Shot(
        id=uuid.uuid4(),
        scene_id=sample_scene.id,
        shot_number=1,
        shot_type="AI_GENERATED",
        video_prompt="A dramatic cinematic sunset over the skyline",
        duration_seconds=5.0,
        is_locked=False,
    )
    db_session.add(shot)
    db_session.commit()

    # Dispatch via WP007 JobDispatchService boundary
    job = JobDispatchService.create_and_dispatch_job(
        db=db_session,
        shot_id=shot.id,
        provider_name="vidu",
    )
    assert job is not None
    assert job.shot_id == shot.id
    assert job.status == "PENDING"
    assert job.payload["prompt"] == shot.video_prompt


def test_non_generatable_shot_rejected_from_queue_dispatch(db_session, sample_scene, sample_asset):
    shot = Shot(
        id=uuid.uuid4(),
        scene_id=sample_scene.id,
        shot_number=1,
        shot_type="IMPORTED_VIDEO",
        source_asset_id=sample_asset.id,
        duration_seconds=4.0,
        is_locked=False,
    )
    db_session.add(shot)
    db_session.commit()

    with pytest.raises(Exception) as exc_info:
        JobDispatchService.create_and_dispatch_job(
            db=db_session,
            shot_id=shot.id,
            provider_name="vidu",
        )
    assert "Cannot dispatch generation job for shot type 'IMPORTED_VIDEO'" in str(exc_info.value)


def test_no_vidu_specific_imports_in_core_shot_services():
    import sys
    # Verify app.services.hybrid_shot, lock_machine, and video_modes do NOT import vidu
    import app.services.hybrid_shot as hs
    import app.services.lock_machine as lm
    import app.services.video_modes as vm

    for mod in (hs, lm, vm):
        content = open(mod.__file__, "r", encoding="utf-8").read()
        assert "app.providers.vidu" not in content
        assert "ViduProviderAdapter" not in content


# ==============================================================================
# 2. SCOPE B — ASSET LOCK MACHINE & FAIL-CLOSED CHECKS
# ==============================================================================

def test_lock_unlock_state_transitions_and_audit(client, db_session, sample_project, sample_scene):
    shot = Shot(
        id=uuid.uuid4(),
        scene_id=sample_scene.id,
        shot_number=1,
        shot_type="AI_GENERATED",
        is_locked=False,
    )
    db_session.add(shot)
    db_session.commit()

    # 1. Lock shot explicitly
    lock_resp = client.post(
        "/api/v1/locks/lock",
        json={
            "project_id": str(sample_project.id),
            "entity_type": "SHOT",
            "entity_id": str(shot.id),
            "actor": "user_lead_editor",
            "reason": "Director approved this shot framing",
        },
    )
    assert lock_resp.status_code == 200
    lock_data = lock_resp.json()
    assert lock_data["is_locked"] is True
    assert lock_data["locked_by"] == "user_lead_editor"
    assert lock_data["lock_reason"] == "Director approved this shot framing"
    assert lock_data["locked_at"] is not None

    # Underlying shot entity reflects locked state
    db_session.refresh(shot)
    assert shot.is_locked is True

    # 2. Query lock endpoint
    get_resp = client.get(f"/api/v1/locks/SHOT/{shot.id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["is_locked"] is True

    # 3. Unlock shot explicitly
    unlock_resp = client.post(
        "/api/v1/locks/unlock",
        json={
            "project_id": str(sample_project.id),
            "entity_type": "SHOT",
            "entity_id": str(shot.id),
            "actor": "user_director",
            "reason": "Requested slight camera re-frame",
        },
    )
    assert unlock_resp.status_code == 200
    unlock_data = unlock_resp.json()
    assert unlock_data["is_locked"] is False
    assert unlock_data["unlocked_by"] == "user_director"
    assert unlock_data["unlock_reason"] == "Requested slight camera re-frame"
    assert unlock_data["unlocked_at"] is not None

    db_session.refresh(shot)
    assert shot.is_locked is False


def test_locked_mutation_rejection(client, db_session, sample_project, sample_scene):
    shot = Shot(
        id=uuid.uuid4(),
        scene_id=sample_scene.id,
        shot_number=1,
        shot_type="AI_GENERATED",
        action="Pilot looks left",
        is_locked=False,
    )
    db_session.add(shot)
    db_session.commit()

    # Lock the shot
    LockMachineService.lock(
        db=db_session,
        project_id=sample_project.id,
        entity_type="SHOT",
        entity_id=shot.id,
        actor="system",
    )

    # Attempt to mutate locked shot via PATCH -> must fail closed with 409
    resp = client.patch(
        f"/api/v1/shots/{shot.id}",
        json={"action": "Pilot looks right"},
    )
    assert resp.status_code == 409
    assert "Cannot mutate locked SHOT" in resp.json()["detail"]


def test_locked_regeneration_rejection(db_session, sample_project, sample_scene):
    shot = Shot(
        id=uuid.uuid4(),
        scene_id=sample_scene.id,
        shot_number=1,
        shot_type="AI_GENERATED",
        video_prompt="A spaceship landing on Mars",
        duration_seconds=4.0,
        is_locked=True,
    )
    db_session.add(shot)
    db_session.commit()

    # LockMachine lock record
    LockMachineService.lock(
        db=db_session,
        project_id=sample_project.id,
        entity_type="SHOT",
        entity_id=shot.id,
        actor="producer",
    )

    with pytest.raises(Exception) as exc_info:
        JobDispatchService.create_and_dispatch_job(
            db=db_session,
            shot_id=shot.id,
            provider_name="vidu",
        )
    assert "Cannot regenerate locked Shot" in str(exc_info.value)


def test_parent_locked_scene_fails_closed_for_shot_mutations(client, db_session, sample_project, sample_scene):
    shot = Shot(
        id=uuid.uuid4(),
        scene_id=sample_scene.id,
        shot_number=1,
        shot_type="AI_GENERATED",
        is_locked=False,
    )
    db_session.add(shot)
    db_session.commit()

    # Lock the parent Scene
    LockMachineService.lock(
        db=db_session,
        project_id=sample_project.id,
        entity_type="SCENE",
        entity_id=sample_scene.id,
        actor="lead_editor",
    )

    # Attempting to mutate shot under locked scene must fail closed (409)
    resp = client.patch(
        f"/api/v1/shots/{shot.id}",
        json={"duration_seconds": 6.0},
    )
    assert resp.status_code == 409
    assert "parent SCENE" in resp.json()["detail"]

    # Attempting to add a new shot under locked scene must fail closed (409)
    resp_create = client.post(
        f"/api/v1/scenes/{sample_scene.id}/shots",
        json={"shot_number": 2, "shot_type": "AI_GENERATED"},
    )
    assert resp_create.status_code == 409
    assert "locked" in resp_create.json()["detail"]


# ==============================================================================
# 3. SCOPE C — BASE VIDEO MODES & CONFIG INHERITANCE TESTS
# ==============================================================================

def test_project_core_v1_video_modes_validation(client):
    for mode in CORE_V1_VIDEO_MODES:
        resp = client.post(
            "/api/v1/projects",
            json={"title": f"{mode} Project", "video_mode": mode},
        )
        assert resp.status_code == 201
        assert resp.json()["video_mode"] == mode


def test_architecture_ready_future_modes_rejected_in_core_v1(client):
    for mode in ARCHITECTURE_READY_VIDEO_MODES:
        resp = client.post(
            "/api/v1/projects",
            json={"title": f"{mode} Project", "video_mode": mode},
        )
        assert resp.status_code == 400
        assert "architecture-ready only and not supported in Core V1" in resp.json()["detail"]


def test_invalid_video_mode_rejected(client):
    resp = client.post(
        "/api/v1/projects",
        json={"title": "Invalid Project", "video_mode": "UNKNOWN_RANDOM_MODE"},
    )
    assert resp.status_code == 400
    assert "Unsupported video mode" in resp.json()["detail"]


def test_short_mode_can_exist_without_story(client, db_session):
    # SHORT mode project created directly
    p_resp = client.post(
        "/api/v1/projects",
        json={
            "title": "Viral Reel Short",
            "video_mode": "SHORT",
            "preferred_aspect_ratio": "9:16",
            "target_duration_seconds": 30.0,
        },
    )
    assert p_resp.status_code == 201
    proj_id = p_resp.json()["id"]

    # Verify no Story exists
    project = db_session.get(Project, uuid.UUID(proj_id))
    assert project.story is None

    # Scene created directly under project without Story
    s_resp = client.post(
        f"/api/v1/projects/{proj_id}/scenes",
        json={"scene_number": 1, "heading": "Hook Scene"},
    )
    assert s_resp.status_code == 201
    scene_data = s_resp.json()
    assert scene_data["project_id"] == proj_id
    assert scene_data["story_id"] is None

    # Shots created under scene
    shot_resp = client.post(
        f"/api/v1/scenes/{scene_data['id']}/shots",
        json={"shot_number": 1, "shot_type": "AI_GENERATED", "duration_seconds": 3.0},
    )
    assert shot_resp.status_code == 201


def test_loop_mode_can_exist_without_story_and_script(client, db_session):
    p_resp = client.post(
        "/api/v1/projects",
        json={
            "title": "Lofi Ambience Loop",
            "video_mode": "LOOP",
            "preferred_aspect_ratio": "16:9",
            "target_duration_seconds": 6.0,
            "mode_config": {"seamless_loop": True},
        },
    )
    assert p_resp.status_code == 201
    proj_id = p_resp.json()["id"]

    project = db_session.get(Project, uuid.UUID(proj_id))
    assert project.story is None

    s_resp = client.post(
        f"/api/v1/projects/{proj_id}/scenes",
        json={"scene_number": 1, "heading": "Loop Scene"},
    )
    assert s_resp.status_code == 201
    scene_id = s_resp.json()["id"]

    shot_resp = client.post(
        f"/api/v1/scenes/{scene_id}/shots",
        json={"shot_number": 1, "shot_type": "AI_GENERATED", "duration_seconds": 6.0},
    )
    assert shot_resp.status_code == 201


def test_scene_mode_can_exist_without_story(client, db_session):
    p_resp = client.post(
        "/api/v1/projects",
        json={
            "title": "Standalone Scene Demo",
            "video_mode": "SCENE",
        },
    )
    assert p_resp.status_code == 201
    proj_id = p_resp.json()["id"]

    s_resp = client.post(
        f"/api/v1/projects/{proj_id}/scenes",
        json={"scene_number": 1, "heading": "Single Scene"},
    )
    assert s_resp.status_code == 201


def test_configuration_inheritance_project_scene_shot(client, db_session):
    # 1. Project has preferred_aspect_ratio 9:16, target_duration 30s, mode_config
    p_resp = client.post(
        "/api/v1/projects",
        json={
            "title": "Inheritance Test Project",
            "video_mode": "SHORT",
            "preferred_aspect_ratio": "9:16",
            "target_duration_seconds": 30.0,
            "default_config": {"fps": 30, "color_space": "rec709"},
            "mode_config": {"hook_intensity": "high"},
        },
    )
    proj_id = p_resp.json()["id"]

    # 2. Scene overrides nothing
    s1_resp = client.post(
        f"/api/v1/projects/{proj_id}/scenes",
        json={"scene_number": 1, "heading": "Scene 1 Default"},
    )
    s1_id = s1_resp.json()["id"]

    shot1_resp = client.post(
        f"/api/v1/scenes/{s1_id}/shots",
        json={"shot_number": 1, "shot_type": "AI_GENERATED", "duration_seconds": 5.0},
    )
    shot1_id = shot1_resp.json()["id"]

    # Shot 1 should inherit 9:16 aspect ratio from Project
    cfg1 = client.get(f"/api/v1/shots/{shot1_id}/effective-config").json()
    assert cfg1["resolved_aspect_ratio"] == "9:16"
    assert cfg1["resolved_duration_seconds"] == 5.0
    assert cfg1["effective_config"]["fps"] == 30
    assert cfg1["effective_config"]["hook_intensity"] == "high"

    # 3. Scene 2 overrides aspect ratio to 1:1 and duration
    s2_resp = client.post(
        f"/api/v1/projects/{proj_id}/scenes",
        json={
            "scene_number": 2,
            "heading": "Scene 2 Overridden",
            "scene_config": {"aspect_ratio": "1:1", "style": "vintage"},
        },
    )
    s2_id = s2_resp.json()["id"]

    shot2_resp = client.post(
        f"/api/v1/scenes/{s2_id}/shots",
        json={"shot_number": 1, "shot_type": "AI_GENERATED"},
    )
    shot2_id = shot2_resp.json()["id"]

    cfg2 = client.get(f"/api/v1/shots/{shot2_id}/effective-config").json()
    assert cfg2["resolved_aspect_ratio"] == "1:1"
    assert cfg2["effective_config"]["style"] == "vintage"
    assert cfg2["effective_config"]["fps"] == 30  # inherited from project

    # 4. Shot 3 explicitly overrides aspect ratio to 16:9 in provider_config
    shot3_resp = client.post(
        f"/api/v1/scenes/{s2_id}/shots",
        json={
            "shot_number": 2,
            "shot_type": "AI_GENERATED",
            "provider_config": {"aspect_ratio": "16:9", "custom_seed": 42},
        },
    )
    shot3_id = shot3_resp.json()["id"]

    cfg3 = client.get(f"/api/v1/shots/{shot3_id}/effective-config").json()
    assert cfg3["resolved_aspect_ratio"] == "16:9"
    assert cfg3["effective_config"]["custom_seed"] == 42
    assert cfg3["effective_config"]["style"] == "vintage"  # from scene
    assert cfg3["effective_config"]["fps"] == 30  # from project
