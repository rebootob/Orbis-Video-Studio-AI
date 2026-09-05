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

    project = Project(title="Timeout Project", status="DRAFT")
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
