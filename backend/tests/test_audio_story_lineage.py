"""Focused regression for S1-LIVE-01 STORY -> AudioPlan lineage."""
import uuid

from app.models.audio_clip import AudioClip, AudioType
from app.models.project import Project
from app.models.scene import Scene
from app.models.shot import Shot
from app.models.story import Story
from app.services.audio_production import AudioProductionService


def test_story_linked_scene_and_shot_feed_audio_plan(db_session):
    project = Project(
        id=uuid.uuid4(),
        title="S1-LIVE-01 STORY Audio",
        description="Canonical STORY-linked audio regression fixture",
        video_mode="STORY",
        status="VIDEO_IN_PROGRESS",
    )
    db_session.add(project)
    db_session.flush()

    story = Story(
        id=uuid.uuid4(),
        project_id=project.id,
        title="Canonical Story",
        logline="A bounded regression story",
        status="GENERATED",
    )
    db_session.add(story)
    db_session.flush()

    active_scene = Scene(
        id=uuid.uuid4(),
        story_id=story.id,
        project_id=None,
        scene_number=1,
        heading="Active STORY scene",
        narration="เสียงบรรยายสำหรับฉากหลัก",
        scene_config={},
    )
    archived_scene = Scene(
        id=uuid.uuid4(),
        story_id=story.id,
        project_id=None,
        scene_number=2,
        heading="Archived STORY scene",
        narration="ต้องไม่เข้าสู่แผนเสียง",
        scene_config={"archived": True},
    )
    db_session.add_all([active_scene, archived_scene])
    db_session.flush()

    active_shot = Shot(
        id=uuid.uuid4(),
        scene_id=active_scene.id,
        shot_number=1,
        shot_type="AI_GENERATED",
        action="ผู้บรรยายอธิบายขั้นตอนอย่างกระชับ",
        visual_prompt="A safe corporate scene",
        duration_seconds=4.0,
        status="COMPLETED",
    )
    archived_shot = Shot(
        id=uuid.uuid4(),
        scene_id=active_scene.id,
        shot_number=2,
        shot_type="AI_GENERATED",
        action="Archived shot must not create audio",
        visual_prompt="Archived visual",
        duration_seconds=4.0,
        status="ARCHIVED",
    )
    hidden_scene_shot = Shot(
        id=uuid.uuid4(),
        scene_id=archived_scene.id,
        shot_number=1,
        shot_type="AI_GENERATED",
        action="Archived scene shot must not create audio",
        visual_prompt="Archived scene visual",
        duration_seconds=4.0,
        status="COMPLETED",
    )
    db_session.add_all([active_shot, archived_shot, hidden_scene_shot])
    db_session.commit()

    plan = AudioProductionService.generate_audio_plan(db_session, project.id)

    assert plan.plan_data["summary"]["total_scenes"] == 1
    assert plan.plan_data["summary"]["total_shots"] == 1
    assert plan.plan_data["tracks"]["bgm_count"] == 1
    assert plan.plan_data["tracks"]["ambience_count"] == 1
    assert plan.plan_data["tracks"]["vo_count"] + plan.plan_data["tracks"]["dialogue_count"] == 1

    clips = db_session.query(AudioClip).filter(AudioClip.project_id == project.id).all()
    assert {clip.audio_type for clip in clips} >= {
        AudioType.BGM.value,
        AudioType.AMBIENCE.value,
        AudioType.VO.value,
    }
    assert all(clip.scene_id != archived_scene.id for clip in clips if clip.scene_id is not None)
    assert all(clip.shot_id != archived_shot.id for clip in clips if clip.shot_id is not None)
    assert all(clip.shot_id != hidden_scene_shot.id for clip in clips if clip.shot_id is not None)
