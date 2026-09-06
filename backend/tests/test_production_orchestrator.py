import uuid
import pytest
from app.models.project import Project
from app.models.scene import Scene
from app.models.shot import Shot
from app.models.generation_job import GenerationJob
from app.models.usage_ledger import UsageLedger
from app.services.pricing import CostStatus
from app.services.creative_generation.fake_provider import FakeCreativeGenerationProvider
from app.services.creative_generation.factory import get_creative_provider


def test_story_mode_happy_path(client, db_session):
    fake_provider = FakeCreativeGenerationProvider()
    client.app.dependency_overrides[get_creative_provider] = lambda: fake_provider

    # 1. Create Story Project
    p = Project(
        title="Epic Story",
        description="A journey through the stars",
        video_mode="STORY",
        status="DRAFT",
        automation_mode="MANUAL",
    )
    db_session.add(p)
    db_session.commit()
    p_id = str(p.id)

    # 2. Inspect initial state
    resp = client.get(f"/api/v1/projects/{p_id}/orchestration")
    assert resp.status_code == 200
    state = resp.json()
    assert state["current_stage"] == "DRAFT"
    assert state["video_mode"] == "STORY"
    assert state["recommended_action"]["action"] == "GENERATE_STORY"
    assert state["is_approval_required"] is False

    # 3. Execute GENERATE_STORY
    exec_resp = client.post(
        f"/api/v1/projects/{p_id}/orchestration/execute",
        json={"action": "GENERATE_STORY"},
    )
    assert exec_resp.status_code == 200
    exec_data = exec_resp.json()
    assert exec_data["success"] is True
    assert exec_data["to_stage"] == "STORY_GENERATED"
    assert exec_data["orchestration_state"]["current_stage"] == "STORY_GENERATED"
    assert exec_data["orchestration_state"]["is_approval_required"] is True
    assert exec_data["orchestration_state"]["recommended_action"]["action"] == "APPROVE_STORY"

    # 4. Approve Story
    appr_resp = client.post(
        f"/api/v1/projects/{p_id}/orchestration/approve",
        json={"stage": "STORY_GENERATED"},
    )
    assert appr_resp.status_code == 200
    appr_data = appr_resp.json()
    assert appr_data["success"] is True
    assert appr_data["to_stage"] == "STORY_APPROVED"
    assert appr_data["orchestration_state"]["current_stage"] == "STORY_APPROVED"
    assert appr_data["orchestration_state"]["recommended_action"]["action"] == "GENERATE_STORYBOARD"

    # 5. Execute GENERATE_STORYBOARD
    exec_sb = client.post(
        f"/api/v1/projects/{p_id}/orchestration/execute",
        json={"action": "GENERATE_STORYBOARD"},
    )
    assert exec_sb.status_code == 200
    assert exec_sb.json()["to_stage"] == "STORYBOARD_GENERATED"

    # 6. Approve Storyboard
    appr_sb = client.post(
        f"/api/v1/projects/{p_id}/orchestration/approve",
        json={"stage": "STORYBOARD_GENERATED"},
    )
    assert appr_sb.status_code == 200
    assert appr_sb.json()["to_stage"] == "STORYBOARD_APPROVED"
    assert appr_sb.json()["orchestration_state"]["recommended_action"]["action"] == "GENERATE_SHOT_PLAN"

    # 7. Execute GENERATE_SHOT_PLAN
    exec_sp = client.post(
        f"/api/v1/projects/{p_id}/orchestration/execute",
        json={"action": "GENERATE_SHOT_PLAN"},
    )
    assert exec_sp.status_code == 200
    assert exec_sp.json()["to_stage"] == "SHOT_PLAN_GENERATED"

    # 8. Approve Shot Plan
    appr_sp = client.post(
        f"/api/v1/projects/{p_id}/orchestration/approve",
        json={"stage": "SHOT_PLAN_GENERATED"},
    )
    assert appr_sp.status_code == 200
    assert appr_sp.json()["to_stage"] == "SHOT_PLAN_APPROVED"
    assert appr_sp.json()["orchestration_state"]["recommended_action"]["action"] == "START_VIDEO_GENERATION"

    # 9. Add scene and shot to test production dispatch
    sc = Scene(project_id=p.id, scene_number=1)
    db_session.add(sc)
    db_session.commit()
    sh = Shot(scene_id=sc.id, shot_number=1, shot_type="AI_GENERATED", duration_seconds=4.0, status="PENDING")
    db_session.add(sh)
    db_session.commit()

    # 10. Execute START_VIDEO_GENERATION
    exec_vg = client.post(
        f"/api/v1/projects/{p_id}/orchestration/execute",
        json={"action": "START_VIDEO_GENERATION"},
    )
    assert exec_vg.status_code == 200
    final_state = exec_vg.json()["orchestration_state"]
    assert final_state["current_stage"] == "VIDEO_IN_PROGRESS"


def test_short_mode_skips_story(client, db_session):
    p = Project(
        title="Short Video",
        video_mode="SHORT",
        status="DRAFT",
    )
    db_session.add(p)
    db_session.commit()
    p_id = str(p.id)

    resp = client.get(f"/api/v1/projects/{p_id}/orchestration")
    assert resp.status_code == 200
    state = resp.json()
    assert state["video_mode"] == "SHORT"
    assert state["current_stage"] == "DRAFT"
    assert state["recommended_action"]["action"] == "GENERATE_STORYBOARD"


def test_loop_mode_skips_story_and_storyboard(client, db_session):
    p = Project(
        title="Looping BG",
        video_mode="LOOP",
        status="DRAFT",
    )
    db_session.add(p)
    db_session.commit()
    p_id = str(p.id)

    resp = client.get(f"/api/v1/projects/{p_id}/orchestration")
    assert resp.status_code == 200
    state = resp.json()
    assert state["video_mode"] == "LOOP"
    assert state["current_stage"] == "DRAFT"
    assert state["recommended_action"]["action"] == "GENERATE_SHOT_PLAN"


def test_scene_mode_skips_story(client, db_session):
    p = Project(
        title="Scene Only",
        video_mode="SCENE",
        status="DRAFT",
    )
    db_session.add(p)
    db_session.commit()
    p_id = str(p.id)

    resp = client.get(f"/api/v1/projects/{p_id}/orchestration")
    assert resp.status_code == 200
    state = resp.json()
    assert state["video_mode"] == "SCENE"
    assert state["current_stage"] == "DRAFT"
    assert state["recommended_action"]["action"] == "GENERATE_STORYBOARD"


def test_invalid_stage_skip_rejected(client, db_session):
    p = Project(
        title="Skip Test",
        video_mode="STORY",
        status="DRAFT",
    )
    db_session.add(p)
    db_session.commit()
    p_id = str(p.id)

    # Cannot approve when in DRAFT
    bad_appr = client.post(
        f"/api/v1/projects/{p_id}/orchestration/approve",
        json={"stage": "SHOT_PLAN_APPROVED"},
    )
    assert bad_appr.status_code == 400
    assert "not awaiting human approval" in bad_appr.json()["detail"]

    # Cannot execute START_VIDEO_GENERATION when in DRAFT
    bad_exec = client.post(
        f"/api/v1/projects/{p_id}/orchestration/execute",
        json={"action": "START_VIDEO_GENERATION"},
    )
    assert bad_exec.status_code == 409
    assert "requires 'SHOT_PLAN_APPROVED' stage" in bad_exec.json()["detail"]


def test_generic_project_patch_cannot_bypass_stage_gates(client, db_session):
    p = Project(
        title="Direct Mutation Bypass Test",
        video_mode="STORY",
        status="DRAFT",
    )
    db_session.add(p)
    db_session.commit()
    p_id = str(p.id)

    resp = client.patch(
        f"/api/v1/projects/{p_id}",
        json={"status": "VIDEO_IN_PROGRESS"},
    )
    assert resp.status_code == 400
    assert "orchestration" in resp.json()["detail"].lower()

    # Project status remains DRAFT
    db_session.refresh(p)
    assert p.status == "DRAFT"


def test_idempotent_repeated_approval(client, db_session):
    p = Project(
        title="Idempotency Test",
        video_mode="STORY",
        status="STORY_APPROVED",
    )
    db_session.add(p)
    db_session.commit()
    p_id = str(p.id)

    # Repeating approval for already approved stage is NO_OP
    resp = client.post(
        f"/api/v1/projects/{p_id}/orchestration/approve",
        json={"stage": "STORY_APPROVED"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["result"] == "NO_OP"
    assert data["orchestration_state"]["current_stage"] == "STORY_APPROVED"


def test_auto_mode_stops_at_approval_gates(client, db_session):
    fake_provider = FakeCreativeGenerationProvider()
    client.app.dependency_overrides[get_creative_provider] = lambda: fake_provider

    p = Project(
        title="Auto Mode Project",
        video_mode="STORY",
        status="DRAFT",
        automation_mode="AUTO",
    )
    db_session.add(p)
    db_session.commit()
    p_id = str(p.id)

    # In AUTO mode, execute GENERATE_STORY reaches STORY_GENERATED and stops for mandatory approval
    resp = client.post(
        f"/api/v1/projects/{p_id}/orchestration/execute",
        json={"action": "GENERATE_STORY"},
    )
    assert resp.status_code == 200
    state = resp.json()["orchestration_state"]
    assert state["current_stage"] == "STORY_GENERATED"
    # Mandatory approval stops automatic cascade
    assert state["is_approval_required"] is True


def test_settings_update_automation_mode(client, db_session):
    p = Project(
        title="Settings Test",
        video_mode="STORY",
        status="DRAFT",
        automation_mode="MANUAL",
    )
    db_session.add(p)
    db_session.commit()
    p_id = str(p.id)

    resp = client.patch(
        f"/api/v1/projects/{p_id}/orchestration/settings",
        json={"automation_mode": "ASSISTED"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["automation_mode"] == "ASSISTED"

    # Verify DB updated
    db_session.refresh(p)
    assert p.automation_mode == "ASSISTED"


def test_blocked_when_active_jobs_in_flight(client, db_session):
    p = Project(
        title="Active Jobs Test",
        video_mode="STORY",
        status="SHOT_PLAN_APPROVED",
    )
    db_session.add(p)
    db_session.commit()

    sc = Scene(project_id=p.id, scene_number=1)
    db_session.add(sc)
    db_session.commit()

    sh = Shot(scene_id=sc.id, shot_number=1, shot_type="AI_GENERATED")
    db_session.add(sh)
    db_session.commit()

    job = GenerationJob(
        shot_id=sh.id,
        provider_name="vidu",
        status="PROCESSING",
    )
    db_session.add(job)
    db_session.commit()

    p_id = str(p.id)
    resp = client.get(f"/api/v1/projects/{p_id}/orchestration")
    assert resp.status_code == 200
    state = resp.json()
    assert any("active" in b.lower() for b in state["blocked_reasons"])


def test_blocked_when_reconciliation_required(client, db_session):
    p = Project(
        title="Reconciliation Test",
        video_mode="STORY",
        status="SHOT_PLAN_APPROVED",
    )
    db_session.add(p)
    db_session.commit()

    sc = Scene(project_id=p.id, scene_number=1)
    db_session.add(sc)
    db_session.commit()

    sh = Shot(scene_id=sc.id, shot_number=1, shot_type="AI_GENERATED")
    db_session.add(sh)
    db_session.commit()

    job = GenerationJob(
        shot_id=sh.id,
        provider_name="vidu",
        status="RECONCILIATION_REQUIRED",
    )
    db_session.add(job)
    db_session.commit()

    p_id = str(p.id)
    resp = client.get(f"/api/v1/projects/{p_id}/orchestration")
    assert resp.status_code == 200
    state = resp.json()
    assert any("reconciliation" in b.lower() for b in state["blocked_reasons"])
    assert state["recommended_action"]["action"] == "RESOLVE_RECONCILIATION"


def test_blocked_when_budget_exceeded(client, db_session):
    p = Project(
        title="Budget Test",
        video_mode="STORY",
        status="SHOT_PLAN_APPROVED",
        budget_limit=10.0,
    )
    db_session.add(p)
    db_session.commit()

    ledger = UsageLedger(
        project_id=p.id,
        provider="vidu",
        operation="GENERATE",
        cost_status=CostStatus.CONFIRMED,
        actual_cost=15.0,
    )
    db_session.add(ledger)
    db_session.commit()

    p_id = str(p.id)
    resp = client.get(f"/api/v1/projects/{p_id}/orchestration")
    assert resp.status_code == 200
    state = resp.json()
    assert any("budget" in b.lower() for b in state["blocked_reasons"])

    # Attempting to execute action when blocked returns 409
    exec_resp = client.post(
        f"/api/v1/projects/{p_id}/orchestration/execute",
        json={"action": "START_VIDEO_GENERATION"},
    )
    assert exec_resp.status_code == 409
    assert "budget limit exceeded" in exec_resp.json()["detail"].lower()


def test_orchestration_history_audit_logging(client, db_session):
    fake_provider = FakeCreativeGenerationProvider()
    client.app.dependency_overrides[get_creative_provider] = lambda: fake_provider

    p = Project(
        title="Audit Test",
        video_mode="STORY",
        status="DRAFT",
    )
    db_session.add(p)
    db_session.commit()
    p_id = str(p.id)

    # Perform action & approval
    client.post(f"/api/v1/projects/{p_id}/orchestration/execute", json={"action": "GENERATE_STORY"})
    client.post(f"/api/v1/projects/{p_id}/orchestration/approve", json={"stage": "STORY_GENERATED"})

    # Query history
    resp = client.get(f"/api/v1/projects/{p_id}/orchestration/history?limit=10")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 2
    actions = [item["action"] for item in data["items"]]
    assert any("APPROVE" in a for a in actions)
    assert "GENERATE_STORY" in actions
