import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models.project import Project
from app.models.story import Story
from app.models.scene import Scene
from app.models.shot import Shot
from app.models.asset import Asset
from app.models.audio_clip import AudioClip
from app.models.assembly import (
    AssemblyTimeline,
    AssemblyScene,
    AssemblyShotPlacement,
    TimelineCheckpoint,
    TimelineAudit,
)
from app.services.assembly import AssemblyService, _to_uuid

client = TestClient(app)


@pytest.fixture
def test_setup(db_session: Session):
    proj_id = uuid.uuid4()
    proj = Project(
        id=proj_id,
        title="Assembly Pipeline Test Project",
        video_mode="STORY",
        status="READY_FOR_ASSEMBLY",
    )
    db_session.add(proj)

    story = Story(
        id=uuid.uuid4(),
        project_id=proj_id,
        title="Test Story",
        logline="Test Logline",
    )
    db_session.add(story)

    # 2 Scenes
    scene1 = Scene(id=uuid.uuid4(), project_id=proj_id, story_id=story.id, scene_number=1, heading="Scene 1")
    scene2 = Scene(id=uuid.uuid4(), project_id=proj_id, story_id=story.id, scene_number=2, heading="Scene 2")
    db_session.add_all([scene1, scene2])

    # 3 Shots
    shot1 = Shot(id=uuid.uuid4(), scene_id=scene1.id, shot_number=1, shot_type="WIDE", visual_prompt="Prompt 1-1")
    shot2 = Shot(id=uuid.uuid4(), scene_id=scene1.id, shot_number=2, shot_type="MEDIUM", visual_prompt="Prompt 1-2")
    shot3 = Shot(id=uuid.uuid4(), scene_id=scene2.id, shot_number=1, shot_type="CLOSEUP", visual_prompt="Prompt 2-1")
    db_session.add_all([shot1, shot2, shot3])

    # 1 Video Asset for shot1, 1 Keyframe Asset for shot2
    video_asset = Asset(
        id=uuid.uuid4(),
        project_id=proj_id,
        name="Video Asset 1",
        original_filename="video1.mp4",
        asset_type="VIDEO",
        content_type="video/mp4",
        file_size_bytes=1024,
        checksum_sha256="dummy_sha1",
        storage_bucket="default",
        storage_key="video1.mp4",
    )
    keyframe_asset = Asset(
        id=uuid.uuid4(),
        project_id=proj_id,
        name="Keyframe Asset 2",
        original_filename="keyframe2.png",
        asset_type="KEYFRAME",
        content_type="image/png",
        file_size_bytes=512,
        checksum_sha256="dummy_sha2",
        storage_bucket="default",
        storage_key="keyframe2.png",
    )
    db_session.add_all([video_asset, keyframe_asset])
    db_session.flush()

    shot1.source_asset_id = video_asset.id
    shot2.keyframe_asset_id = keyframe_asset.id

    # Add 1 Voiceover audio clip
    vo_clip = AudioClip(
        id=uuid.uuid4(),
        project_id=proj_id,
        scene_id=scene1.id,
        shot_id=shot1.id,
        audio_type="VO",
        source_type="GENERATED_AUDIO",
        generation_mode="SEPARATE_AUDIO",
        scope="SHOT",
        name="VO Shot 1",
        start_time=0.0,
        duration_seconds=4.5,
        volume=1.0,
    )
    db_session.add(vo_clip)
    db_session.commit()

    return {
        "project": proj,
        "scene1": scene1,
        "scene2": scene2,
        "shot1": shot1,
        "shot2": shot2,
        "shot3": shot3,
        "video_asset": video_asset,
        "keyframe_asset": keyframe_asset,
        "vo_clip": vo_clip,
    }


def test_auto_assemble_timeline_creates_timeline_and_scenes(db_session: Session, test_setup):
    proj_id = str(test_setup["project"].id)

    timeline = AssemblyService.auto_assemble_timeline(db_session, proj_id)
    assert timeline is not None
    assert str(timeline.project_id) == proj_id
    assert timeline.version == 1
    assert timeline.is_active is True
    assert len(timeline.scenes) == 2
    assert len(timeline.shot_placements) == 3


def test_visual_fallback_resolution(db_session: Session, test_setup):
    proj_id = str(test_setup["project"].id)
    timeline = AssemblyService.auto_assemble_timeline(db_session, proj_id)

    placements = {str(p.shot_id): p for p in timeline.shot_placements}

    # Shot 1 has video asset -> VIDEO
    p1 = placements[str(test_setup["shot1"].id)]
    assert p1.source_type == "VIDEO"
    assert str(p1.visual_asset_id) == str(test_setup["video_asset"].id)
    assert p1.effective_duration == 4.0
    assert p1.trim_out is None  # Source duration unknown

    # Shot 2 has keyframe asset -> KEYFRAME
    p2 = placements[str(test_setup["shot2"].id)]
    assert p2.source_type == "KEYFRAME"
    assert str(p2.visual_asset_id) == str(test_setup["keyframe_asset"].id)
    assert p2.effective_duration == 4.0

    # Shot 3 has no assets -> MISSING
    p3 = placements[str(test_setup["shot3"].id)]
    assert p3.source_type == "MISSING"
    assert p3.visual_asset_id is None


def test_reorder_scenes_and_shots(db_session: Session, test_setup):
    proj_id = str(test_setup["project"].id)
    timeline = AssemblyService.auto_assemble_timeline(db_session, proj_id)

    s1_id = str(test_setup["scene1"].id)
    s2_id = str(test_setup["scene2"].id)

    # Reorder scenes
    timeline = AssemblyService.reorder_scenes(db_session, proj_id, [(s1_id, 1), (s2_id, 0)])
    scenes = sorted(timeline.scenes, key=lambda s: s.scene_order)
    assert str(scenes[0].scene_id) == s2_id
    assert str(scenes[1].scene_id) == s1_id


def test_cross_scene_shot_move(db_session: Session, test_setup):
    proj_id = str(test_setup["project"].id)
    timeline = AssemblyService.auto_assemble_timeline(db_session, proj_id)

    shot1_id = str(test_setup["shot1"].id)
    target_scene2_id = str(test_setup["scene2"].id)

    # Move shot 1 to scene 2
    updated = AssemblyService.move_shot_to_scene(
        db_session, proj_id, shot_id=shot1_id, target_scene_id=target_scene2_id, target_position=1
    )
    assert updated is not None

    p1 = [p for p in updated.shot_placements if str(p.shot_id) == shot1_id][0]
    assert str(p1.scene_id) == target_scene2_id


def test_update_placement_trim_and_transition(db_session: Session, test_setup):
    proj_id = str(test_setup["project"].id)
    timeline = AssemblyService.auto_assemble_timeline(db_session, proj_id)
    p1 = timeline.shot_placements[0]

    updated_p1 = AssemblyService.update_shot_placement(
        db_session, proj_id, placement_id=str(p1.id), trim_in=1.0, trim_out=4.5, transition_to_next="FADE"
    )
    assert updated_p1.trim_in == 1.0
    assert updated_p1.trim_out == 4.5
    assert updated_p1.effective_duration == 3.5
    assert updated_p1.transition_to_next == "FADE"


def test_lock_safety_prevents_unauthorized_edits(db_session: Session, test_setup):
    proj_id = str(test_setup["project"].id)
    timeline = AssemblyService.auto_assemble_timeline(db_session, proj_id)
    p1 = timeline.shot_placements[0]

    # Lock placement
    AssemblyService.update_shot_placement(db_session, proj_id, str(p1.id), is_locked=True)

    # Attempt trim on locked placement -> fail closed
    with pytest.raises(Exception):
        AssemblyService.update_shot_placement(db_session, proj_id, str(p1.id), trim_in=2.0)


def test_checkpoint_creation_and_restore(db_session: Session, test_setup):
    proj_id = str(test_setup["project"].id)
    timeline = AssemblyService.auto_assemble_timeline(db_session, proj_id)

    ckpt = AssemblyService.create_checkpoint(db_session, proj_id, label="Cut 1 Alpha")
    assert ckpt.checkpoint_number == 1
    assert ckpt.label == "Cut 1 Alpha"

    restored = AssemblyService.restore_checkpoint(db_session, proj_id, str(ckpt.id))
    assert restored.version == 2
    assert restored.is_active is True


def test_blockers_and_recommended_fixes(db_session: Session, test_setup):
    proj_id = str(test_setup["project"].id)
    timeline = AssemblyService.auto_assemble_timeline(db_session, proj_id)

    blockers = AssemblyService.get_timeline_blockers(db_session, proj_id)
    assert len(blockers) > 0
    missing_b = [b for b in blockers if b.code == "MISSING_VISUAL"]
    assert len(missing_b) == 1
    assert len(missing_b[0].recommended_fixes) > 0


# =====================================================================
# REGRESSION TESTS FOR REVIEW 5127013489 FINDINGS
# =====================================================================

def test_auto_assembly_idempotency_manual_trim_and_transition_survive(db_session: Session, test_setup):
    proj_id = str(test_setup["project"].id)
    t1 = AssemblyService.auto_assemble_timeline(db_session, proj_id)
    p1 = t1.shot_placements[0]

    # Apply manual trim and transition edits
    updated_p1 = AssemblyService.update_shot_placement(
        db_session, proj_id, placement_id=str(p1.id), trim_in=1.5, trim_out=3.8, transition_to_next="FADE"
    )
    assert updated_p1.trim_in == 1.5
    assert updated_p1.trim_out == 3.8
    assert updated_p1.transition_to_next == "FADE"

    # Re-run Auto Assembly on unchanged project truth
    t2 = AssemblyService.auto_assemble_timeline(db_session, proj_id)
    assert t2.version == t1.version + 1
    assert len(t2.shot_placements) == 3

    p1_new = [p for p in t2.shot_placements if str(p.shot_id) == str(test_setup["shot1"].id)][0]
    assert p1_new.trim_in == 1.5
    assert p1_new.trim_out == 3.8
    assert p1_new.transition_to_next == "FADE"
    assert p1_new.effective_duration == 2.3


def test_auto_assembly_idempotency_locked_placement_survives(db_session: Session, test_setup):
    proj_id = str(test_setup["project"].id)
    t1 = AssemblyService.auto_assemble_timeline(db_session, proj_id)
    p1 = t1.shot_placements[0]

    # Lock placement
    AssemblyService.update_shot_placement(db_session, proj_id, placement_id=str(p1.id), is_locked=True)

    # Re-run Auto Assembly
    t2 = AssemblyService.auto_assemble_timeline(db_session, proj_id)
    p1_new = [p for p in t2.shot_placements if str(p.shot_id) == str(test_setup["shot1"].id)][0]
    assert p1_new.is_locked is True


def test_lock_safety_mixed_unlock_and_modify_rejected(db_session: Session, test_setup):
    proj_id = str(test_setup["project"].id)
    t1 = AssemblyService.auto_assemble_timeline(db_session, proj_id)
    p1 = t1.shot_placements[0]

    # Lock placement
    AssemblyService.update_shot_placement(db_session, proj_id, placement_id=str(p1.id), is_locked=True)

    # Attempt combined unlock + trim modification -> must be REJECTED (400)
    with pytest.raises(Exception) as exc_info:
        AssemblyService.update_shot_placement(
            db_session, proj_id, placement_id=str(p1.id), is_locked=False, trim_in=2.0
        )
    assert "400" in str(exc_info.value) or "Unlock placement first" in str(exc_info.value)

    # Isolated unlock request -> must succeed
    unlocked = AssemblyService.update_shot_placement(
        db_session, proj_id, placement_id=str(p1.id), is_locked=False
    )
    assert unlocked.is_locked is False

    # Subsequent trim request -> must succeed
    trimmed = AssemblyService.update_shot_placement(
        db_session, proj_id, placement_id=str(p1.id), trim_in=2.0
    )
    assert trimmed.trim_in == 2.0


def test_cross_project_ownership_validation_fails_closed(db_session: Session, test_setup):
    proj1_id = str(test_setup["project"].id)
    t1 = AssemblyService.auto_assemble_timeline(db_session, proj1_id)
    p1_id = str(t1.shot_placements[0].id)

    # Create project 2
    proj2 = Project(id=uuid.uuid4(), title="Project 2", video_mode="STORY")
    db_session.add(proj2)
    db_session.commit()
    proj2_id = str(proj2.id)

    # Attempt to update placement from project 1 under project 2 -> must fail closed (404)
    with pytest.raises(Exception) as exc_info:
        AssemblyService.update_shot_placement(db_session, project_id=proj2_id, placement_id=p1_id, trim_in=1.0)
    assert "404" in str(exc_info.value) or "Placement not found" in str(exc_info.value) or "Project not found" in str(exc_info.value)


def test_image_source_asset_must_not_become_video(db_session: Session, test_setup):
    proj_id = str(test_setup["project"].id)

    # Create an IMAGE asset and attach to shot3.source_asset_id
    img_asset = Asset(
        id=uuid.uuid4(),
        project_id=_to_uuid(proj_id),
        name="Image Asset 3",
        original_filename="image3.png",
        asset_type="IMAGE",
        content_type="image/png",
        file_size_bytes=512,
        checksum_sha256="dummy_sha3",
        storage_bucket="default",
        storage_key="image3.png",
    )
    db_session.add(img_asset)
    db_session.flush()

    shot3 = test_setup["shot3"]
    shot3.source_asset_id = img_asset.id
    db_session.commit()

    timeline = AssemblyService.auto_assemble_timeline(db_session, proj_id)
    p3 = [p for p in timeline.shot_placements if str(p.shot_id) == str(shot3.id)][0]

    # Must NOT become VIDEO! Must be KEYFRAME or IMAGE!
    assert p3.source_type != "VIDEO"
    assert p3.source_type in ("KEYFRAME", "IMAGE")
    assert str(p3.visual_asset_id) == str(img_asset.id)


def test_known_video_duration_used_for_trim_bounds(db_session: Session, test_setup):
    proj_id = str(test_setup["project"].id)

    # Create VIDEO asset with known duration metadata (7.5s)
    vid_asset = Asset(
        id=uuid.uuid4(),
        project_id=_to_uuid(proj_id),
        name="Video Asset 7.5s",
        original_filename="vid75.mp4",
        asset_type="VIDEO",
        content_type="video/mp4",
        file_size_bytes=2048,
        checksum_sha256="dummy_sha75",
        storage_bucket="default",
        storage_key="vid75.mp4",
    )
    setattr(vid_asset, "duration_seconds", 7.5)
    db_session.add(vid_asset)
    db_session.flush()

    shot3 = test_setup["shot3"]
    shot3.source_asset_id = vid_asset.id
    db_session.commit()

    timeline = AssemblyService.auto_assemble_timeline(db_session, proj_id)
    p3 = [p for p in timeline.shot_placements if str(p.shot_id) == str(shot3.id)][0]

    assert p3.source_type == "VIDEO"
    assert p3.trim_out == 7.5
    assert p3.effective_duration == 7.5


# =====================================================================
# REGRESSION TESTS FOR REVIEW 5127042971 FINDINGS
# =====================================================================

def test_auto_assembly_preserves_scene_reorder(db_session: Session, test_setup):
    proj_id = str(test_setup["project"].id)
    t1 = AssemblyService.auto_assemble_timeline(db_session, proj_id)
    s1_id = str(test_setup["scene1"].id)
    s2_id = str(test_setup["scene2"].id)

    # Reorder scenes: Scene 2 -> order 0, Scene 1 -> order 1
    AssemblyService.reorder_scenes(db_session, proj_id, [(s1_id, 1), (s2_id, 0)])

    # Re-run Auto Assembly
    t2 = AssemblyService.auto_assemble_timeline(db_session, proj_id)
    scenes = sorted(t2.scenes, key=lambda s: s.scene_order)
    assert str(scenes[0].scene_id) == s2_id
    assert str(scenes[1].scene_id) == s1_id


def test_auto_assembly_preserves_shot_reorder_in_scene(db_session: Session, test_setup):
    proj_id = str(test_setup["project"].id)
    t1 = AssemblyService.auto_assemble_timeline(db_session, proj_id)
    s1_id = str(test_setup["scene1"].id)
    sh1_id = str(test_setup["shot1"].id)
    sh2_id = str(test_setup["shot2"].id)

    # Reorder shots in Scene 1: Shot 2 -> order 0, Shot 1 -> order 1
    AssemblyService.reorder_shots_in_scene(db_session, proj_id, scene_id=s1_id, shot_orders=[(sh1_id, 1), (sh2_id, 0)])

    # Re-run Auto Assembly
    t2 = AssemblyService.auto_assemble_timeline(db_session, proj_id)
    s1_placements = [sc for sc in t2.scenes if str(sc.scene_id) == s1_id][0].shot_placements
    sorted_p = sorted(s1_placements, key=lambda p: p.shot_order)
    assert str(sorted_p[0].shot_id) == sh2_id
    assert str(sorted_p[1].shot_id) == sh1_id


def test_auto_assembly_preserves_cross_scene_shot_move(db_session: Session, test_setup):
    proj_id = str(test_setup["project"].id)
    t1 = AssemblyService.auto_assemble_timeline(db_session, proj_id)
    sh1_id = str(test_setup["shot1"].id)
    s2_id = str(test_setup["scene2"].id)

    # Move Shot 1 from Scene 1 to Scene 2
    AssemblyService.move_shot_to_scene(db_session, proj_id, shot_id=sh1_id, target_scene_id=s2_id, target_position=1)

    # Re-run Auto Assembly
    t2 = AssemblyService.auto_assemble_timeline(db_session, proj_id)
    p1 = [p for s in t2.scenes for p in s.shot_placements if str(p.shot_id) == sh1_id][0]
    assert str(p1.scene_id) == s2_id


def test_auto_assembly_preserves_locked_cross_scene_shot_move(db_session: Session, test_setup):
    proj_id = str(test_setup["project"].id)
    t1 = AssemblyService.auto_assemble_timeline(db_session, proj_id)
    sh1_id = str(test_setup["shot1"].id)
    s2_id = str(test_setup["scene2"].id)

    # Move Shot 1 to Scene 2 and Lock placement
    moved_t = AssemblyService.move_shot_to_scene(db_session, proj_id, shot_id=sh1_id, target_scene_id=s2_id, target_position=1)
    p1_moved = [p for s in moved_t.scenes for p in s.shot_placements if str(p.shot_id) == sh1_id][0]
    AssemblyService.update_shot_placement(db_session, proj_id, placement_id=str(p1_moved.id), is_locked=True)

    # Re-run Auto Assembly
    t2 = AssemblyService.auto_assemble_timeline(db_session, proj_id)
    p1 = [p for s in t2.scenes for p in s.shot_placements if str(p.shot_id) == sh1_id][0]
    assert str(p1.scene_id) == s2_id
    assert p1.is_locked is True


def test_unknown_video_duration_remains_none(db_session: Session, test_setup):
    proj_id = str(test_setup["project"].id)

    # Video asset without duration_seconds or metadata duration
    raw_vid_asset = Asset(
        id=uuid.uuid4(),
        project_id=_to_uuid(proj_id),
        name="Unknown Duration Video",
        original_filename="unknown.mp4",
        asset_type="VIDEO",
        content_type="video/mp4",
        file_size_bytes=1024,
        checksum_sha256="dummy_unk",
        storage_bucket="default",
        storage_key="unknown.mp4",
    )
    db_session.add(raw_vid_asset)
    db_session.flush()

    shot3 = test_setup["shot3"]
    shot3.source_asset_id = raw_vid_asset.id
    db_session.commit()

    timeline = AssemblyService.auto_assemble_timeline(db_session, proj_id)
    p3 = [p for p in timeline.shot_placements if str(p.shot_id) == str(shot3.id)][0]

    assert p3.source_type == "VIDEO"
    assert p3.trim_out is None  # Source duration remains unknown (None), not fabricated 4.0!
    assert p3.effective_duration == 4.0  # Separate UI preview fallback


from app.db.session import get_db


def test_assembly_api_endpoints(db_session: Session, test_setup):
    app.dependency_overrides[get_db] = lambda: db_session
    try:
        proj_id = str(test_setup["project"].id)

        res = client.get(f"/api/v1/projects/{proj_id}/assembly")
        assert res.status_code == 200
        data = res.json()
        assert data["project_id"] == proj_id
        assert data["scene_count"] == 2
        assert data["shot_count"] == 3

        # Checkpoints endpoint
        cp_res = client.post(f"/api/v1/projects/{proj_id}/assembly/checkpoints", json={"label": "API Checkpoint"})
        assert cp_res.status_code == 200
        cp_data = cp_res.json()
        assert cp_data["label"] == "API Checkpoint"
    finally:
        app.dependency_overrides.clear()
