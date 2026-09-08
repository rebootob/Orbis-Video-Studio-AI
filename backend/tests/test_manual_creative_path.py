from app.models.orchestration_audit import OrchestrationAudit
from app.models.story import Story
from app.models.story_version import StoryVersion
from app.models.usage_ledger import UsageLedger
from app.services.creative_generation.openai_provider import OpenAICreativeGenerationProvider


def _forbid_openai(monkeypatch):
    def fail_if_called(*args, **kwargs):
        raise AssertionError("CreativeProvider must not be called by MANUAL creative path")

    monkeypatch.setattr(
        OpenAICreativeGenerationProvider,
        "_execute_completion",
        fail_if_called,
    )


def _create_project(client, *, title, video_mode, automation_mode="MANUAL"):
    response = client.post(
        "/api/v1/projects",
        json={
            "title": title,
            "description": "Manual zero-provider acceptance project",
            "video_mode": video_mode,
            "automation_mode": automation_mode,
            "mode_config": {"automation_level": automation_mode, "language": "Thai"},
            "target_duration_seconds": 30,
            "preferred_aspect_ratio": "16:9",
        },
    )
    assert response.status_code == 201, response.text
    assert response.json()["automation_mode"] == automation_mode
    return response.json()


def _approve(client, project_id, generated_stage):
    response = client.post(
        f"/api/v1/projects/{project_id}/orchestration/approve",
        json={"stage": generated_stage},
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_manual_story_mode_reaches_shot_plan_approved_without_creative_provider(
    client, db_session, monkeypatch
):
    _forbid_openai(monkeypatch)
    project = _create_project(client, title="Manual Story", video_mode="STORY")
    project_id = project["id"]

    initial = client.get(f"/api/v1/projects/{project_id}/orchestration")
    assert initial.status_code == 200
    initial_state = initial.json()
    assert initial_state["automation_mode"] == "MANUAL"
    assert initial_state["recommended_action"]["action"] == "SUBMIT_MANUAL_STORY"
    assert initial_state["recommended_action"]["is_chargeable"] is False
    assert initial_state["recommended_action"]["is_blocked"] is True

    first_story = client.put(
        f"/api/v1/projects/{project_id}/story/manual",
        json={
            "title": "Manual Story Title",
            "logline": "A manually authored corporate story.",
            "synopsis": "Beginning, conflict, resolution — authored without CreativeProvider.",
            "tone": "corporate documentary",
            "target_duration_seconds": 30,
            "language": "th",
        },
    )
    assert first_story.status_code == 200, first_story.text
    assert first_story.json()["version_number"] == 1

    second_story = client.put(
        f"/api/v1/projects/{project_id}/story/manual",
        json={
            "title": "Manual Story Title v2",
            "logline": "A revised manually authored corporate story.",
            "synopsis": "Revised narrative with retained version history.",
            "tone": "corporate documentary",
            "target_duration_seconds": 30,
            "language": "th",
        },
    )
    assert second_story.status_code == 200, second_story.text
    assert second_story.json()["version_number"] == 2
    assert db_session.query(StoryVersion).filter(StoryVersion.project_id == project_id).count() == 1

    ready_story = client.get(f"/api/v1/projects/{project_id}/orchestration").json()
    assert ready_story["recommended_action"]["action"] == "SUBMIT_MANUAL_STORY"
    assert ready_story["recommended_action"]["is_blocked"] is False

    submit_story = client.post(
        f"/api/v1/projects/{project_id}/orchestration/execute",
        json={"action": "SUBMIT_MANUAL_STORY"},
    )
    assert submit_story.status_code == 200, submit_story.text
    assert submit_story.json()["to_stage"] == "STORY_GENERATED"
    assert _approve(client, project_id, "STORY_GENERATED")["to_stage"] == "STORY_APPROVED"

    scene = client.post(
        f"/api/v1/projects/{project_id}/scenes",
        json={
            "scene_number": 1,
            "heading": "INT. TRAINING ROOM - DAY",
            "description": "Employees review a new safety workflow.",
            "purpose": "Establish the learning objective",
            "setting": "Bright corporate training room",
            "duration_seconds": 8,
            "narration": "วันนี้เราจะเรียนรู้ขั้นตอนใหม่ร่วมกัน",
            "dialogue": "หัวหน้าทีม: เริ่มจากความปลอดภัยก่อน",
        },
    )
    assert scene.status_code == 201, scene.text
    scene_id = scene.json()["id"]

    storyboard_state = client.get(f"/api/v1/projects/{project_id}/orchestration").json()
    assert storyboard_state["recommended_action"]["action"] == "SUBMIT_MANUAL_STORYBOARD"
    assert storyboard_state["recommended_action"]["is_chargeable"] is False

    submit_storyboard = client.post(
        f"/api/v1/projects/{project_id}/orchestration/execute",
        json={"action": "SUBMIT_MANUAL_STORYBOARD"},
    )
    assert submit_storyboard.status_code == 200, submit_storyboard.text
    assert submit_storyboard.json()["to_stage"] == "STORYBOARD_GENERATED"
    assert _approve(client, project_id, "STORYBOARD_GENERATED")["to_stage"] == "STORYBOARD_APPROVED"

    shot = client.post(
        f"/api/v1/scenes/{scene_id}/shots",
        json={
            "shot_number": 1,
            "shot_type": "AI_GENERATED",
            "visual_prompt": "Wide corporate training room, Thai employees listening attentively",
            "camera": "Slow dolly in",
            "subject": "Training facilitator and employees",
            "action": "Facilitator explains the first safety step",
            "duration_seconds": 4,
        },
    )
    assert shot.status_code == 201, shot.text

    shot_state = client.get(f"/api/v1/projects/{project_id}/orchestration").json()
    assert shot_state["recommended_action"]["action"] == "SUBMIT_MANUAL_SHOT_PLAN"
    assert shot_state["recommended_action"]["is_chargeable"] is False

    submit_plan = client.post(
        f"/api/v1/projects/{project_id}/orchestration/execute",
        json={"action": "SUBMIT_MANUAL_SHOT_PLAN"},
    )
    assert submit_plan.status_code == 200, submit_plan.text
    assert submit_plan.json()["to_stage"] == "SHOT_PLAN_GENERATED"
    approved = _approve(client, project_id, "SHOT_PLAN_GENERATED")
    assert approved["to_stage"] == "SHOT_PLAN_APPROVED"

    assert db_session.query(UsageLedger).filter(UsageLedger.project_id == project_id).count() == 0
    story = db_session.query(Story).filter(Story.project_id == project_id).one()
    assert story.title == "Manual Story Title v2"

    actions = {
        row.action
        for row in db_session.query(OrchestrationAudit)
        .filter(OrchestrationAudit.project_id == project_id)
        .all()
    }
    assert "MANUAL_STORY_CREATE" in actions
    assert "MANUAL_STORY_UPDATE" in actions
    assert "SUBMIT_MANUAL_STORY" in actions
    assert "SUBMIT_MANUAL_STORYBOARD" in actions
    assert "SUBMIT_MANUAL_SHOT_PLAN" in actions


def test_manual_scene_mode_reaches_shot_plan_approved_without_story_or_provider(
    client, db_session, monkeypatch
):
    _forbid_openai(monkeypatch)
    project = _create_project(client, title="Manual Scene", video_mode="SCENE")
    project_id = project["id"]

    initial = client.get(f"/api/v1/projects/{project_id}/orchestration").json()
    assert initial["recommended_action"]["action"] == "SUBMIT_MANUAL_STORYBOARD"
    assert initial["recommended_action"]["is_blocked"] is True

    scene = client.post(
        f"/api/v1/projects/{project_id}/scenes",
        json={
            "scene_number": 1,
            "heading": "EXT. FACTORY WALKWAY - DAY",
            "description": "A supervisor checks the line.",
            "setting": "Factory",
            "duration_seconds": 6,
        },
    )
    assert scene.status_code == 201, scene.text
    scene_id = scene.json()["id"]

    submitted = client.post(
        f"/api/v1/projects/{project_id}/orchestration/execute",
        json={"action": "SUBMIT_MANUAL_STORYBOARD"},
    )
    assert submitted.status_code == 200, submitted.text
    assert _approve(client, project_id, "STORYBOARD_GENERATED")["to_stage"] == "STORYBOARD_APPROVED"

    shot = client.post(
        f"/api/v1/scenes/{scene_id}/shots",
        json={
            "shot_number": 1,
            "shot_type": "AI_GENERATED",
            "visual_prompt": "Supervisor walking along a clean production line",
            "camera": "Medium tracking shot",
            "action": "Supervisor inspects workstations",
            "duration_seconds": 4,
        },
    )
    assert shot.status_code == 201, shot.text

    submitted_plan = client.post(
        f"/api/v1/projects/{project_id}/orchestration/execute",
        json={"action": "SUBMIT_MANUAL_SHOT_PLAN"},
    )
    assert submitted_plan.status_code == 200, submitted_plan.text
    assert _approve(client, project_id, "SHOT_PLAN_GENERATED")["to_stage"] == "SHOT_PLAN_APPROVED"

    assert db_session.query(Story).filter(Story.project_id == project_id).count() == 0
    assert db_session.query(UsageLedger).filter(UsageLedger.project_id == project_id).count() == 0


def test_assisted_and_auto_keep_provider_backed_recommended_actions(client):
    for mode in ("ASSISTED", "AUTO"):
        project = _create_project(
            client,
            title=f"{mode} Story",
            video_mode="STORY",
            automation_mode=mode,
        )
        state = client.get(
            f"/api/v1/projects/{project['id']}/orchestration"
        ).json()
        assert state["automation_mode"] == mode
        assert state["recommended_action"]["action"] == "GENERATE_STORY"
        assert state["recommended_action"]["is_chargeable"] is True
