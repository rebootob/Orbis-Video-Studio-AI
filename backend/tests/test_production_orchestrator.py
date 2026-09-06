import uuid
import pytest
from app.models.project import Project
from app.models.story import Story
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

    # 3. Execute GENERATE_STORY -> actually creates Story artifact
    exec_resp = client.post(
        f"/api/v1/projects/{p_id}/orchestration/execute",
        json={"action": "GENERATE_STORY"},
    )
    assert exec_resp.status_code == 200
    exec_data = exec_resp.json()
    assert exec_data["success"] is True
    assert exec_data["to_stage"] == "STORY_GENERATED"
    story = db_session.query(Story).filter(Story.project_id == p.id).first()
    assert story is not None
    assert story.title is not None

    # 4. Approve Story
    appr_resp = client.post(
        f"/api/v1/projects/{p_id}/orchestration/approve",
        json={"stage": "STORY_GENERATED"},
    )
    assert appr_resp.status_code == 200
    appr_data = appr_resp.json()
    assert appr_data["success"] is True
    assert appr_data["to_stage"] == "STORY_APPROVED"

    # 5. Execute GENERATE_STORYBOARD -> actually creates Scene artifacts
    exec_sb = client.post(
        f"/api/v1/projects/{p_id}/orchestration/execute",
        json={"action": "GENERATE_STORYBOARD"},
    )
    assert exec_sb.status_code == 200
    assert exec_sb.json()["to_stage"] == "STORYBOARD_GENERATED"
    scenes = db_session.query(Scene).filter(Scene.story_id == story.id).all()
    assert len(scenes) >= 1

    # 6. Approve Storyboard
    appr_sb = client.post(
        f"/api/v1/projects/{p_id}/orchestration/approve",
        json={"stage": "STORYBOARD_GENERATED"},
    )
    assert appr_sb.status_code == 200
    assert appr_sb.json()["to_stage"] == "STORYBOARD_APPROVED"

    # 7. Execute GENERATE_SHOT_PLAN -> actually creates Shot artifacts
    exec_sp = client.post(
        f"/api/v1/projects/{p_id}/orchestration/execute",
        json={"action": "GENERATE_SHOT_PLAN"},
    )
    assert exec_sp.status_code == 200
    assert exec_sp.json()["to_stage"] == "SHOT_PLAN_GENERATED"
    shots = (
        db_session.query(Shot)
        .join(Scene, Shot.scene_id == Scene.id)
        .filter(Scene.story_id == story.id)
        .all()
    )
    assert len(shots) >= 1

    # 8. Approve Shot Plan
    appr_sp = client.post(
        f"/api/v1/projects/{p_id}/orchestration/approve",
        json={"stage": "SHOT_PLAN_GENERATED"},
    )
    assert appr_sp.status_code == 200
    assert appr_sp.json()["to_stage"] == "SHOT_PLAN_APPROVED"
    assert appr_sp.json()["orchestration_state"]["recommended_action"]["action"] == "START_VIDEO_GENERATION"

    # 9. Execute START_VIDEO_GENERATION
    exec_vg = client.post(
        f"/api/v1/projects/{p_id}/orchestration/execute",
        json={"action": "START_VIDEO_GENERATION"},
    )
    assert exec_vg.status_code == 200
    final_state = exec_vg.json()["orchestration_state"]
    assert final_state["current_stage"] == "VIDEO_IN_PROGRESS"


def test_short_mode_skips_story(client, db_session):
    fake_provider = FakeCreativeGenerationProvider()
    client.app.dependency_overrides[get_creative_provider] = lambda: fake_provider

    p = Project(
        title="Short Video",
        description="Quick short-form hook",
        video_mode="SHORT",
        status="DRAFT",
    )
    db_session.add(p)
    db_session.commit()
    p_id = str(p.id)

    # Initial action should be GENERATE_STORYBOARD, skipping Story outline
    resp = client.get(f"/api/v1/projects/{p_id}/orchestration")
    assert resp.status_code == 200
    state = resp.json()
    assert state["video_mode"] == "SHORT"
    assert state["recommended_action"]["action"] == "GENERATE_STORYBOARD"

    # Execute GENERATE_STORYBOARD
    exec_resp = client.post(
        f"/api/v1/projects/{p_id}/orchestration/execute",
        json={"action": "GENERATE_STORYBOARD"},
    )
    assert exec_resp.status_code == 200
    assert exec_resp.json()["to_stage"] == "STORYBOARD_GENERATED"
    # Ensure no Story record was created
    story = db_session.query(Story).filter(Story.project_id == p.id).first()
    assert story is None


def test_loop_mode_shot_plan(client, db_session):
    fake_provider = FakeCreativeGenerationProvider()
    client.app.dependency_overrides[get_creative_provider] = lambda: fake_provider

    p = Project(
        title="Background Loop",
        description="Seamless ambient loop",
        video_mode="LOOP",
        status="DRAFT",
    )
    db_session.add(p)
    db_session.commit()
    p_id = str(p.id)

    # LOOP mode goes directly to GENERATE_SHOT_PLAN
    resp = client.get(f"/api/v1/projects/{p_id}/orchestration")
    assert resp.status_code == 200
    state = resp.json()
    assert state["video_mode"] == "LOOP"
    assert state["recommended_action"]["action"] == "GENERATE_SHOT_PLAN"

    # Execute shot plan
    exec_resp = client.post(
        f"/api/v1/projects/{p_id}/orchestration/execute",
        json={"action": "GENERATE_SHOT_PLAN"},
    )
    assert exec_resp.status_code == 200
    assert exec_resp.json()["to_stage"] == "SHOT_PLAN_GENERATED"


def test_scene_mode_skips_story(client, db_session):
    fake_provider = FakeCreativeGenerationProvider()
    client.app.dependency_overrides[get_creative_provider] = lambda: fake_provider

    p = Project(
        title="Scene Production",
        description="Independent scene visual layout",
        video_mode="SCENE",
        status="DRAFT",
    )
    db_session.add(p)
    db_session.commit()
    p_id = str(p.id)

    resp = client.get(f"/api/v1/projects/{p_id}/orchestration")
    assert resp.status_code == 200
    assert resp.json()["recommended_action"]["action"] == "GENERATE_STORYBOARD"


def test_no_generated_state_without_artifact(client, db_session):
    """If generation fails (e.g. no source context), stage must NOT advance to GENERATED."""
    fake_provider = FakeCreativeGenerationProvider()
    client.app.dependency_overrides[get_creative_provider] = lambda: fake_provider

    p = Project(
        title="Empty Project",
        description="",  # No context
        video_mode="STORY",
        status="DRAFT",
    )
    db_session.add(p)
    db_session.commit()
    p_id = str(p.id)

    resp = client.post(
        f"/api/v1/projects/{p_id}/orchestration/execute",
        json={"action": "GENERATE_STORY"},
    )
    assert resp.status_code == 400
    db_session.refresh(p)
    assert p.status == "DRAFT"  # Remains in DRAFT, not marked STORY_GENERATED!


def test_auto_mode_safe_continuation_and_mandatory_stops(client, db_session):
    """AUTO mode automatically cascades safe creative planning steps upon approval,
    but stops at mandatory human review gates and chargeable video generation gates.
    """
    fake_provider = FakeCreativeGenerationProvider()
    client.app.dependency_overrides[get_creative_provider] = lambda: fake_provider

    p = Project(
        title="Auto Mode Project",
        description="A sci-fi adventure brief",
        video_mode="STORY",
        status="DRAFT",
        automation_mode="AUTO",
    )
    db_session.add(p)
    db_session.commit()
    p_id = str(p.id)

    # 1. Execute GENERATE_STORY -> reaches STORY_GENERATED and STOPS for mandatory human approval
    resp = client.post(
        f"/api/v1/projects/{p_id}/orchestration/execute",
        json={"action": "GENERATE_STORY"},
    )
    assert resp.status_code == 200
    state = resp.json()["orchestration_state"]
    assert state["current_stage"] == "STORY_GENERATED"
    assert state["is_approval_required"] is True

    # 2. Human approves STORY_GENERATED
    # In AUTO mode, approving story automatically continues to GENERATE_STORYBOARD
    # and reaches STORYBOARD_GENERATED, then stops for human review!
    appr_resp = client.post(
        f"/api/v1/projects/{p_id}/orchestration/approve",
        json={"stage": "STORY_GENERATED"},
    )
    assert appr_resp.status_code == 200
    appr_state = appr_resp.json()["orchestration_state"]
    assert appr_state["current_stage"] == "STORYBOARD_GENERATED"
    assert appr_state["is_approval_required"] is True

    # 3. Human approves STORYBOARD_GENERATED
    # In AUTO mode, approving storyboard automatically continues to GENERATE_SHOT_PLAN
    # and reaches SHOT_PLAN_GENERATED, then stops for human review!
    appr_sb = client.post(
        f"/api/v1/projects/{p_id}/orchestration/approve",
        json={"stage": "STORYBOARD_GENERATED"},
    )
    assert appr_sb.status_code == 200
    sb_state = appr_sb.json()["orchestration_state"]
    assert sb_state["current_stage"] == "SHOT_PLAN_GENERATED"
    assert sb_state["is_approval_required"] is True

    # 4. Human approves SHOT_PLAN_GENERATED
    # In AUTO mode, approving shot plan reaches SHOT_PLAN_APPROVED.
    # It MUST STOP at SHOT_PLAN_APPROVED because video generation is CHARGEABLE!
    appr_sp = client.post(
        f"/api/v1/projects/{p_id}/orchestration/approve",
        json={"stage": "SHOT_PLAN_GENERATED"},
    )
    assert appr_sp.status_code == 200
    sp_state = appr_sp.json()["orchestration_state"]
    assert sp_state["current_stage"] == "SHOT_PLAN_APPROVED"
    assert sp_state["recommended_action"]["action"] == "START_VIDEO_GENERATION"
    assert sp_state["recommended_action"]["is_chargeable"] is True
    # Verify it did not silently dispatch video generation jobs
    db_session.refresh(p)
    assert p.status == "SHOT_PLAN_APPROVED"


def test_assisted_mode_does_not_silently_charge(client, db_session):
    p = Project(
        title="Assisted Project",
        description="Assisted mode brief",
        video_mode="STORY",
        status="SHOT_PLAN_APPROVED",
        automation_mode="ASSISTED",
    )
    db_session.add(p)
    db_session.commit()
    p_id = str(p.id)

    resp = client.get(f"/api/v1/projects/{p_id}/orchestration")
    assert resp.status_code == 200
    state = resp.json()
    assert state["recommended_action"]["action"] == "START_VIDEO_GENERATION"
    assert state["recommended_action"]["is_chargeable"] is True
    db_session.refresh(p)
    assert p.status == "SHOT_PLAN_APPROVED"


def test_fail_closed_draft_cannot_approve_story_directly(client, db_session):
    """Direct approval shortcut from DRAFT to STORY_APPROVED must fail closed."""
    p = Project(
        title="Draft Project",
        description="Testing bypass",
        video_mode="STORY",
        status="DRAFT",
    )
    db_session.add(p)
    db_session.commit()
    p_id = str(p.id)

    resp = client.post(
        f"/api/v1/projects/{p_id}/orchestration/approve",
        json={"stage": "STORY_APPROVED"},
    )
    assert resp.status_code == 400
    assert "not awaiting human approval" in resp.json()["detail"].lower()


def test_fail_closed_wrong_approval_action_rejected(client, db_session):
    """Approving a mismatched gate must be rejected with 400."""
    p = Project(
        title="Generated Story",
        description="Testing wrong approval",
        video_mode="STORY",
        status="STORY_GENERATED",
    )
    db_session.add(p)
    db_session.commit()
    p_id = str(p.id)

    # Try approving storyboard while at story generated
    resp = client.post(
        f"/api/v1/projects/{p_id}/orchestration/approve",
        json={"stage": "STORYBOARD_APPROVED"},
    )
    assert resp.status_code == 400
    assert "out of order" in resp.json()["detail"].lower()

    # Try executing APPROVE_STORYBOARD via execute endpoint
    resp2 = client.post(
        f"/api/v1/projects/{p_id}/orchestration/execute",
        json={"action": "APPROVE_STORYBOARD"},
    )
    assert resp2.status_code == 400


def test_fail_closed_invalid_revision_and_final_transitions_rejected(client, db_session):
    p = Project(
        title="Test Guards",
        description="Guard checks",
        video_mode="STORY",
        status="DRAFT",
    )
    db_session.add(p)
    db_session.commit()
    p_id = str(p.id)

    # 1. TRANSITION_TO_FINAL_REVIEW from DRAFT must fail
    resp = client.post(
        f"/api/v1/projects/{p_id}/orchestration/execute",
        json={"action": "TRANSITION_TO_FINAL_REVIEW"},
    )
    assert resp.status_code == 400

    # 2. Revisions from COMPLETED must fail
    p.status = "COMPLETED"
    db_session.commit()
    resp2 = client.post(
        f"/api/v1/projects/{p_id}/orchestration/execute",
        json={"action": "REVISE_STORY"},
    )
    assert resp2.status_code == 400


def test_happy_path_video_in_progress_to_final_review_to_completed(client, db_session):
    """VIDEO_IN_PROGRESS -> TRANSITION_TO_FINAL_REVIEW -> FINAL_REVIEW -> APPROVE_FINAL -> COMPLETED"""
    p = Project(
        title="Final Review Test",
        video_mode="STORY",
        status="VIDEO_IN_PROGRESS",
    )
    db_session.add(p)
    db_session.commit()

    sc = Scene(project_id=p.id, scene_number=1)
    db_session.add(sc)
    db_session.commit()

    sh = Shot(scene_id=sc.id, shot_number=1, shot_type="AI_GENERATED", status="COMPLETED")
    db_session.add(sh)
    db_session.commit()

    job = GenerationJob(id=uuid.uuid4(), shot_id=sh.id, provider_name="vidu", status="COMPLETED")
    db_session.add(job)
    db_session.commit()
    p_id = str(p.id)

    # 1. While in VIDEO_IN_PROGRESS with 0 active and all completed:
    # State evaluation preserves current_stage as VIDEO_IN_PROGRESS, recommends TRANSITION_TO_FINAL_REVIEW
    resp = client.get(f"/api/v1/projects/{p_id}/orchestration")
    assert resp.status_code == 200
    state = resp.json()
    assert state["current_stage"] == "VIDEO_IN_PROGRESS"
    assert state["recommended_action"]["action"] == "TRANSITION_TO_FINAL_REVIEW"

    # 2. Execute TRANSITION_TO_FINAL_REVIEW -> stage becomes FINAL_REVIEW
    resp_trans = client.post(
        f"/api/v1/projects/{p_id}/orchestration/execute",
        json={"action": "TRANSITION_TO_FINAL_REVIEW"},
    )
    assert resp_trans.status_code == 200
    assert resp_trans.json()["to_stage"] == "FINAL_REVIEW"

    # 3. State evaluation at FINAL_REVIEW recommends APPROVE_FINAL
    resp2 = client.get(f"/api/v1/projects/{p_id}/orchestration")
    assert resp2.status_code == 200
    assert resp2.json()["current_stage"] == "FINAL_REVIEW"
    assert resp2.json()["recommended_action"]["action"] == "APPROVE_FINAL"

    # 4. Approve final cut -> transitions to COMPLETED
    resp_appr = client.post(
        f"/api/v1/projects/{p_id}/orchestration/approve",
        json={"stage": "FINAL_REVIEW"},
    )
    assert resp_appr.status_code == 200
    assert resp_appr.json()["to_stage"] == "COMPLETED"
    db_session.refresh(p)
    assert p.status == "COMPLETED"


def test_resolve_reconciliation_action(client, db_session):
    p = Project(
        title="Reconciliation Project",
        video_mode="STORY",
        status="VIDEO_IN_PROGRESS",
    )
    db_session.add(p)
    db_session.commit()

    sc = Scene(project_id=p.id, scene_number=1)
    db_session.add(sc)
    db_session.commit()

    sh = Shot(scene_id=sc.id, shot_number=1, shot_type="AI_GENERATED")
    db_session.add(sh)
    db_session.commit()

    job = GenerationJob(id=uuid.uuid4(), shot_id=sh.id, provider_name="vidu", status="RECONCILIATION_REQUIRED")
    db_session.add(job)
    db_session.commit()
    p_id = str(p.id)

    # State should recommend RESOLVE_RECONCILIATION
    resp = client.get(f"/api/v1/projects/{p_id}/orchestration")
    assert resp.status_code == 200
    assert resp.json()["recommended_action"]["action"] == "RESOLVE_RECONCILIATION"

    # Execute RESOLVE_RECONCILIATION -> reconciles to FAILED
    resp_res = client.post(
        f"/api/v1/projects/{p_id}/orchestration/execute",
        json={"action": "RESOLVE_RECONCILIATION"},
    )
    assert resp_res.status_code == 200
    db_session.refresh(job)
    assert job.status == "FAILED"


def test_poll_status_and_view_summary_non_failing(client, db_session):
    p = Project(
        title="Nav Actions",
        video_mode="STORY",
        status="COMPLETED",
    )
    db_session.add(p)
    db_session.commit()
    p_id = str(p.id)

    # POLL_STATUS succeeds with NO_OP
    resp1 = client.post(
        f"/api/v1/projects/{p_id}/orchestration/execute",
        json={"action": "POLL_STATUS"},
    )
    assert resp1.status_code == 200
    assert resp1.json()["result"] == "NO_OP"

    # VIEW_SUMMARY succeeds with NO_OP
    resp2 = client.post(
        f"/api/v1/projects/{p_id}/orchestration/execute",
        json={"action": "VIEW_SUMMARY"},
    )
    assert resp2.status_code == 200
    assert resp2.json()["result"] == "NO_OP"


def test_locked_only_batch_produces_truthful_blocked_no_op_outcome(client, db_session):
    """When all candidate shots are locked, batch execution produces truthful NO_OP/BLOCKED without starting video."""
    p = Project(
        title="Locked Project",
        video_mode="STORY",
        status="SHOT_PLAN_APPROVED",
    )
    db_session.add(p)
    db_session.commit()

    sc = Scene(project_id=p.id, scene_number=1)
    db_session.add(sc)
    db_session.commit()

    sh = Shot(scene_id=sc.id, shot_number=1, shot_type="AI_GENERATED", is_locked=True)
    db_session.add(sh)
    db_session.commit()
    p_id = str(p.id)

    # State shows blocked reason for locked shots
    resp = client.get(f"/api/v1/projects/{p_id}/orchestration")
    assert resp.status_code == 200
    assert resp.json()["is_blocked"] is True
    assert "locked" in resp.json()["blocked_reasons"][0].lower()

    # Executing START_VIDEO_GENERATION reports BLOCKED/NO_OP and does not advance stage
    resp_exec = client.post(
        f"/api/v1/projects/{p_id}/orchestration/execute",
        json={"action": "START_VIDEO_GENERATION"},
    )
    assert resp_exec.status_code == 200
    assert resp_exec.json()["result"] in ("BLOCKED", "NO_OP")
    db_session.refresh(p)
    assert p.status == "SHOT_PLAN_APPROVED"  # Remains in SHOT_PLAN_APPROVED!


def test_idempotent_stage_approval(client, db_session):
    p = Project(
        title="Idempotent Test",
        video_mode="STORY",
        status="STORY_APPROVED",
    )
    db_session.add(p)
    db_session.commit()
    p_id = str(p.id)

    resp = client.post(
        f"/api/v1/projects/{p_id}/orchestration/approve",
        json={"stage": "STORY_APPROVED"},
    )
    assert resp.status_code == 200
    assert resp.json()["result"] == "NO_OP"
    assert resp.json()["to_stage"] == "STORY_APPROVED"


def test_budget_hard_limit_blocks_dispatch(client, db_session):
    p = Project(
        title="Budget Limited Project",
        video_mode="STORY",
        status="SHOT_PLAN_APPROVED",
        budget_limit=10.0,
    )
    db_session.add(p)
    db_session.commit()

    # Add committed ledger usage exceeding budget
    ledger = UsageLedger(
        project_id=p.id,
        provider="vidu",
        operation="VIDEO_GENERATION",
        model="vidu-q1",
        cost_status=CostStatus.CONFIRMED,
        actual_cost=15.0,
    )
    db_session.add(ledger)
    db_session.commit()
    p_id = str(p.id)

    resp = client.get(f"/api/v1/projects/{p_id}/orchestration")
    assert resp.status_code == 200
    state = resp.json()
    assert state["is_blocked"] is True
    assert "hard budget limit exceeded" in state["blocked_reasons"][0].lower()

    # Execute generation fails with 409
    resp_exec = client.post(
        f"/api/v1/projects/{p_id}/orchestration/execute",
        json={"action": "START_VIDEO_GENERATION"},
    )
    assert resp_exec.status_code == 409
