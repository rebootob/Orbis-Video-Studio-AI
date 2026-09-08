import uuid

import pytest
from fastapi import HTTPException

from app.models.project import Project
from app.models.scene import Scene
from app.models.shot import Shot
from app.models.assembly import AssemblyTimeline, AssemblyScene, AssemblyShotPlacement
from app.services.subtitle import SubtitleService, build_srt


def _make_timeline(db_session, *, video_mode: str = "SHORT"):
    project = Project(
        id=uuid.uuid4(),
        title="Subtitle Test",
        video_mode=video_mode,
        status="DRAFT",
    )
    db_session.add(project)
    db_session.flush()

    scene = Scene(
        id=uuid.uuid4(),
        project_id=project.id,
        scene_number=1,
        heading="Opening",
        narration="สวัสดีจาก Orbis",
        dialogue=[{"speaker": "Host", "text": "ยินดีต้อนรับ"}],
    )
    db_session.add(scene)
    db_session.flush()

    shot = Shot(
        id=uuid.uuid4(),
        scene_id=scene.id,
        shot_number=1,
        shot_type="AI_GENERATED",
        duration_seconds=4.0,
    )
    db_session.add(shot)
    db_session.flush()

    timeline = AssemblyTimeline(
        id=uuid.uuid4(),
        project_id=project.id,
        version=1,
        status="DRAFT",
        is_active=True,
    )
    db_session.add(timeline)
    db_session.flush()

    assembly_scene = AssemblyScene(
        id=uuid.uuid4(),
        timeline_id=timeline.id,
        scene_id=scene.id,
        scene_order=0,
    )
    db_session.add(assembly_scene)
    db_session.flush()

    placement = AssemblyShotPlacement(
        id=uuid.uuid4(),
        timeline_id=timeline.id,
        assembly_scene_id=assembly_scene.id,
        scene_id=scene.id,
        shot_id=shot.id,
        shot_order=0,
        source_type="IMAGE",
        effective_duration=4.0,
        still_duration=4.0,
        transition_to_next="CUT",
    )
    db_session.add(placement)
    db_session.commit()
    db_session.refresh(timeline)
    return project, scene, shot, timeline, placement


def test_generate_review_export_and_history(db_session):
    project, _scene, _shot, timeline, _placement = _make_timeline(db_session)

    generated = SubtitleService.generate(db_session, project.id, language="th")
    assert generated["timeline_version"] == 1
    assert generated["language"] == "th"
    assert generated["is_stale"] is False
    assert generated["review_status"] == "GENERATED"
    assert len(generated["segments"]) == 2
    assert generated["segments"][0]["end_time"] <= generated["segments"][1]["start_time"]
    assert "00:00:00,000 -->" in generated["srt_content"]
    assert generated["srt_sha256"]

    reviewed = SubtitleService.review(
        db_session,
        project.id,
        enabled=True,
        render_mode="BURN_IN",
    )
    assert reviewed["is_reviewed"] is True
    assert reviewed["render_mode"] == "BURN_IN"
    assert reviewed["is_stale"] is False
    assert reviewed["version_number"] == 2

    db_session.refresh(timeline)
    assert len(timeline.subtitle_state["history"]) == 1
    assert timeline.subtitle_state["history"][0]["review_status"] == "GENERATED"

    content, evidence = SubtitleService.export_srt(db_session, project.id)
    assert "สวัสดีจาก Orbis" in content
    assert evidence["track_id"] == reviewed["id"]
    assert evidence["sha256"] == reviewed["srt_sha256"]


def test_timeline_edit_marks_subtitles_stale_and_review_fails_closed(db_session):
    project, _scene, _shot, _timeline, placement = _make_timeline(db_session)
    SubtitleService.generate(db_session, project.id, language="th")

    placement.effective_duration = 6.0
    placement.still_duration = 6.0
    placement.version += 1
    db_session.commit()

    active = SubtitleService.get_active(db_session, project.id)
    assert active is not None
    assert active["is_stale"] is True

    with pytest.raises(HTTPException) as exc:
        SubtitleService.review(db_session, project.id, enabled=True, render_mode="BURN_IN")
    assert exc.value.status_code == 409

    with pytest.raises(HTTPException) as exc:
        SubtitleService.export_srt(db_session, project.id)
    assert exc.value.status_code == 409


def test_generate_requires_authoritative_text(db_session):
    project, scene, _shot, _timeline, _placement = _make_timeline(db_session)
    scene.narration = None
    scene.dialogue = None
    db_session.commit()

    with pytest.raises(HTTPException) as exc:
        SubtitleService.generate(db_session, project.id)
    assert exc.value.status_code == 400
    assert "authoritative subtitle text" in exc.value.detail


def test_srt_formatter_is_deterministic_and_nonempty():
    segments = [
        {
            "text": "Hello",
            "start_time": 1.25,
            "end_time": 2.5,
        },
        {
            "text": "World",
            "start_time": 2.5,
            "end_time": 3.0,
        },
    ]
    assert build_srt(segments) == (
        "1\n00:00:01,250 --> 00:00:02,500\nHello\n\n"
        "2\n00:00:02,500 --> 00:00:03,000\nWorld\n"
    )
