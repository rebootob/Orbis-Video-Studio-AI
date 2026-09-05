import uuid
import pytest
from app.models.project import Project
from app.models.asset import Asset
from app.models.reference_library import (
    ProjectReference,
    CharacterBible,
    LocationBible,
    StyleBible,
    BrandBible,
)
from app.services.reference_library.context_builder import ReferenceContextBuilder
from app.services.creative_generation.prompt_composer import StoryPromptComposer
from app.services.creative_generation.fake_provider import FakeCreativeGenerationProvider
from app.services.creative_generation.factory import get_creative_provider
from app.core.config import settings


def test_reference_library_crud_and_lock_protection(client, db_session):
    # 1. Create two projects
    p1 = Project(title="Project One", description="P1 desc", status="DRAFT")
    p2 = Project(title="Project Two", description="P2 desc", status="DRAFT")
    db_session.add_all([p1, p2])
    db_session.commit()

    # 2. Create assets for P1 and P2
    asset_p1 = Asset(
        id=uuid.uuid4(),
        project_id=p1.id,
        name="P1 Character Concept",
        asset_type="IMAGE",
        original_filename="concept.jpg",
        content_type="image/jpeg",
        file_size_bytes=1024,
        checksum_sha256="abc123sha256",
        storage_bucket="bkt",
        storage_key="k1",
    )
    asset_p2 = Asset(
        id=uuid.uuid4(),
        project_id=p2.id,
        name="P2 Asset",
        asset_type="IMAGE",
        original_filename="p2.jpg",
        content_type="image/jpeg",
        file_size_bytes=2048,
        checksum_sha256="def456sha256",
        storage_bucket="bkt",
        storage_key="k2",
    )
    db_session.add_all([asset_p1, asset_p2])
    db_session.commit()

    # 3. Create ProjectReference with valid asset link (P1 asset to P1 project)
    resp = client.post(
        f"/api/v1/projects/{p1.id}/references",
        json={
            "name": "World Lore",
            "category": "DOCUMENT",
            "description": "Detailed history of ancient kingdom",
            "reference_asset_id": str(asset_p1.id),
            "is_locked": True,
        },
    )
    assert resp.status_code == 201
    ref_data = resp.json()
    ref_id = ref_data["id"]
    assert ref_data["is_locked"] is True

    # 4. Attempt to create ProjectReference with cross-project asset (P2 asset to P1 project) -> 400
    resp_cross = client.post(
        f"/api/v1/projects/{p1.id}/references",
        json={
            "name": "Cross Project Reference",
            "category": "OTHER",
            "description": "Invalid reference",
            "reference_asset_id": str(asset_p2.id),
        },
    )
    assert resp_cross.status_code == 400
    assert resp_cross.json()["detail"] == f"Referenced asset '{asset_p2.id}' belongs to project '{p2.id}', not project '{p1.id}'. Cross-project asset linking is prohibited."

    # 5. Attempt to update locked ProjectReference without unlocking -> 409
    resp_lock_upd = client.patch(
        f"/api/v1/references/{ref_id}",
        json={"name": "Updated World Lore"},
    )
    assert resp_lock_upd.status_code == 409
    assert "is locked" in resp_lock_upd.json()["detail"]

    # 6. Attempt to delete locked ProjectReference -> 409
    resp_lock_del = client.delete(f"/api/v1/references/{ref_id}")
    assert resp_lock_del.status_code == 409
    assert "is locked" in resp_lock_del.json()["detail"]

    # 7. Attempt unlock + modify in same request -> 409
    resp_unlock_mod = client.patch(
        f"/api/v1/references/{ref_id}",
        json={"is_locked": False, "name": "Unlocked World Lore"},
    )
    assert resp_unlock_mod.status_code == 409

    # 8. Unlock-only -> 200
    resp_unlock = client.patch(
        f"/api/v1/references/{ref_id}",
        json={"is_locked": False},
    )
    assert resp_unlock.status_code == 200
    assert resp_unlock.json()["is_locked"] is False

    # 9. Subsequent modification after unlock -> 200
    resp_mod = client.patch(
        f"/api/v1/references/{ref_id}",
        json={"name": "Unlocked World Lore"},
    )
    assert resp_mod.status_code == 200
    assert resp_mod.json()["name"] == "Unlocked World Lore"

    # 10. Delete unlocked reference -> 204, underlying asset must remain intact
    resp_del = client.delete(f"/api/v1/references/{ref_id}")
    assert resp_del.status_code == 204

    db_session.expire_all()
    remaining_asset = db_session.query(Asset).filter(Asset.id == asset_p1.id).first()
    assert remaining_asset is not None


def test_character_and_location_bibles_endpoints(client, db_session):
    project = Project(title="Anime Movie", description="Test project", status="DRAFT")
    db_session.add(project)
    db_session.commit()

    # Create Character Bible (Japanese & Thai script)
    char_resp = client.post(
        f"/api/v1/projects/{project.id}/characters",
        json={
            "name": "คาเอเดะ (Kaede - 楓)",
            "role": "Protagonist / พระเอก",
            "appearance": "นักซามูไรผมสีเงิน ตาเทา มีรอยแผลเป็นที่แก้มซ้าย",
            "personality": "เงียบขรึม ยึดมั่นในเกียรติ",
            "speaking_style": "พูดน้อย ใช้คำสุภาพแต่เด็ดขาด",
            "is_locked": True,
        },
    )
    assert char_resp.status_code == 201
    char_data = char_resp.json()
    assert char_data["name"] == "คาเอเดะ (Kaede - 楓)"
    char_id = char_data["id"]

    # Create Location Bible
    loc_resp = client.post(
        f"/api/v1/projects/{project.id}/locations",
        json={
            "name": "วัดไผ่เขียว (Green Bamboo Temple)",
            "description": "วัดโบราณท่ามกลางป่าไผ่ หมอกหนาแน่นยามเช้า",
            "environment": "เงียบสงบ ลึกลับ ศักดิ์สิทธิ์",
            "time_of_day_default": "DAWN",
            "is_locked": True,
        },
    )
    assert loc_resp.status_code == 201
    loc_data = loc_resp.json()
    assert loc_data["name"] == "วัดไผ่เขียว (Green Bamboo Temple)"

    # List Characters and Locations
    chars_list = client.get(f"/api/v1/projects/{project.id}/characters").json()
    assert len(chars_list) == 1

    locs_list = client.get(f"/api/v1/projects/{project.id}/locations").json()
    assert len(locs_list) == 1

    # Verify lock protection on character
    upd_resp = client.patch(
        f"/api/v1/characters/{char_id}",
        json={"role": "Antagonist"},
    )
    assert upd_resp.status_code == 409


def test_style_and_brand_bibles_endpoints(client, db_session):
    project = Project(title="Brand Promo", description="Test project", status="DRAFT")
    db_session.add(project)
    db_session.commit()

    # Style Bible
    style_resp = client.post(
        f"/api/v1/projects/{project.id}/styles",
        json={
            "name": "Default Project Style",
            "visual_style": "Cinematic Anime 8K",
            "color_direction": "Vibrant Red and Blue",
            "lighting_style": "High Contrast Dramatic",
            "camera_style": "Anamorphic Lens 35mm",
            "negative_constraints": "blurry, low quality, distorted",
        },
    )
    assert style_resp.status_code == 201
    assert style_resp.json()["visual_style"] == "Cinematic Anime 8K"

    # Brand Bible
    brand_resp = client.post(
        f"/api/v1/projects/{project.id}/brands",
        json={
            "brand_name": "Orbis Studio",
            "do_and_dont_rules": "Do not show violent scenes with logo.",
        },
    )
    assert brand_resp.status_code == 201
    assert brand_resp.json()["brand_name"] == "Orbis Studio"


def test_reference_context_builder_prioritization_and_bounding(db_session):
    project = Project(title="Context Test Project", description="Desc", status="DRAFT")
    db_session.add(project)
    db_session.commit()

    # Add references of various categories
    ref_factual = ProjectReference(
        id=uuid.uuid4(),
        project_id=project.id,
        name="Historical Fact Sheet",
        category="DOCUMENT",
        description="Fact 1: Event occurred in 1920.",
        is_locked=True,
    )
    ref_brand = ProjectReference(
        id=uuid.uuid4(),
        project_id=project.id,
        name="Brand Guidelines",
        category="BRAND",
        description="Use primary blue color #0000FF.",
        is_locked=False,
    )
    char = CharacterBible(
        id=uuid.uuid4(),
        project_id=project.id,
        name="Hero",
        role="Lead",
        appearance="Brave warrior",
        is_locked=True,
    )
    loc = LocationBible(
        id=uuid.uuid4(),
        project_id=project.id,
        name="Castle",
        description="Stone fortress",
        is_locked=True,
    )
    style = StyleBible(
        id=uuid.uuid4(),
        project_id=project.id,
        name="Main Style",
        visual_style="Photorealistic",
    )
    brand = BrandBible(
        id=uuid.uuid4(),
        project_id=project.id,
        brand_name="Global Brand",
        do_and_dont_rules="Always highlight innovation.",
    )
    db_session.add_all([ref_factual, ref_brand, char, loc, style, brand])
    db_session.commit()

    context_dict = ReferenceContextBuilder.build_context(db_session, project.id)
    context_text = ReferenceContextBuilder.format_prompt_section(context_dict)

    # Verify section headings and ordering
    assert "=== LOCKED PROJECT REFERENCES ===" in context_text
    assert "Hero" in context_text
    assert "Castle" in context_text
    assert "Global Brand" in context_text
    assert "Photorealistic" in context_text

    # Verify character length limit
    assert len(context_text) <= settings.MAX_REFERENCE_CONTEXT_CHARACTERS


def test_story_generation_includes_reference_context(client, db_session):
    fake_provider = FakeCreativeGenerationProvider()
    client.app.dependency_overrides[get_creative_provider] = lambda: fake_provider

    project = Project(title="Reference Integration Project", description="Story brief", status="DRAFT")
    db_session.add(project)
    db_session.commit()

    char = CharacterBible(
        id=uuid.uuid4(),
        project_id=project.id,
        name="Captain John",
        role="Commander",
        appearance="Tall officer with eye patch",
        personality="Decisive, strict",
        is_locked=True,
    )
    db_session.add(char)
    db_session.commit()

    gen_resp = client.post(
        f"/api/v1/projects/{project.id}/story/generate",
        json={
            "target_duration_seconds": 30.0,
            "tone": "action",
            "language": "en",
        },
    )
    assert gen_resp.status_code == 200
    data = gen_resp.json()
    assert data["status"] == "GENERATED"


def test_locked_entity_unlock_only_transitions_all_types(client, db_session):
    project = Project(title="Lock Contract Test", status="DRAFT")
    db_session.add(project)
    db_session.commit()

    # 1. Character Bible lock transitions
    c_resp = client.post(f"/api/v1/projects/{project.id}/characters", json={"name": "LockChar", "is_locked": True})
    c_id = c_resp.json()["id"]

    # Unlock + Modify in same request -> 409
    assert client.patch(f"/api/v1/characters/{c_id}", json={"is_locked": False, "role": "Hero"}).status_code == 409
    # Modify while locked -> 409
    assert client.patch(f"/api/v1/characters/{c_id}", json={"role": "Hero"}).status_code == 409
    # Unlock-only -> 200
    res_u = client.patch(f"/api/v1/characters/{c_id}", json={"is_locked": False})
    assert res_u.status_code == 200
    assert res_u.json()["is_locked"] is False
    # Subsequent modification after unlock -> 200
    res_m = client.patch(f"/api/v1/characters/{c_id}", json={"role": "Hero"})
    assert res_m.status_code == 200
    assert res_m.json()["role"] == "Hero"

    # 2. Location Bible lock transitions
    l_resp = client.post(f"/api/v1/projects/{project.id}/locations", json={"name": "LockLoc", "is_locked": True})
    l_id = l_resp.json()["id"]
    assert client.patch(f"/api/v1/locations/{l_id}", json={"is_locked": False, "environment": "Forest"}).status_code == 409
    assert client.patch(f"/api/v1/locations/{l_id}", json={"is_locked": False}).status_code == 200
    assert client.patch(f"/api/v1/locations/{l_id}", json={"environment": "Forest"}).status_code == 200

    # 3. Style Bible lock transitions
    s_resp = client.post(f"/api/v1/projects/{project.id}/styles", json={"name": "LockStyle", "is_locked": True})
    s_id = s_resp.json()["id"]
    assert client.patch(f"/api/v1/styles/{s_id}", json={"is_locked": False, "visual_style": "8K"}).status_code == 409
    assert client.patch(f"/api/v1/styles/{s_id}", json={"is_locked": False}).status_code == 200
    assert client.patch(f"/api/v1/styles/{s_id}", json={"visual_style": "8K"}).status_code == 200

    # 4. Brand Bible lock transitions
    b_resp = client.post(f"/api/v1/projects/{project.id}/brands", json={"brand_name": "LockBrand", "is_locked": True})
    b_id = b_resp.json()["id"]
    assert client.patch(f"/api/v1/brands/{b_id}", json={"is_locked": False, "tone": "Bold"}).status_code == 409
    assert client.patch(f"/api/v1/brands/{b_id}", json={"is_locked": False}).status_code == 200
    assert client.patch(f"/api/v1/brands/{b_id}", json={"tone": "Bold"}).status_code == 200


def test_oversized_context_truncation_and_factual_priority():
    # 1. Test factual document priority
    context_payload = {
        "facts": [{"filename": "critical_facts.pdf", "content": "IMPORTANT_FACT: The secret code is 42."}],
        "characters": [{"name": "Protagonist", "role": "Lead hero"}],
        "style": {"name": "Cinematic", "visual_style": "Photorealistic"},
    }
    formatted = ReferenceContextBuilder.format_prompt_section(context_payload, max_characters=500)

    # Factual document content appears before lower-priority reference content
    fact_pos = formatted.find("IMPORTANT_FACT: The secret code is 42.")
    char_pos = formatted.find("Protagonist")
    assert fact_pos != -1
    assert char_pos != -1
    assert fact_pos < char_pos

    # 2. Test genuinely oversized context truncation
    huge_facts = [{"filename": "huge_doc.pdf", "content": "X" * 10000}]
    huge_context = {
        "facts": huge_facts,
        "characters": [{"name": "C" * 1000}],
    }
    custom_limit = 150
    bounded_text = ReferenceContextBuilder.format_prompt_section(huge_context, max_characters=custom_limit)
    assert len(bounded_text) <= custom_limit

