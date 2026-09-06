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
from app.services.assembly import AssemblyService

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
        db_session, proj_id, placement_id=p1.id, trim_in=1.0, trim_out=4.5, transition_to_next="FADE"
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
    AssemblyService.update_shot_placement(db_session, proj_id, p1.id, is_locked=True)

    # Attempt trim on locked placement -> fail closed
    with pytest.raises(Exception):
        AssemblyService.update_shot_placement(db_session, proj_id, p1.id, trim_in=2.0)


def test_checkpoint_creation_and_restore(db_session: Session, test_setup):
    proj_id = str(test_setup["project"].id)
    timeline = AssemblyService.auto_assemble_timeline(db_session, proj_id)

    ckpt = AssemblyService.create_checkpoint(db_session, proj_id, label="Cut 1 Alpha")
    assert ckpt.checkpoint_number == 1
    assert ckpt.label == "Cut 1 Alpha"

    restored = AssemblyService.restore_checkpoint(db_session, proj_id, ckpt.id)
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
