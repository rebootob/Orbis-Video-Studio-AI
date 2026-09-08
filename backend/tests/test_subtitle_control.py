import uuid

import pytest
from fastapi import HTTPException

from app.models.project import Project
from app.models.scene import Scene
from app.models.shot import Shot
from app.models.assembly import AssemblyTimeline, AssemblyScene, AssemblyShotPlacement
from app.models.render_job import RenderJob, RenderJobStatus
from app.services.subtitle_control import PORTABLE_SUBTITLE_NAMESPACE, SubtitleService


def _make_project_timeline(db_session):
    project = Project(
        id=uuid.uuid4(),
        title="Portable Subtitle Test",
        video_mode="SHORT",
        status="DRAFT",
        mode_config={"existing_setting": True},
    )
    db_session.add(project)
    db_session.flush()

    scene = Scene(
        id=uuid.uuid4(),
        project_id=project.id,
        scene_number=1,
        narration="ข้อความบรรยายสำหรับซับไตเติล",
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
    return project, timeline


def test_portable_mirror_recovers_timeline_state_after_archive_style_loss(db_session):
    project, timeline = _make_project_timeline(db_session)

    generated = SubtitleService.generate(db_session, project.id, language="th")
    reviewed = SubtitleService.review(
        db_session,
        project.id,
        enabled=True,
        render_mode="BURN_IN",
    )
    assert reviewed["id"] != generated["id"]

    db_session.refresh(project)
    namespace = project.mode_config[PORTABLE_SUBTITLE_NAMESPACE]
    assert namespace["schema_version"] == 1
    assert len(namespace["tracks"]) == 1
    mirror = namespace["tracks"][0]
    assert mirror["timeline_version"] == timeline.version
    assert mirror["state"]["active"]["id"] == reviewed["id"]
    assert project.mode_config["existing_setting"] is True

    # Simulate current archive importer behavior for a newly cloned timeline:
    # mode_config is portable, while the timeline-local runtime cache is absent.
    timeline.subtitle_state = None
    db_session.commit()
    db_session.expire(timeline)

    recovered = SubtitleService.get_active(db_session, project.id, str(timeline.id))
    assert recovered is not None
    assert recovered["id"] == reviewed["id"]
    assert recovered["render_mode"] == "BURN_IN"
    assert recovered["is_stale"] is False


def test_active_render_freezes_subtitle_mutation(db_session):
    project, timeline = _make_project_timeline(db_session)
    SubtitleService.generate(db_session, project.id, language="th")

    render_job = RenderJob(
        id=uuid.uuid4(),
        project_id=project.id,
        timeline_id=timeline.id,
        timeline_version=timeline.version,
        approval_id=uuid.uuid4(),
        render_profile="MASTER_HD",
        render_variant_key="MASTER",
        status=RenderJobStatus.QUEUED.value,
        idempotency_key=f"test-{uuid.uuid4()}",
        estimated_cost_usd=0.0,
        imported_historical=False,
        execution_disabled=False,
    )
    db_session.add(render_job)
    db_session.commit()

    with pytest.raises(HTTPException) as review_exc:
        SubtitleService.review(
            db_session,
            project.id,
            enabled=True,
            render_mode="BURN_IN",
        )
    assert review_exc.value.status_code == 409
    assert "Subtitle state is frozen" in review_exc.value.detail

    with pytest.raises(HTTPException) as generate_exc:
        SubtitleService.generate(db_session, project.id, language="th")
    assert generate_exc.value.status_code == 409
