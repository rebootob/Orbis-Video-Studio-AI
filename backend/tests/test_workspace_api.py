import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models.project import Project
from app.models.scene import Scene
from app.models.shot import Shot
from app.models.generation_job import GenerationJob
from app.services.lock_machine import LockMachineService
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


class MockWorkspaceProvider(IVideoGenerationProviderAdapter):
    provider_name = "mock_ws"

    def submit_video_job(self, request):
        return ProviderJobResult(
            provider_job_id="mock-ws-job-123",
            provider_status="PENDING",
        )

    def poll_video_job(self, provider_job_id: str):
        return ProviderJobResult(
            provider_job_id=provider_job_id,
            provider_status="COMPLETED",
            result_video_url="https://mock.storage/video.mp4",
        )

    def cancel_video_job(self, provider_job_id: str):
        return True


def test_cors_middleware(client: TestClient):
    # Allowed origin
    allowed = client.options(
        "/api/v1/projects",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert allowed.status_code == 200
    assert allowed.headers.get("access-control-allow-origin") == "http://localhost:5173"

    # Disallowed origin
    disallowed = client.options(
        "/api/v1/projects",
        headers={
            "Origin": "http://malicious-site.com",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert disallowed.headers.get("access-control-allow-origin") != "http://malicious-site.com"
    assert disallowed.headers.get("access-control-allow-origin") != "*"


def test_project_crud_and_archive_endpoints(client: TestClient, db_session: Session):
    # 1. Create project
    create_resp = client.post(
        "/api/v1/projects",
        json={
            "title": "Workspace Test Project",
            "video_mode": "STORY",
            "purpose": "Marketing Video",
            "target_platform": "YouTube",
            "target_duration_seconds": 60.0,
            "preferred_aspect_ratio": "16:9",
        },
    )
    assert create_resp.status_code == 201
    proj_data = create_resp.json()
    proj_id = proj_data["id"]
    assert proj_data["title"] == "Workspace Test Project"
    assert proj_data["status"] == "DRAFT"

    # 2. List projects
    list_resp = client.get("/api/v1/projects")
    assert list_resp.status_code == 200
    projects = list_resp.json()
    assert any(p["id"] == proj_id for p in projects)

    # 3. Patch project
    patch_resp = client.patch(
        f"/api/v1/projects/{proj_id}",
        json={
            "title": "Updated Workspace Title",
            "status": "APPROVED",
            "target_duration_seconds": 75.0,
        },
    )
    assert patch_resp.status_code == 200
    updated = patch_resp.json()
    assert updated["title"] == "Updated Workspace Title"
    assert updated["status"] == "APPROVED"
    assert updated["target_duration_seconds"] == 75.0

    # 4. Soft-delete / archive project (HTTP 200, status=ARCHIVED)
    del_resp = client.delete(f"/api/v1/projects/{proj_id}")
    assert del_resp.status_code == 200
    assert del_resp.json()["status"] == "ARCHIVED"

    # 5. Verify excluded from default list, but included when include_archived=true
    list_active = client.get("/api/v1/projects")
    assert not any(p["id"] == proj_id for p in list_active.json())

    list_all = client.get("/api/v1/projects?include_archived=true")
    assert any(p["id"] == proj_id for p in list_all.json())

    # 6. Unarchive project
    unarc_resp = client.post(f"/api/v1/projects/{proj_id}/unarchive")
    assert unarc_resp.status_code == 200
    assert unarc_resp.json()["status"] == "DRAFT"

    # 7. Archive project explicitly via archive endpoint
    arc_resp = client.post(f"/api/v1/projects/{proj_id}/archive")
    assert arc_resp.status_code == 200
    assert arc_resp.json()["status"] == "ARCHIVED"


def test_scene_update_delete_and_lock_guards(client: TestClient, db_session: Session):
    # Create project
    proj = Project(
        id=uuid.uuid4(),
        title="Scene Lock Test",
        video_mode="SCENE",
        status="DRAFT",
    )
    db_session.add(proj)
    db_session.commit()

    # Create scene via endpoint
    scene_resp = client.post(
        f"/api/v1/projects/{proj.id}/scenes",
        json={
            "scene_number": 1,
            "heading": "EXT. BEACH - DAY",
            "description": "Opening sunny beach scene",
            "setting": "Tropical beach",
            "duration_seconds": 5.0,
        },
    )
    assert scene_resp.status_code == 201
    scene_id = scene_resp.json()["id"]

    # Patch scene
    patch_resp = client.patch(
        f"/api/v1/scenes/{scene_id}",
        json={
            "heading": "EXT. SUNNY BEACH - DAY",
            "description": "Waves rolling onto white sand",
        },
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["heading"] == "EXT. SUNNY BEACH - DAY"

    # Lock the scene
    LockMachineService.lock(
        db=db_session,
        project_id=proj.id,
        entity_type="SCENE",
        entity_id=uuid.UUID(scene_id),
        actor="lead_editor",
    )

    # Attempt patch when locked -> 409
    patch_locked = client.patch(
        f"/api/v1/scenes/{scene_id}",
        json={"heading": "EXT. STORMY BEACH - NIGHT"},
    )
    assert patch_locked.status_code == 409

    # Attempt delete when locked -> 409
    del_locked = client.delete(f"/api/v1/scenes/{scene_id}")
    assert del_locked.status_code == 409

    # Unlock scene
    LockMachineService.unlock(
        db=db_session,
        project_id=proj.id,
        entity_type="SCENE",
        entity_id=uuid.UUID(scene_id),
        actor="lead_editor",
    )

    # Delete scene succeeds
    del_resp = client.delete(f"/api/v1/scenes/{scene_id}")
    assert del_resp.status_code == 204


def test_shot_delete_and_lock_guard(client: TestClient, db_session: Session):
    proj = Project(
        id=uuid.uuid4(),
        title="Shot Lock Test",
        video_mode="SCENE",
        status="DRAFT",
    )
    db_session.add(proj)
    db_session.commit()

    scene = Scene(
        id=uuid.uuid4(),
        project_id=proj.id,
        scene_number=1,
        heading="INT. LAB - DAY",
    )
    db_session.add(scene)
    db_session.commit()

    shot_resp = client.post(
        f"/api/v1/scenes/{scene.id}/shots",
        json={
            "shot_number": 1,
            "shot_type": "AI_GENERATED",
            "visual_prompt": "Scientist peering into microscope",
            "duration_seconds": 4.0,
        },
    )
    assert shot_resp.status_code == 201
    shot_id = shot_resp.json()["id"]

    # Lock shot
    LockMachineService.lock(
        db=db_session,
        project_id=proj.id,
        entity_type="SHOT",
        entity_id=uuid.UUID(shot_id),
        actor="director",
    )

    # Deleting locked shot -> 409
    del_locked = client.delete(f"/api/v1/shots/{shot_id}")
    assert del_locked.status_code == 409

    # Unlock shot
    LockMachineService.unlock(
        db=db_session,
        project_id=proj.id,
        entity_type="SHOT",
        entity_id=uuid.UUID(shot_id),
        actor="director",
    )

    # Deleting unlocked shot -> 204
    del_resp = client.delete(f"/api/v1/shots/{shot_id}")
    assert del_resp.status_code == 204


def test_project_queue_and_batch_endpoints(client: TestClient, db_session: Session):
    proj = Project(
        id=uuid.uuid4(),
        title="Queue Test Project",
        video_mode="SHORT",
        status="DRAFT",
    )
    db_session.add(proj)
    db_session.commit()

    scene = Scene(
        id=uuid.uuid4(),
        project_id=proj.id,
        scene_number=1,
        heading="SCENE 1",
    )
    db_session.add(scene)
    db_session.commit()

    shot1 = Shot(
        id=uuid.uuid4(),
        scene_id=scene.id,
        shot_number=1,
        shot_type="AI_GENERATED",
        visual_prompt="Quick zoom on product",
        duration_seconds=3.0,
        is_locked=False,
    )
    shot2 = Shot(
        id=uuid.uuid4(),
        scene_id=scene.id,
        shot_number=2,
        shot_type="AI_GENERATED",
        visual_prompt="Customer smiling",
        duration_seconds=3.0,
        is_locked=False,
    )
    db_session.add_all([shot1, shot2])
    db_session.commit()

    # Batch generate shots for project
    batch_resp = client.post(
        f"/api/v1/projects/{proj.id}/jobs/batch"
    )
    assert batch_resp.status_code == 200
    jobs = batch_resp.json()
    assert len(jobs) == 2

    # Query project jobs
    proj_jobs_resp = client.get(f"/api/v1/projects/{proj.id}/jobs")
    assert proj_jobs_resp.status_code == 200
    all_jobs = proj_jobs_resp.json()
    assert len(all_jobs) == 2
    assert all(j["shot_id"] in [str(shot1.id), str(shot2.id)] for j in all_jobs)


def test_duplicate_project_and_scene(client: TestClient, db_session: Session):
    # Setup project with scenes and shots
    proj = Project(
        id=uuid.uuid4(),
        title="Source Project For Clone",
        video_mode="STORY",
        status="STORY_APPROVED",
        purpose="Testing Duplication",
    )
    db_session.add(proj)
    db_session.commit()

    scene = Scene(
        id=uuid.uuid4(),
        project_id=proj.id,
        scene_number=1,
        heading="INTRO SCENE",
    )
    db_session.add(scene)
    db_session.commit()

    shot = Shot(
        id=uuid.uuid4(),
        scene_id=scene.id,
        shot_number=1,
        shot_type="AI_GENERATED",
        visual_prompt="Close up of device",
        duration_seconds=5.0,
    )
    db_session.add(shot)
    db_session.commit()

    # 1. Duplicate Scene
    dup_scene_resp = client.post(f"/api/v1/scenes/{scene.id}/duplicate")
    assert dup_scene_resp.status_code == 201
    dup_scene = dup_scene_resp.json()
    assert dup_scene["id"] != str(scene.id)
    assert dup_scene["heading"] == "INTRO SCENE (Copy)"
    assert dup_scene["scene_number"] == 2
    assert len(dup_scene["shots"]) == 1
    assert dup_scene["shots"][0]["id"] != str(shot.id)

    # 2. Duplicate Project
    dup_proj_resp = client.post(f"/api/v1/projects/{proj.id}/duplicate")
    assert dup_proj_resp.status_code == 201
    dup_proj = dup_proj_resp.json()
    assert dup_proj["id"] != str(proj.id)
    assert dup_proj["title"] == "Copy of Source Project For Clone"
    assert dup_proj["status"] == "DRAFT"

    # Verify duplicated project has duplicated scenes and shots
    scenes_resp = client.get(f"/api/v1/projects/{dup_proj['id']}/scenes")
    assert scenes_resp.status_code == 200
    dup_scenes = scenes_resp.json()
    assert len(dup_scenes) == 2


def test_scene_and_shot_reorder(client: TestClient, db_session: Session):
    proj = Project(id=uuid.uuid4(), title="Reorder Project", video_mode="STORY")
    db_session.add(proj)
    db_session.commit()

    s1 = Scene(id=uuid.uuid4(), project_id=proj.id, scene_number=1, heading="S1")
    s2 = Scene(id=uuid.uuid4(), project_id=proj.id, scene_number=2, heading="S2")
    db_session.add_all([s1, s2])
    db_session.commit()

    # Reorder scenes: swap 1 and 2
    reorder_resp = client.patch(
        f"/api/v1/projects/{proj.id}/scenes/reorder",
        json={
            "items": [
                {"id": str(s1.id), "order": 2},
                {"id": str(s2.id), "order": 1},
            ]
        },
    )
    assert reorder_resp.status_code == 200
    scenes_list = reorder_resp.json()
    assert scenes_list[0]["id"] == str(s2.id)
    assert scenes_list[0]["scene_number"] == 1
    assert scenes_list[1]["id"] == str(s1.id)
    assert scenes_list[1]["scene_number"] == 2

    # Add shots to s1 and reorder shots
    sh1 = Shot(id=uuid.uuid4(), scene_id=s1.id, shot_number=1, shot_type="AI_GENERATED")
    sh2 = Shot(id=uuid.uuid4(), scene_id=s1.id, shot_number=2, shot_type="AI_GENERATED")
    db_session.add_all([sh1, sh2])
    db_session.commit()

    shot_reorder_resp = client.patch(
        f"/api/v1/scenes/{s1.id}/shots/reorder",
        json={
            "items": [
                {"id": str(sh1.id), "order": 2},
                {"id": str(sh2.id), "order": 1},
            ]
        },
    )
    assert shot_reorder_resp.status_code == 200
    shots_list = shot_reorder_resp.json()
    assert shots_list[0]["id"] == str(sh2.id)
    assert shots_list[0]["shot_number"] == 1


def test_deletion_blocked_on_recorded_history(client: TestClient, db_session: Session):
    proj = Project(id=uuid.uuid4(), title="Audit Guard Project", video_mode="STORY")
    db_session.add(proj)
    db_session.commit()

    scene = Scene(id=uuid.uuid4(), project_id=proj.id, scene_number=1)
    db_session.add(scene)
    db_session.commit()

    shot = Shot(id=uuid.uuid4(), scene_id=scene.id, shot_number=1, shot_type="AI_GENERATED")
    db_session.add(shot)
    db_session.commit()

    # Attach a generation job to shot
    job = GenerationJob(
        id=uuid.uuid4(),
        shot_id=shot.id,
        provider_name="vidu",
        status="COMPLETED",
    )
    db_session.add(job)
    db_session.commit()

    # Attempt to delete shot -> 409 Conflict
    del_shot_resp = client.delete(f"/api/v1/shots/{shot.id}")
    assert del_shot_resp.status_code == 409
    assert "recorded generation jobs" in del_shot_resp.json()["detail"]

    # Attempt to delete scene containing this shot -> 409 Conflict
    del_scene_resp = client.delete(f"/api/v1/scenes/{scene.id}")
    assert del_scene_resp.status_code == 409
    assert "recorded generation jobs" in del_scene_resp.json()["detail"]


def test_batch_job_estimate_and_selected_generation(client: TestClient, db_session: Session):
    proj = Project(id=uuid.uuid4(), title="Estimate & Selected Project", video_mode="SHORT")
    db_session.add(proj)
    db_session.commit()

    scene = Scene(id=uuid.uuid4(), project_id=proj.id, scene_number=1)
    db_session.add(scene)
    db_session.commit()

    shot1 = Shot(id=uuid.uuid4(), scene_id=scene.id, shot_number=1, duration_seconds=5.0, shot_type="AI_GENERATED")
    shot2 = Shot(id=uuid.uuid4(), scene_id=scene.id, shot_number=2, duration_seconds=4.0, shot_type="AI_GENERATED")
    db_session.add_all([shot1, shot2])
    db_session.commit()

    # 1. Estimate for all incomplete shots
    est_resp = client.post(
        f"/api/v1/projects/{proj.id}/jobs/estimate",
        json={"provider_name": "vidu", "only_incomplete": True},
    )
    assert est_resp.status_code == 200
    est = est_resp.json()
    assert est["shot_count"] == 2
    # Check pricing status: vidu video generation is estimated or flagged UNKNOWN truthfully
    assert est["currency"] == "USD"
    if est["has_unknown_pricing"]:
        assert est["estimated_cost_total"] is None
        assert any("UNKNOWN" in w for w in est["warning_messages"])

    # 2. Batch dispatch with selected shot_ids only (Generate Selected)
    batch_resp = client.post(
        f"/api/v1/projects/{proj.id}/jobs/batch",
        json={"shot_ids": [str(shot1.id)]},
    )
    assert batch_resp.status_code == 200
    created = batch_resp.json()
    assert len(created) == 1
    assert created[0]["shot_id"] == str(shot1.id)
