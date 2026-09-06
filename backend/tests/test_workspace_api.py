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
    response = client.options(
        "/api/v1/projects",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"



def test_project_crud_endpoints(client: TestClient, db_session: Session):
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

    # 4. Delete project
    del_resp = client.delete(f"/api/v1/projects/{proj_id}")
    assert del_resp.status_code == 204

    # 5. Verify 404
    get_resp = client.get(f"/api/v1/projects/{proj_id}")
    assert get_resp.status_code == 404


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

