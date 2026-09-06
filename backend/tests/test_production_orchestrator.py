import uuid
import pytest
from app.models.project import Project
from app.models.story import Story
from app.models.scene import Scene
from app.models.shot import Shot
from app.models.generation_job import GenerationJob
from app.models.usage_ledger import UsageLedger
from app.models.asset import Asset
from app.models.asset_lock import AssetLock
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

    # 2. Human approves STORY_GENERATED WITHOUT cost authorization
    # In AUTO mode, approving story without explicit cost authorization must NOT silently execute GENERATE_STORYBOARD!
    # It must STOP at STORY_APPROVED and recommend GENERATE_STORYBOARD (is_chargeable=True)
    appr_resp = client.post(
        f"/api/v1/projects/{p_id}/orchestration/approve",
        json={"stage": "STORY_GENERATED"},
    )
    assert appr_resp.status_code == 200
    appr_state = appr_resp.json()["orchestration_state"]
    assert appr_state["current_stage"] == "STORY_APPROVED"
    assert appr_state["recommended_action"]["action"] == "GENERATE_STORYBOARD"
    assert appr_state["recommended_action"]["is_chargeable"] is True
    # Verify no scenes were silently created without cost authorization
    db_session.refresh(p)
    assert p.status == "STORY_APPROVED"
    assert len(p.scenes) == 0

    # 3. Now test one-shot cost authorization:
    # First, let's revert or execute GENERATE_STORYBOARD manually to reach STORYBOARD_GENERATED
    gen_sb = client.post(
        f"/api/v1/projects/{p_id}/orchestration/execute",
        json={"action": "GENERATE_STORYBOARD"},
    )
    assert gen_sb.status_code == 200
    assert gen_sb.json()["orchestration_state"]["current_stage"] == "STORYBOARD_GENERATED"

    # Human approves STORYBOARD_GENERATED WITH explicit one-shot cost authorization:
    # With cost_authorized=True, AUTO automatically cascades to GENERATE_SHOT_PLAN
    # and reaches SHOT_PLAN_GENERATED, then stops for human review!
    appr_sb = client.post(
        f"/api/v1/projects/{p_id}/orchestration/approve",
        json={"stage": "STORYBOARD_GENERATED", "cost_authorized": True},
    )
    assert appr_sb.status_code == 200
    sb_state = appr_sb.json()["orchestration_state"]
    assert sb_state["current_stage"] == "SHOT_PLAN_GENERATED"
    assert sb_state["is_approval_required"] is True

    # 4. Human approves SHOT_PLAN_GENERATED (even with cost_authorized=True)
    # Approving shot plan reaches SHOT_PLAN_APPROVED.
    # It MUST ALWAYS STOP at SHOT_PLAN_APPROVED because video generation is never auto-cascaded!
    appr_sp = client.post(
        f"/api/v1/projects/{p_id}/orchestration/approve",
        json={"stage": "SHOT_PLAN_GENERATED", "cost_authorized": True},
    )
    assert appr_sp.status_code == 200
    sp_state = appr_sp.json()["orchestration_state"]
    assert sp_state["current_stage"] == "SHOT_PLAN_APPROVED"
    assert sp_state["recommended_action"]["action"] == "START_VIDEO_GENERATION"
    assert sp_state["recommended_action"]["is_chargeable"] is True
    # Verify it did not silently dispatch video generation jobs
    db_session.refresh(p)
    assert p.status == "SHOT_PLAN_APPROVED"

    # 5. Verify persisted cost authorization via settings
    patch_resp = client.patch(
        f"/api/v1/projects/{p_id}/orchestration/settings",
        json={"auto_cost_authorized": True},
    )
    assert patch_resp.status_code == 200
    db_session.refresh(p)
    assert (p.default_config or {}).get("auto_cost_authorized") is True


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

    # 1. Attempting resolution without evidence fails closed and preserves RECONCILIATION_REQUIRED
    resp_no_evidence = client.post(
        f"/api/v1/projects/{p_id}/orchestration/execute",
        json={"action": "RESOLVE_RECONCILIATION"},
    )
    assert resp_no_evidence.status_code == 400
    db_session.refresh(job)
    assert job.status == "RECONCILIATION_REQUIRED"

    # 2. Providing explicit job_id, resolution, and evidence succeeds
    resp_res = client.post(
        f"/api/v1/projects/{p_id}/orchestration/execute",
        json={
            "action": "RESOLVE_RECONCILIATION",
            "parameters": {
                "job_id": str(job.id),
                "resolution": "CONFIRMED_FAILED",
                "evidence": "Provider API query confirmed render failed with error code 500.",
            },
        },
    )
    assert resp_res.status_code == 200
    db_session.refresh(job)
    assert job.status == "FAILED"
    assert "Reconciled to FAILED" in (job.error_message or "")


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


# ==============================================================================
# Comprehensive Corrective Tests for Review ID 5124927218 Blockers
# ==============================================================================


def test_reconciliation_safety_all_outcomes_require_explicit_evidence(client, db_session):
    p = Project(title="Recon Safety", video_mode="STORY", status="VIDEO_IN_PROGRESS")
    db_session.add(p)
    db_session.commit()
    sc = Scene(project_id=p.id, scene_number=1)
    db_session.add(sc)
    db_session.commit()
    sh1 = Shot(scene_id=sc.id, shot_number=1, shot_type="AI_GENERATED")
    sh2 = Shot(scene_id=sc.id, shot_number=2, shot_type="AI_GENERATED")
    db_session.add_all([sh1, sh2])
    db_session.commit()

    j1 = GenerationJob(id=uuid.uuid4(), shot_id=sh1.id, provider_name="vidu", status="RECONCILIATION_REQUIRED")
    j2 = GenerationJob(id=uuid.uuid4(), shot_id=sh2.id, provider_name="vidu", status="RECONCILIATION_REQUIRED")
    db_session.add_all([j1, j2])
    db_session.commit()
    p_id = str(p.id)

    # 1. Missing evidence fails with 400 and preserves status
    res = client.post(
        f"/api/v1/projects/{p_id}/orchestration/execute",
        json={"action": "RESOLVE_RECONCILIATION", "parameters": {"job_id": str(j1.id), "resolution": "CONFIRMED_FAILED"}},
    )
    assert res.status_code == 400
    db_session.refresh(j1)
    assert j1.status == "RECONCILIATION_REQUIRED"

    # 2. Invalid resolution fails with 400
    res = client.post(
        f"/api/v1/projects/{p_id}/orchestration/execute",
        json={"action": "RESOLVE_RECONCILIATION", "parameters": {"job_id": str(j1.id), "resolution": "UNKNOWN", "evidence": "something"}},
    )
    assert res.status_code == 400

    # 3. CONFIRMED_COMPLETED with evidence sets COMPLETED and output_url
    res = client.post(
        f"/api/v1/projects/{p_id}/orchestration/execute",
        json={
            "action": "RESOLVE_RECONCILIATION",
            "parameters": {
                "job_id": str(j1.id),
                "resolution": "CONFIRMED_COMPLETED",
                "evidence": "Verified render succeeded on provider dashboard.",
                "output_url": "https://storage.provider.com/output/j1.mp4",
            },
        },
    )
    assert res.status_code == 200
    db_session.refresh(j1)
    assert j1.status == "COMPLETED"
    assert j1.output_url == "https://storage.provider.com/output/j1.mp4"

    # 4. CONFIRMED_CANCELLED sets CANCELLED
    res = client.post(
        f"/api/v1/projects/{p_id}/orchestration/execute",
        json={
            "action": "RESOLVE_RECONCILIATION",
            "parameters": {
                "job_id": str(j2.id),
                "resolution": "CONFIRMED_CANCELLED",
                "evidence": "Job was aborted by provider operator.",
            },
        },
    )
    assert res.status_code == 200
    db_session.refresh(j2)
    assert j2.status == "CANCELLED"


def test_duplicate_completed_jobs_do_not_falsely_complete_other_shots(client, db_session):
    p = Project(title="Duplicate Jobs Test", video_mode="STORY", status="VIDEO_IN_PROGRESS")
    db_session.add(p)
    db_session.commit()
    sc = Scene(project_id=p.id, scene_number=1)
    db_session.add(sc)
    db_session.commit()
    sh1 = Shot(scene_id=sc.id, shot_number=1, shot_type="AI_GENERATED")
    sh2 = Shot(scene_id=sc.id, shot_number=2, shot_type="AI_GENERATED")
    db_session.add_all([sh1, sh2])
    db_session.commit()

    # Shot 1 has 3 completed jobs across historical runs
    for _ in range(3):
        job = GenerationJob(id=uuid.uuid4(), shot_id=sh1.id, provider_name="vidu", status="COMPLETED")
        db_session.add(job)
    db_session.commit()

    # Shot 2 has NO completed jobs
    p_id = str(p.id)
    resp = client.get(f"/api/v1/projects/{p_id}/orchestration")
    assert resp.status_code == 200
    data = resp.json()
    summary = data["summary"]
    assert summary["shot_count"] == 2
    assert summary["completed_jobs"] == 3  # Raw historical jobs
    assert summary["distinct_completed_shots"] == 1  # Only 1 distinct shot completed!
    assert summary["production_ready_shots"] == 1

    # Transition to final review MUST be rejected: only 1 of 2 shots is production ready!
    res_trans = client.post(
        f"/api/v1/projects/{p_id}/orchestration/execute",
        json={"action": "TRANSITION_TO_FINAL_REVIEW"},
    )
    assert res_trans.status_code == 400
    assert "only 1/2 shots are production-ready" in res_trans.json()["detail"]


def test_imported_source_backed_shots_satisfy_production_readiness(client, db_session):
    p = Project(title="Imported Shots Test", video_mode="STORY", status="VIDEO_IN_PROGRESS")
    db_session.add(p)
    db_session.commit()

    ast = Asset(
        id=uuid.uuid4(),
        project_id=p.id,
        name="source.mp4",
        original_filename="source.mp4",
        asset_type="VIDEO",
        content_type="video/mp4",
        file_size_bytes=1024,
        checksum_sha256="abc123",
        storage_bucket="bucket",
        storage_key="key",
    )
    db_session.add(ast)
    db_session.commit()

    sc = Scene(project_id=p.id, scene_number=1)
    db_session.add(sc)
    db_session.commit()

    # Shot 1: IMPORTED_VIDEO with source_asset_id (no GenerationJob needed)
    sh1 = Shot(scene_id=sc.id, shot_number=1, shot_type="IMPORTED_VIDEO", source_asset_id=ast.id, status="COMPLETED")
    # Shot 2: AI_GENERATED with COMPLETED job
    sh2 = Shot(scene_id=sc.id, shot_number=2, shot_type="AI_GENERATED", status="PENDING")
    db_session.add_all([sh1, sh2])
    db_session.commit()

    job2 = GenerationJob(id=uuid.uuid4(), shot_id=sh2.id, provider_name="vidu", status="COMPLETED")
    db_session.add(job2)
    db_session.commit()

    p_id = str(p.id)
    resp = client.get(f"/api/v1/projects/{p_id}/orchestration")
    assert resp.status_code == 200
    data = resp.json()
    assert data["summary"]["production_ready_shots"] == 2
    assert data["summary"]["shot_count"] == 2
    assert data["recommended_action"]["action"] == "TRANSITION_TO_FINAL_REVIEW"

    # Transition succeeds because 2/2 are production ready
    res_trans = client.post(
        f"/api/v1/projects/{p_id}/orchestration/execute",
        json={"action": "TRANSITION_TO_FINAL_REVIEW"},
    )
    assert res_trans.status_code == 200
    assert res_trans.json()["to_stage"] == "FINAL_REVIEW"


def test_soft_archived_scenes_and_shots_excluded_from_counts(client, db_session):
    p = Project(title="Archived Excluded Test", video_mode="STORY", status="VIDEO_IN_PROGRESS")
    db_session.add(p)
    db_session.commit()

    # Active Scene
    sc_active = Scene(project_id=p.id, scene_number=1)
    # Archived Scene
    sc_archived = Scene(project_id=p.id, scene_number=2, scene_config={"archived": True})
    db_session.add_all([sc_active, sc_archived])
    db_session.commit()

    # Shot in active scene (completed)
    sh1 = Shot(scene_id=sc_active.id, shot_number=1, shot_type="AI_GENERATED")
    # Shot in active scene (archived status)
    sh_archived = Shot(scene_id=sc_active.id, shot_number=2, shot_type="AI_GENERATED", status="ARCHIVED")
    # Shot in archived scene
    sh3 = Shot(scene_id=sc_archived.id, shot_number=1, shot_type="AI_GENERATED")
    db_session.add_all([sh1, sh_archived, sh3])
    db_session.commit()

    j1 = GenerationJob(id=uuid.uuid4(), shot_id=sh1.id, provider_name="vidu", status="COMPLETED")
    db_session.add(j1)
    db_session.commit()

    p_id = str(p.id)
    resp = client.get(f"/api/v1/projects/{p_id}/orchestration")
    assert resp.status_code == 200
    data = resp.json()
    # Only 1 active scene and 1 active shot!
    assert data["summary"]["scene_count"] == 1
    assert data["summary"]["shot_count"] == 1
    assert data["summary"]["production_ready_shots"] == 1
    assert data["recommended_action"]["action"] == "TRANSITION_TO_FINAL_REVIEW"


def test_full_roundtrip_revision_lifecycle_no_dead_ends(client, db_session):
    fake_provider = FakeCreativeGenerationProvider()
    client.app.dependency_overrides[get_creative_provider] = lambda: fake_provider

    p = Project(title="Revision Roundtrip", video_mode="STORY", status="DRAFT", description="Brief description")
    db_session.add(p)
    db_session.commit()
    p_id = str(p.id)

    # 1. At DRAFT, recommended action is GENERATE_STORY (never APPROVE_STORY)
    st = client.get(f"/api/v1/projects/{p_id}/orchestration").json()
    assert st["recommended_action"]["action"] == "GENERATE_STORY"
    assert st["recommended_action"]["is_chargeable"] is True

    # 2. Execute GENERATE_STORY -> transitions to STORY_GENERATED
    gen_st = client.post(f"/api/v1/projects/{p_id}/orchestration/execute", json={"action": "GENERATE_STORY"}).json()
    assert gen_st["to_stage"] == "STORY_GENERATED"
    st = client.get(f"/api/v1/projects/{p_id}/orchestration").json()
    assert st["recommended_action"]["action"] == "APPROVE_STORY"

    # 3. Approve Story -> transitions to STORY_APPROVED
    app_st = client.post(f"/api/v1/projects/{p_id}/orchestration/approve", json={"stage": "STORY_GENERATED"}).json()
    assert app_st["to_stage"] == "STORY_APPROVED"
    st = client.get(f"/api/v1/projects/{p_id}/orchestration").json()
    # At STORY_APPROVED, recommended is GENERATE_STORYBOARD (never APPROVE_STORYBOARD)
    assert st["recommended_action"]["action"] == "GENERATE_STORYBOARD"
    assert st["recommended_action"]["is_chargeable"] is True

    # 4. Revise Story -> reverts to DRAFT
    rev_st = client.post(f"/api/v1/projects/{p_id}/orchestration/execute", json={"action": "REVISE_STORY"}).json()
    assert rev_st["to_stage"] == "DRAFT"
    st = client.get(f"/api/v1/projects/{p_id}/orchestration").json()
    # Must still recommend GENERATE_STORY, NOT APPROVE_STORY
    assert st["recommended_action"]["action"] == "GENERATE_STORY"

    # Re-generate and re-approve Story
    client.post(f"/api/v1/projects/{p_id}/orchestration/execute", json={"action": "GENERATE_STORY"})
    client.post(f"/api/v1/projects/{p_id}/orchestration/approve", json={"stage": "STORY_GENERATED"})

    # 5. Generate Storyboard -> STORYBOARD_GENERATED
    gen_sb = client.post(f"/api/v1/projects/{p_id}/orchestration/execute", json={"action": "GENERATE_STORYBOARD"}).json()
    assert gen_sb["to_stage"] == "STORYBOARD_GENERATED"
    st = client.get(f"/api/v1/projects/{p_id}/orchestration").json()
    assert st["recommended_action"]["action"] == "APPROVE_STORYBOARD"

    # 6. Approve Storyboard -> STORYBOARD_APPROVED
    app_sb = client.post(f"/api/v1/projects/{p_id}/orchestration/approve", json={"stage": "STORYBOARD_GENERATED"}).json()
    assert app_sb["to_stage"] == "STORYBOARD_APPROVED"
    st = client.get(f"/api/v1/projects/{p_id}/orchestration").json()
    # At STORYBOARD_APPROVED, recommended is GENERATE_SHOT_PLAN (never APPROVE_SHOT_PLAN)
    assert st["recommended_action"]["action"] == "GENERATE_SHOT_PLAN"
    assert st["recommended_action"]["is_chargeable"] is True

    # 7. Revise Storyboard -> reverts to STORY_APPROVED
    rev_sb = client.post(f"/api/v1/projects/{p_id}/orchestration/execute", json={"action": "REVISE_STORYBOARD"}).json()
    assert rev_sb["to_stage"] == "STORY_APPROVED"
    st = client.get(f"/api/v1/projects/{p_id}/orchestration").json()
    assert st["recommended_action"]["action"] == "GENERATE_STORYBOARD"

    # Re-generate and re-approve Storyboard
    client.post(f"/api/v1/projects/{p_id}/orchestration/execute", json={"action": "GENERATE_STORYBOARD"})
    client.post(f"/api/v1/projects/{p_id}/orchestration/approve", json={"stage": "STORYBOARD_GENERATED"})

    # 8. Generate Shot Plan -> SHOT_PLAN_GENERATED
    gen_sp = client.post(f"/api/v1/projects/{p_id}/orchestration/execute", json={"action": "GENERATE_SHOT_PLAN"}).json()
    assert gen_sp["to_stage"] == "SHOT_PLAN_GENERATED"
    st = client.get(f"/api/v1/projects/{p_id}/orchestration").json()
    assert st["recommended_action"]["action"] == "APPROVE_SHOT_PLAN"

    # 9. Approve Shot Plan -> SHOT_PLAN_APPROVED
    app_sp = client.post(f"/api/v1/projects/{p_id}/orchestration/approve", json={"stage": "SHOT_PLAN_GENERATED"}).json()
    assert app_sp["to_stage"] == "SHOT_PLAN_APPROVED"
    st = client.get(f"/api/v1/projects/{p_id}/orchestration").json()
    assert st["recommended_action"]["action"] == "START_VIDEO_GENERATION"

    # 10. Revise Shot Plan -> reverts to STORYBOARD_APPROVED
    rev_sp = client.post(f"/api/v1/projects/{p_id}/orchestration/execute", json={"action": "REVISE_SHOT_PLAN"}).json()
    assert rev_sp["to_stage"] == "STORYBOARD_APPROVED"
    st = client.get(f"/api/v1/projects/{p_id}/orchestration").json()
    assert st["recommended_action"]["action"] == "GENERATE_SHOT_PLAN"


def test_action_specific_generation_matrix_strict_guards(client, db_session):
    p = Project(title="Matrix Strictness", video_mode="STORY", status="SHOT_PLAN_GENERATED")
    db_session.add(p)
    db_session.commit()
    p_id = str(p.id)

    # 1. START_VIDEO_GENERATION fails closed from SHOT_PLAN_GENERATED (must be SHOT_PLAN_APPROVED)
    res1 = client.post(f"/api/v1/projects/{p_id}/orchestration/execute", json={"action": "START_VIDEO_GENERATION"})
    assert res1.status_code == 409
    assert "requires 'SHOT_PLAN_APPROVED'" in res1.json()["detail"]

    # 2. RETRY_FAILED fails closed from SHOT_PLAN_GENERATED (must be VIDEO_IN_PROGRESS or NEEDS_ATTENTION)
    res2 = client.post(f"/api/v1/projects/{p_id}/orchestration/execute", json={"action": "RETRY_FAILED"})
    assert res2.status_code == 409
    assert "requires 'VIDEO_IN_PROGRESS'" in res2.json()["detail"]

    # 3. From COMPLETED, generation and continue actions fail closed
    p.status = "COMPLETED"
    db_session.commit()
    res3 = client.post(f"/api/v1/projects/{p_id}/orchestration/execute", json={"action": "START_VIDEO_GENERATION"})
    assert res3.status_code == 409
    res4 = client.post(f"/api/v1/projects/{p_id}/orchestration/execute", json={"action": "CONTINUE_INCOMPLETE"})
    assert res4.status_code == 409
    res5 = client.post(f"/api/v1/projects/{p_id}/orchestration/execute", json={"action": "GENERATE_SELECTED_SHOTS", "parameters": {"shot_ids": [str(uuid.uuid4())]}})
    assert res5.status_code == 409


def test_hierarchical_lock_truth_surfaces_in_evaluate_state(client, db_session):
    p = Project(title="Hierarchical Lock Project", video_mode="STORY", status="SHOT_PLAN_APPROVED")
    db_session.add(p)
    db_session.commit()
    sc = Scene(project_id=p.id, scene_number=1)
    db_session.add(sc)
    db_session.commit()
    sh = Shot(scene_id=sc.id, shot_number=1, shot_type="AI_GENERATED")
    db_session.add(sh)
    db_session.commit()

    # Lock the shot via AssetLock table
    lock = AssetLock(
        id=uuid.uuid4(),
        project_id=p.id,
        entity_type="SHOT",
        entity_id=sh.id,
        is_locked=True,
        lock_reason="Shot locked by operator",
    )
    db_session.add(lock)
    db_session.commit()

    p_id = str(p.id)
    resp = client.get(f"/api/v1/projects/{p_id}/orchestration")
    assert resp.status_code == 200
    state = resp.json()
    assert state["is_blocked"] is True
    assert "locked against generation" in state["blocked_reasons"][0]
    assert state["recommended_action"]["is_blocked"] is True
    assert "locked" in state["recommended_action"]["blocked_reason"]


def test_legacy_generation_endpoints_fail_closed_on_completed_project(client, db_session):
    fake_provider = FakeCreativeGenerationProvider()
    client.app.dependency_overrides[get_creative_provider] = lambda: fake_provider

    p = Project(title="Terminal Project", video_mode="STORY", status="COMPLETED")
    db_session.add(p)
    db_session.commit()
    p_id = str(p.id)

    # Legacy story generation rejects
    res = client.post(f"/api/v1/projects/{p_id}/story/generate", json={})
    assert res.status_code == 409
    assert "Cannot generate story when project is in 'COMPLETED'" in res.json()["detail"]

    # Legacy storyboard generation rejects
    res_sb = client.post(f"/api/v1/projects/{p_id}/storyboard/generate", json={})
    assert res_sb.status_code == 409


def test_auto_mode_does_not_invoke_provider_silently_without_cost_authorization(client, db_session):
    """
    AUTO COST SAFETY:
    GENERATE_STORY / GENERATE_STORYBOARD / GENERATE_SHOT_PLAN are chargeable provider actions.
    AUTO must NOT silently execute a chargeable action after approval.
    Unless explicit persisted/one-shot cost authorization exists, AUTO must STOP and recommend the chargeable next action.
    """
    class SpyProvider(FakeCreativeGenerationProvider):
        def __init__(self):
            super().__init__()
            self.generate_story_called = 0
            self.generate_scenes_called = 0
            self.generate_shots_called = 0

        def generate_story(self, prompt, **kwargs):
            self.generate_story_called += 1
            return super().generate_story(prompt, **kwargs)

        def generate_scenes(self, prompt="", **kwargs):
            self.generate_scenes_called += 1
            return super().generate_scenes(prompt=prompt, **kwargs)

        def generate_shots(self, scene_heading, scene_description, **kwargs):
            self.generate_shots_called += 1
            return super().generate_shots(scene_heading, scene_description, **kwargs)

    spy_provider = SpyProvider()
    client.app.dependency_overrides[get_creative_provider] = lambda: spy_provider

    # Create project in STORY_GENERATED stage with AUTO mode
    p = Project(
        title="Auto Cost Safety Project",
        video_mode="STORY",
        status="STORY_GENERATED",
        automation_mode="AUTO",
    )
    db_session.add(p)
    db_session.commit()
    story = Story(project_id=p.id, logline="Outline prompt", title="Story Title", synopsis="Story outline")
    db_session.add(story)
    db_session.commit()
    p_id = str(p.id)

    # 1. User approves STORY_GENERATED WITHOUT cost authorization
    resp = client.post(
        f"/api/v1/projects/{p_id}/orchestration/approve",
        json={"stage": "STORY_GENERATED"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["to_stage"] == "STORY_APPROVED"
    assert "cost authorization" in data["message"].lower()

    # CRITICAL: Verify provider was NOT silently invoked to generate scenes
    assert spy_provider.generate_scenes_called == 0
    state = data["orchestration_state"]
    assert state["current_stage"] == "STORY_APPROVED"
    assert state["recommended_action"]["action"] == "GENERATE_STORYBOARD"
    assert state["recommended_action"]["is_chargeable"] is True

    # 2. If hard limit exceeded, even with cost_authorized=True, AUTO must halt
    p.budget_limit = 10.0
    db_session.commit()
    # Add ledger entry exceeding limit
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

    # Revert to STORY_GENERATED to test approval under hard limit exceeded
    p.status = "STORY_GENERATED"
    db_session.commit()

    resp_hard = client.post(
        f"/api/v1/projects/{p_id}/orchestration/approve",
        json={"stage": "STORY_GENERATED", "cost_authorized": True},
    )
    assert resp_hard.status_code == 200
    assert "hard budget limit exceeded" in resp_hard.json()["message"].lower()
    # Provider still not called
    assert spy_provider.generate_scenes_called == 0

    # 3. Clear hard limit and approve with explicit cost authorization -> provider IS called
    p.budget_limit = 100.0
    p.status = "STORY_GENERATED"
    db_session.commit()

    resp_authorized = client.post(
        f"/api/v1/projects/{p_id}/orchestration/approve",
        json={"stage": "STORY_GENERATED", "cost_authorized": True},
    )
    assert resp_authorized.status_code == 200
    assert spy_provider.generate_scenes_called == 1
    assert resp_authorized.json()["orchestration_state"]["current_stage"] == "STORYBOARD_GENERATED"
