import io
import uuid
import pytest
from app.models.project import Project
from app.models.story import Story
from app.models.scene import Scene
from app.models.shot import Shot
from app.models.asset import Asset
from app.models.document_extraction import DocumentExtraction
from app.models.generation_audit import GenerationAuditLog
from app.services.creative_generation.prompt_composer import (
    StoryPromptComposer,
    ScenePromptComposer,
    ShotPromptComposer,
)
from app.services.creative_generation.fake_provider import FakeCreativeGenerationProvider
from app.services.creative_generation.factory import get_creative_provider
from app.api.v1.endpoints import story_generation as story_endpoint


def test_prompt_composer_separates_facts_and_creative_direction():
    docs = [{"filename": "brief.pdf", "content": "Company revenue grew 50% in 2025."}]
    prompt = StoryPromptComposer.compose(
        project_title="Annual Report Video",
        project_brief="Create visual summary of 2025 growth",
        extracted_documents=docs,
        target_duration_seconds=30.0,
        tone="professional",
        language="th",
    )

    assert "=== FACTUAL SOURCE MATERIAL (AUTHORITATIVE) ===" in prompt
    assert "Company revenue grew 50% in 2025." in prompt
    assert "=== CREATIVE DIRECTION & OBJECTIVES ===" in prompt
    assert "Annual Report Video" in prompt
    assert "30.0 seconds" in prompt
    assert "Primary Output Language: th" in prompt


def test_full_story_generation_flow_with_fake_provider(client, db_session):
    fake_provider = FakeCreativeGenerationProvider()
    client.app.dependency_overrides[get_creative_provider] = lambda: fake_provider

    # 1. Create Project
    project = Project(title="Sci-Fi Adventure Project", description="Epic space story brief", status="DRAFT")
    db_session.add(project)
    db_session.commit()

    # 2. Add an Asset & DocumentExtraction from WP004
    asset = Asset(
        id=uuid.uuid4(),
        project_id=project.id,
        name="Research Brief",
        asset_type="DOCUMENT",
        original_filename="brief.txt",
        content_type="text/plain",
        file_size_bytes=100,
        checksum_sha256="dummychecksum1234567890",
        storage_bucket="test-bucket",
        storage_key="test-key",
    )
    db_session.add(asset)
    db_session.commit()

    doc_ext = DocumentExtraction(
        id=uuid.uuid4(),
        asset_id=asset.id,
        document_type="txt",
        status="SUCCESS",
        extracted_text="ในอวกาศอันไกลโพ้น สถานีอวกาศ Jupiter Prime ได้ถูกค้นพบ",
        character_count=50,
        segment_count=1,
        extraction_method="text-decoder",
        extraction_duration_ms=5.0,
    )
    db_session.add(doc_ext)
    db_session.commit()

    # 3. Call POST /api/v1/projects/{project_id}/story/generate
    gen_resp = client.post(
        f"/api/v1/projects/{project.id}/story/generate",
        json={
            "target_duration_seconds": 60.0,
            "tone": "cinematic",
            "language": "th",
            "profile": "BALANCED",
        },
    )
    assert gen_resp.status_code == 200
    data = gen_resp.json()

    assert data["project_id"] == str(project.id)
    assert "บทภาพยนตร์จำลอง" in data["title"]
    assert "กัปตันซาร่า" in data["logline"]
    assert data["status"] == "GENERATED"
    assert data["is_locked"] is False

    # Verify Scenes and Shots in response
    assert len(data["scenes"]) >= 1
    scene1 = data["scenes"][0]
    assert scene1["scene_number"] == 1
    assert "EXT. JUPITER ORBIT" in scene1["heading"]
    assert "ในปี 2088" in scene1["narration"]

    assert len(scene1["shots"]) >= 2
    shot1 = scene1["shots"][0]
    assert shot1["shot_number"] == 1
    assert shot1["shot_type"] == "AI_GENERATED"
    assert "image_prompt" in shot1 and shot1["image_prompt"]
    assert "video_prompt" in shot1 and shot1["video_prompt"]
    assert "Futuristic spaceship" in shot1["video_prompt"]

    # 4. Verify GET /api/v1/projects/{project_id}/story
    get_resp = client.get(f"/api/v1/projects/{project.id}/story")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == data["id"]

    # 5. Verify Audit Log entry in DB
    audit = db_session.query(GenerationAuditLog).filter(GenerationAuditLog.project_id == project.id).first()
    assert audit is not None
    assert audit.provider == "fake_openai"
    assert audit.request_type == "STORY_GENERATE"
    assert audit.status == "SUCCESS"
    assert audit.duration_ms >= 0.0


def test_locked_story_blocks_regeneration(client, db_session):
    fake_provider = FakeCreativeGenerationProvider()
    client.app.dependency_overrides[get_creative_provider] = lambda: fake_provider

    project = Project(title="Locked Story Project", status="DRAFT")
    db_session.add(project)
    db_session.commit()

    story = Story(
        id=uuid.uuid4(),
        project_id=project.id,
        title="Locked Story",
        logline="Locked logline",
        synopsis="Locked synopsis",
        is_locked=True,
        status="GENERATED",
    )
    db_session.add(story)
    db_session.commit()

    gen_resp = client.post(f"/api/v1/projects/{project.id}/story/generate", json={})
    assert gen_resp.status_code == 409
    assert "locked" in gen_resp.json()["detail"].lower()


def test_granular_scene_and_shot_generation_endpoints(client, db_session):
    fake_provider = FakeCreativeGenerationProvider()
    client.app.dependency_overrides[get_creative_provider] = lambda: fake_provider

    project = Project(title="Granular Project", status="DRAFT")
    db_session.add(project)
    db_session.commit()

    story = Story(
        id=uuid.uuid4(),
        project_id=project.id,
        title="Existing Story",
        logline="Logline",
        synopsis="Synopsis",
        is_locked=False,
    )
    db_session.add(story)
    db_session.commit()

    # Generate Scenes
    scenes_resp = client.post(f"/api/v1/stories/{story.id}/scenes/generate", json={"custom_instructions": "Focus on lab scene"})
    assert scenes_resp.status_code == 200
    scenes = scenes_resp.json()
    assert len(scenes) >= 1
    scene_id = scenes[0]["id"]

    # Generate Shots for Scene
    shots_resp = client.post(f"/api/v1/scenes/{scene_id}/shots/generate", json={"custom_instructions": "Focus on crystal optics"})
    assert shots_resp.status_code == 200
    shots = shots_resp.json()
    assert len(shots) >= 1
    assert shots[0]["shot_number"] == 1
    assert shots[0]["image_prompt"]
    assert shots[0]["video_prompt"]


def test_provider_error_status_mappings(client, db_session):
    # Test Timeout mapping (504)
    timeout_provider = FakeCreativeGenerationProvider(should_fail=True, error_code="PROVIDER_TIMEOUT", error_message="Request timed out")
    client.app.dependency_overrides[get_creative_provider] = lambda: timeout_provider

    project = Project(title="Timeout Project", description="Valid story brief context", status="DRAFT")
    db_session.add(project)
    db_session.commit()

    resp = client.post(f"/api/v1/projects/{project.id}/story/generate", json={})
    assert resp.status_code == 504
    assert "timed out" in resp.json()["detail"].lower()

    # Test Provider Unavailable mapping (503)
    unavail_provider = FakeCreativeGenerationProvider(should_fail=True, error_code="PROVIDER_UNAVAILABLE", error_message="Server 503")
    client.app.dependency_overrides[get_creative_provider] = lambda: unavail_provider

    resp = client.post(f"/api/v1/projects/{project.id}/story/generate", json={})
    assert resp.status_code == 503

    # Test Invalid Provider Response mapping (502)
    invalid_provider = FakeCreativeGenerationProvider(should_fail=True, error_code="INVALID_PROVIDER_RESPONSE", error_message="Invalid JSON")
    client.app.dependency_overrides[get_creative_provider] = lambda: invalid_provider

    resp = client.post(f"/api/v1/projects/{project.id}/story/generate", json={})
    assert resp.status_code == 502


def test_non_existent_project_returns_404(client):
    fake_project_id = str(uuid.uuid4())
    resp = client.post(f"/api/v1/projects/{fake_project_id}/story/generate", json={})
    assert resp.status_code == 404


def test_no_source_context_guard_prevents_provider_call(client, db_session):
    from unittest.mock import MagicMock

    mock_provider = MagicMock()
    client.app.dependency_overrides[get_creative_provider] = lambda: mock_provider

    # Project with no description/brief and no documents
    project = Project(title="Empty Context Project", description=None, status="DRAFT")
    db_session.add(project)
    db_session.commit()

    resp = client.post(f"/api/v1/projects/{project.id}/story/generate", json={})
    assert resp.status_code == 400
    assert "no source context provided" in resp.json()["detail"].lower()
    mock_provider.generate_story.assert_not_called()


def test_success_audit_transaction_rollback_on_persistence_failure(db_session, monkeypatch):
    from app.services.creative_generation.service import StoryGenerationService

    project = Project(title="Rollback Test Project", description="Valid story brief", status="DRAFT")
    db_session.add(project)
    db_session.commit()
    proj_id = project.id

    fake_provider = FakeCreativeGenerationProvider()
    service = StoryGenerationService(db=db_session, provider=fake_provider)

    # Monkeypatch db_session.flush to simulate persistence failure during domain persistence
    def failing_flush():
        raise RuntimeError("Simulated DB Persistence Flush Error")

    # Let project setup flush normally, then fail on generation flush
    monkeypatch.setattr(db_session, "flush", failing_flush)

    with pytest.raises(RuntimeError) as exc_info:
        service.generate_project_story(proj_id)

    assert "Simulated DB Persistence Flush Error" in str(exc_info.value)

    # Verify no durable SUCCESS audit log remains in DB
    audits = db_session.query(GenerationAuditLog).filter(
        GenerationAuditLog.project_id == proj_id,
        GenerationAuditLog.status == "SUCCESS",
    ).all()
    assert len(audits) == 0


def test_sanitized_provider_error_response_no_raw_body_leak(monkeypatch):
    import httpx
    from app.services.creative_generation.openai_provider import OpenAICreativeGenerationProvider
    from app.services.creative_generation.base import CreativeGenerationError

    provider = OpenAICreativeGenerationProvider(api_key="sk-test-key-12345")

    # Mock httpx.Client.post to return a 400 error containing sensitive diagnostics
    class MockResponse:
        status_code = 400
        text = '{"error": {"code": "invalid_prompt", "secret_diagnostic": "token_abc123secret_leak"}}'

        def json(self):
            return {"error": "diagnostic"}

    class MockClient:
        def __init__(self, timeout=None):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            pass

        def post(self, url, headers=None, json=None):
            return MockResponse()

    monkeypatch.setattr(httpx, "Client", MockClient)

    with pytest.raises(CreativeGenerationError) as exc_info:
        provider.generate_story("Test prompt")

    assert exc_info.value.code == "GENERATION_FAILED"
    # Ensure raw secret diagnostics and headers are NOT present in error message
    assert "token_abc123secret_leak" not in exc_info.value.message
    assert "sk-test-key-12345" not in exc_info.value.message
    assert exc_info.value.message == "OpenAI provider returned HTTP error 400."


def test_regeneration_preserves_history_and_lineage(client, db_session):
    """Verify that regenerating a story or scenes soft-archives previous records instead of destructively deleting them."""
    fake_provider = FakeCreativeGenerationProvider()
    client.app.dependency_overrides[get_creative_provider] = lambda: fake_provider

    project = Project(title="Lineage Retention Project", description="Historical lineage brief", status="DRAFT")
    db_session.add(project)
    db_session.commit()

    # First generation pass
    resp1 = client.post(f"/api/v1/projects/{project.id}/story/generate", json={"generate_scenes": True})
    assert resp1.status_code == 200
    data1 = resp1.json()
    old_scene_ids = [uuid.UUID(s["id"]) for s in data1["scenes"]]
    old_shot_ids = [uuid.UUID(sh["id"]) for s in data1["scenes"] for sh in s["shots"]]
    assert len(old_scene_ids) > 0
    assert len(old_shot_ids) > 0

    # Second generation pass (regeneration)
    resp2 = client.post(f"/api/v1/projects/{project.id}/story/generate", json={"generate_scenes": True})
    assert resp2.status_code == 200
    data2 = resp2.json()
    new_scene_ids = [uuid.UUID(s["id"]) for s in data2["scenes"]]
    new_shot_ids = [uuid.UUID(sh["id"]) for s in data2["scenes"] for sh in s["shots"]]

    # Verify new records were created
    assert set(old_scene_ids).isdisjoint(set(new_scene_ids))
    assert set(old_shot_ids).isdisjoint(set(new_shot_ids))

    # CRITICAL: Verify previous records REMAIN in the database
    for old_scene_id in old_scene_ids:
        sc = db_session.get(Scene, old_scene_id)
        assert sc is not None, f"Scene {old_scene_id} was unexpectedly deleted from DB!"
        assert (sc.scene_config or {}).get("archived") is True

    for old_shot_id in old_shot_ids:
        sh = db_session.get(Shot, old_shot_id)
        assert sh is not None, f"Shot {old_shot_id} was unexpectedly deleted from DB!"
        assert sh.status == "ARCHIVED"

    # Verify normal list endpoint excludes archived by default, but includes them when requested
    list_resp = client.get(f"/api/v1/projects/{project.id}/scenes")
    assert list_resp.status_code == 200
    active_ids = [s["id"] for s in list_resp.json()]
    assert all(str(oid) not in active_ids for oid in old_scene_ids)

    list_all_resp = client.get(f"/api/v1/projects/{project.id}/scenes?include_archived=true")
    assert list_all_resp.status_code == 200
    all_ids = [s["id"] for s in list_all_resp.json()]
    assert all(str(oid) in all_ids for oid in old_scene_ids)


def test_staged_story_generation_without_scenes(client, db_session):
    """Verify that STORY mode can generate an inspectable Story artifact without creating scenes/shots before approval."""
    fake_provider = FakeCreativeGenerationProvider()
    client.app.dependency_overrides[get_creative_provider] = lambda: fake_provider

    project = Project(title="Staged Story Only Project", description="Story stage brief", status="DRAFT")
    db_session.add(project)
    db_session.commit()

    resp = client.post(
        f"/api/v1/projects/{project.id}/story/generate",
        json={"generate_scenes": False},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "GENERATED"
    assert "title" in data and data["title"]
    assert "logline" in data and data["logline"]
    assert "synopsis" in data and data["synopsis"]

    # Verify NO scenes or shots were created downstream
    assert len(data["scenes"]) == 0
    scenes_in_db = db_session.query(Scene).filter(Scene.story_id == uuid.UUID(data["id"])).all()
    assert len(scenes_in_db) == 0


def test_non_story_mode_storyboard_bypass(client, db_session):
    """Verify that SHORT / LOOP / SCENE modes can generate a storyboard directly without creating a Story entity."""
    fake_provider = FakeCreativeGenerationProvider()
    client.app.dependency_overrides[get_creative_provider] = lambda: fake_provider

    project = Project(
        title="Short Mode Project",
        description="Viral TikTok hook brief",
        video_mode="SHORT",
        status="DRAFT",
    )
    db_session.add(project)
    db_session.commit()

    # Call project storyboard generation directly
    resp = client.post(
        f"/api/v1/projects/{project.id}/storyboard/generate",
        json={"generate_shots": False},
    )
    assert resp.status_code == 200
    scenes = resp.json()
    assert len(scenes) >= 1

    # Verify scenes belong to project directly and story_id is None
    for sc in scenes:
        scene_row = db_session.get(Scene, uuid.UUID(sc["id"]))
        assert scene_row.project_id == project.id
        assert scene_row.story_id is None
        # Verify shots not yet generated
        assert len(scene_row.shots) == 0

    # Verify NO Story record was created
    story = db_session.query(Story).filter(Story.project_id == project.id).first()
    assert story is None


def test_real_shot_plan_generation_service(client, db_session):
    """Verify that generating a shot plan uses the real backend service to create detailed prompts."""
    fake_provider = FakeCreativeGenerationProvider()
    client.app.dependency_overrides[get_creative_provider] = lambda: fake_provider

    project = Project(title="Shot Planning Project", description="Detailed planning brief", status="DRAFT")
    db_session.add(project)
    db_session.commit()

    scene = Scene(id=uuid.uuid4(), project_id=project.id, scene_number=1, heading="INT. CONTROL ROOM")
    db_session.add(scene)
    db_session.commit()

    resp = client.post(f"/api/v1/scenes/{scene.id}/shots/generate", json={})
    assert resp.status_code == 200
    shots = resp.json()
    assert len(shots) >= 1
    shot1 = shots[0]
    assert shot1["scene_id"] == str(scene.id)
    assert shot1["shot_type"] == "AI_GENERATED"
    assert shot1["image_prompt"] is not None and len(shot1["image_prompt"]) > 0
    assert shot1["video_prompt"] is not None and len(shot1["video_prompt"]) > 0
    assert shot1["camera"] is not None
