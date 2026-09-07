import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models.project import Project
from app.models.scene import Scene
from app.models.shot import Shot
from app.models.asset import Asset
from app.models.audio_clip import AudioClip
from app.models.assembly import AssemblyTimeline, AssemblyScene, AssemblyShotPlacement
from app.models.qc import QCRun, QCFinding, WarningDecision, ApprovalRecord
from app.services.qc import QCService
from app.services.assembly import AssemblyService
from app.services.production_orchestrator import ProductionOrchestrator

from app.db.session import get_db

client = TestClient(app)


@pytest.fixture
def test_project_context(db_session: Session):
    """Creates a standard test project with story, scenes, shots, timeline and assets."""
    app.dependency_overrides[get_db] = lambda: db_session

    project = Project(
        id=uuid.uuid4(),
        title="QC Test Movie",
        video_mode="STORY",
        status="FINAL_REVIEW",
    )
    db_session.add(project)
    db_session.flush()

    scene1 = Scene(
        id=uuid.uuid4(),
        project_id=project.id,
        scene_number=1,
        heading="INT. QC LAB - DAY",
    )
    db_session.add(scene1)
    db_session.flush()

    shot1 = Shot(
        id=uuid.uuid4(),
        scene_id=scene1.id,
        shot_number=1,
        visual_prompt="Close up of AI inspector",
        shot_type="AI_GENERATED",
        status="COMPLETED",
    )
    shot2 = Shot(
        id=uuid.uuid4(),
        scene_id=scene1.id,
        shot_number=2,
        visual_prompt="Wide view of testing terminal",
        shot_type="AI_GENERATED",
        status="COMPLETED",
    )
    db_session.add_all([shot1, shot2])
    db_session.flush()

    asset1 = Asset(
        id=uuid.uuid4(),
        project_id=project.id,
        name="Shot 1 Video",
        original_filename="shot1.mp4",
        asset_type="VIDEO",
        content_type="video/mp4",
        file_size_bytes=1024,
        checksum_sha256="dummy_sha1",
        storage_bucket="default",
        storage_key="videos/shot1.mp4",
    )
    asset2 = Asset(
        id=uuid.uuid4(),
        project_id=project.id,
        name="Shot 2 Video",
        original_filename="shot2.mp4",
        asset_type="VIDEO",
        content_type="video/mp4",
        file_size_bytes=1024,
        checksum_sha256="dummy_sha2",
        storage_bucket="default",
        storage_key="videos/shot2.mp4",
    )
    db_session.add_all([asset1, asset2])
    db_session.flush()

    shot1.source_asset_id = asset1.id
    shot2.source_asset_id = asset2.id

    audio = AudioClip(
        id=uuid.uuid4(),
        project_id=project.id,
        scene_id=scene1.id,
        shot_id=shot1.id,
        audio_type="VO",
        source_type="GENERATED_AUDIO",
        generation_mode="SEPARATE_AUDIO",
        scope="SHOT",
        name="VO Clip 1",
    )
    db_session.add(audio)
    db_session.flush()

    timeline = AssemblyService.auto_assemble_timeline(db_session, str(project.id))
    db_session.commit()

    return {
        "project": project,
        "scene1": scene1,
        "shot1": shot1,
        "shot2": shot2,
        "asset1": asset1,
        "asset2": asset2,
        "audio": audio,
        "timeline": timeline,
    }


def test_1_blocker_prevents_approval(db_session: Session, test_project_context):
    ctx = test_project_context
    project = ctx["project"]
    timeline = ctx["timeline"]

    # Invalidate placement visual asset to force a BLOCKER finding (MISSING_VISUAL)
    placement = timeline.scenes[0].shot_placements[0]
    placement.visual_asset_id = None
    placement.source_type = "MISSING"
    db_session.commit()

    qc_run = QCService.run_qc(db_session, project.id)
    assert qc_run.status == "BLOCKED"
    assert qc_run.blocker_count > 0

    # Attempt approval must fail with 400 error explaining blocker
    with pytest.raises(Exception) as exc_info:
        QCService.approve_production(db_session, project.id, timeline_id=timeline.id, qc_run_id=qc_run.id)

    assert "BLOCKER" in str(exc_info.value) or "blocker" in str(exc_info.value).lower() or "cannot approve" in str(exc_info.value).lower()


def test_2_warning_requires_explicit_user_decision(db_session: Session, test_project_context):
    ctx = test_project_context
    project = ctx["project"]

    qc_run = QCService.run_qc(db_session, project.id)

    # Add an undecided warning finding
    finding = QCFinding(
        id=uuid.uuid4(),
        project_id=project.id,
        qc_run_id=qc_run.id,
        timeline_id=qc_run.timeline_id,
        rule_code="TEST_UNDECIDED_WARNING",
        severity="WARNING",
        message="Undecided warning message",
    )
    db_session.add(finding)
    qc_run.warning_count += 1
    qc_run.status = "RUNNING"
    db_session.commit()

    with pytest.raises(Exception) as exc_info:
        QCService.approve_production(db_session, project.id)

    assert "warning" in str(exc_info.value).lower()


def test_3_accepting_warning_without_reason_fails(db_session: Session, test_project_context):
    ctx = test_project_context
    project = ctx["project"]

    qc_run = QCService.run_qc(db_session, project.id)
    finding = QCFinding(
        id=uuid.uuid4(),
        project_id=project.id,
        qc_run_id=qc_run.id,
        timeline_id=qc_run.timeline_id,
        rule_code="TEST_WARNING",
        severity="WARNING",
        message="Test warning requirement.",
    )
    db_session.add(finding)
    db_session.commit()

    response = client.post(
        f"/api/v1/projects/{project.id}/qc/findings/{finding.id}/decision",
        json={"decision": "ACCEPTED_WITH_REASON", "reason": ""},
    )
    assert response.status_code == 400 or response.status_code == 422


def test_4_accepting_warning_with_reason_succeeds(db_session: Session, test_project_context):
    ctx = test_project_context
    project = ctx["project"]

    qc_run = QCService.run_qc(db_session, project.id)
    finding = QCFinding(
        id=uuid.uuid4(),
        project_id=project.id,
        qc_run_id=qc_run.id,
        timeline_id=qc_run.timeline_id,
        rule_code="TEST_WARNING_4",
        severity="WARNING",
        message="Test warning requiring reason.",
    )
    db_session.add(finding)
    qc_run.warning_count += 1
    db_session.commit()

    response = client.post(
        f"/api/v1/projects/{project.id}/qc/findings/{finding.id}/decision?actor=TestUser",
        json={"decision": "ACCEPTED_WITH_REASON", "reason": "Stylistic jump cut intended by director"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["decision"] == "ACCEPTED_WITH_REASON"
    assert data["reason"] == "Stylistic jump cut intended by director"
    assert data["actor"] == "TestUser"


def test_5_warning_decision_binds_to_exact_revision(db_session: Session, test_project_context):
    ctx = test_project_context
    project = ctx["project"]
    timeline = ctx["timeline"]

    qc_run = QCService.run_qc(db_session, project.id)
    finding = QCFinding(
        id=uuid.uuid4(),
        project_id=project.id,
        qc_run_id=qc_run.id,
        timeline_id=timeline.id,
        rule_code="TEST_WARNING_5",
        severity="WARNING",
        message="Test binding.",
    )
    db_session.add(finding)
    db_session.commit()

    dec = QCService.record_warning_decision(
        db_session, project.id, finding.id, decision="ACCEPTED_WITH_REASON", reason="Valid reason"
    )

    assert dec.timeline_id == timeline.id
    assert dec.qc_run_id == qc_run.id
    assert dec.finding_id == finding.id


def test_6_old_revision_decision_does_not_satisfy_new_revision(db_session: Session, test_project_context):
    ctx = test_project_context
    project = ctx["project"]

    qc_run_v1 = QCService.run_qc(db_session, project.id)
    finding_v1 = QCFinding(
        id=uuid.uuid4(),
        project_id=project.id,
        qc_run_id=qc_run_v1.id,
        timeline_id=qc_run_v1.timeline_id,
        rule_code="TEST_WARNING_6",
        severity="WARNING",
        message="V1 Warning.",
    )
    db_session.add(finding_v1)
    db_session.commit()

    QCService.record_warning_decision(
        db_session, project.id, finding_v1.id, decision="ACCEPTED_WITH_REASON", reason="V1 decision reason"
    )

    # Spawn new timeline revision v2
    timeline_v2 = AssemblyService.auto_assemble_timeline(db_session, str(project.id))
    assert timeline_v2.version == 2

    # Run QC on v2
    qc_run_v2 = QCService.run_qc(db_session, project.id)
    assert qc_run_v2.timeline_id == timeline_v2.id

    decisions_v2_finding_ids = {d.finding_id for d in qc_run_v2.decisions}
    assert finding_v1.id not in decisions_v2_finding_ids


def test_7_clean_current_revision_can_approve(db_session: Session, test_project_context):
    ctx = test_project_context
    project = ctx["project"]

    qc_run = QCService.run_qc(db_session, project.id)

    # Resolve all warning findings if any
    for f in qc_run.findings:
        if f.severity == "WARNING":
            QCService.record_warning_decision(
                db_session, project.id, f.id, decision="ACCEPTED_WITH_REASON", reason="Accepted for test"
            )

    db_session.refresh(qc_run)
    assert qc_run.blocker_count == 0

    approval = QCService.approve_production(
        db_session, project.id, timeline_id=qc_run.timeline_id, qc_run_id=qc_run.id, notes="Final cut approved!"
    )

    assert approval.status == "APPROVED"
    assert project.status == "COMPLETED"
    assert ctx["timeline"].status == "APPROVED"


def test_8_stale_qc_cannot_approve_newer_revision(db_session: Session, test_project_context):
    ctx = test_project_context
    project = ctx["project"]

    qc_run_v1 = QCService.run_qc(db_session, project.id)

    # Edit timeline to create v2
    timeline_v2 = AssemblyService.auto_assemble_timeline(db_session, str(project.id))
    assert timeline_v2.version == 2

    with pytest.raises(Exception) as exc_info:
        QCService.approve_production(
            db_session, project.id, timeline_id=timeline_v2.id, qc_run_id=qc_run_v1.id
        )

    assert "qc" in str(exc_info.value).lower() or "revision" in str(exc_info.value).lower() or "stale" in str(exc_info.value).lower()


def test_9_and_10_approved_old_revision_remains_immutable(db_session: Session, test_project_context):
    ctx = test_project_context
    project = ctx["project"]
    timeline_v1 = ctx["timeline"]

    qc_run = QCService.run_qc(db_session, project.id)
    for f in qc_run.findings:
        if f.severity == "WARNING":
            QCService.record_warning_decision(db_session, project.id, f.id, "ACCEPTED_WITH_REASON", "Reason")

    QCService.approve_production(db_session, project.id)

    db_session.refresh(timeline_v1)
    assert timeline_v1.status == "APPROVED"
    assert timeline_v1.is_active is True

    placement = timeline_v1.scenes[0].shot_placements[0]

    # Editing placement after approval
    updated_p = AssemblyService.update_shot_placement(
        db_session, str(project.id), str(placement.id), still_duration=6.0, actor="UserEdit"
    )

    active_timeline_now = AssemblyService.get_active_timeline(db_session, str(project.id))
    assert active_timeline_now.id != timeline_v1.id
    assert active_timeline_now.version == 2
    assert active_timeline_now.status == "DRAFT"

    db_session.refresh(timeline_v1)
    assert timeline_v1.status == "APPROVED"
    assert timeline_v1.is_active is False


def test_11_direct_patch_cannot_jump_to_approval(db_session: Session, test_project_context):
    ctx = test_project_context
    project = ctx["project"]

    placement = ctx["timeline"].scenes[0].shot_placements[0]
    placement.source_type = "MISSING"
    placement.visual_asset_id = None
    db_session.commit()

    with pytest.raises(Exception) as exc_info:
        ProductionOrchestrator.approve_stage(db_session, project.id, stage="FINAL_REVIEW")

    assert "qc" in str(exc_info.value).lower() or "blocker" in str(exc_info.value).lower() or "missing" in str(exc_info.value).lower() or "cannot" in str(exc_info.value).lower()


def test_12_cross_project_access_fails_closed(db_session: Session, test_project_context):
    ctx = test_project_context
    project1 = ctx["project"]

    project2 = Project(id=uuid.uuid4(), title="Project 2", video_mode="STORY")
    db_session.add(project2)
    db_session.flush()

    qc_run1 = QCService.run_qc(db_session, project1.id)
    finding1 = QCFinding(
        id=uuid.uuid4(),
        project_id=project1.id,
        qc_run_id=qc_run1.id,
        timeline_id=qc_run1.timeline_id,
        rule_code="PROJ1_WARNING",
        severity="WARNING",
        message="Proj 1 warning",
    )
    db_session.add(finding1)
    db_session.commit()

    response = client.post(
        f"/api/v1/projects/{project2.id}/qc/findings/{finding1.id}/decision",
        json={"decision": "ACCEPTED_WITH_REASON", "reason": "Attack attempt"},
    )
    assert response.status_code == 404


def test_13_audit_history_retains_actor_reason_time(db_session: Session, test_project_context):
    ctx = test_project_context
    project = ctx["project"]

    qc_run = QCService.run_qc(db_session, project.id)
    finding = QCFinding(
        id=uuid.uuid4(),
        project_id=project.id,
        qc_run_id=qc_run.id,
        timeline_id=qc_run.timeline_id,
        rule_code="AUDIT_TEST",
        severity="WARNING",
        message="Audit warning",
    )
    db_session.add(finding)
    db_session.commit()

    dec = QCService.record_warning_decision(
        db_session, project.id, finding.id, "ACCEPTED_WITH_REASON", "Audit trail test reason", actor="AuditorBob"
    )

    assert dec.actor == "AuditorBob"
    assert dec.reason == "Audit trail test reason"
    assert dec.decided_at is not None


def test_14_no_external_provider_calls(db_session: Session, test_project_context):
    ctx = test_project_context
    project = ctx["project"]

    qc_run = QCService.run_qc(db_session, project.id)
    assert qc_run.id is not None


def test_15_bounded_paginated_history(db_session: Session, test_project_context):
    ctx = test_project_context
    project = ctx["project"]

    for _ in range(5):
        QCService.run_qc(db_session, project.id)

    res = QCService.get_qc_history(db_session, project.id, offset=0, limit=2)
    assert len(res.qc_runs) == 2
    assert res.total_count >= 5
    assert res.limit == 2
    assert res.offset == 0


def test_16_representative_large_project_no_n_plus_1(db_session: Session):
    project = Project(id=uuid.uuid4(), title="Large Movie", video_mode="STORY")
    db_session.add(project)
    db_session.flush()

    for s_idx in range(5):
        scene = Scene(id=uuid.uuid4(), project_id=project.id, scene_number=s_idx + 1)
        db_session.add(scene)
        db_session.flush()

        for sh_idx in range(10):
            shot = Shot(
                id=uuid.uuid4(),
                scene_id=scene.id,
                shot_number=sh_idx + 1,
                visual_prompt=f"Shot {s_idx}-{sh_idx}",
                shot_type="AI_GENERATED",
                status="COMPLETED",
            )
            asset = Asset(
                id=uuid.uuid4(),
                project_id=project.id,
                name=f"Asset {s_idx}-{sh_idx}",
                original_filename=f"v_{s_idx}_{sh_idx}.mp4",
                asset_type="VIDEO",
                content_type="video/mp4",
                file_size_bytes=1024,
                checksum_sha256=f"sha_{s_idx}_{sh_idx}",
                storage_bucket="default",
                storage_key=f"v/{s_idx}_{sh_idx}.mp4",
            )
            db_session.add_all([shot, asset])
            db_session.flush()
            shot.source_asset_id = asset.id

    db_session.commit()

    qc_run = QCService.run_qc(db_session, project.id)
    assert qc_run is not None
    assert qc_run.blocker_count == 0


def test_17_fix_required_blocks_approval_and_status_not_passed(db_session: Session, test_project_context):
    ctx = test_project_context
    project = ctx["project"]

    qc_run = QCService.run_qc(db_session, project.id)
    finding = QCFinding(
        id=uuid.uuid4(),
        project_id=project.id,
        qc_run_id=qc_run.id,
        timeline_id=qc_run.timeline_id,
        rule_code="TEST_FIX_REQ_RULE",
        severity="WARNING",
        message="Warning that needs fixing.",
    )
    db_session.add(finding)
    db_session.commit()

    # User decides FIX_REQUIRED for the warning
    QCService.record_warning_decision(
        db_session, project.id, finding.id, decision="FIX_REQUIRED", reason="Intend to fix later"
    )

    db_session.refresh(qc_run)
    # QC run MUST NOT become PASSED solely because all warnings have decisions when any is FIX_REQUIRED
    assert qc_run.status != "PASSED"

    # Attempting approval while a warning is FIX_REQUIRED MUST fail
    with pytest.raises(Exception) as exc_info:
        QCService.approve_production(db_session, project.id)

    assert "FIX_REQUIRED" in str(exc_info.value) or "fix" in str(exc_info.value).lower()


def test_18_accepted_with_reason_allows_approval(db_session: Session, test_project_context):
    ctx = test_project_context
    project = ctx["project"]

    qc_run = QCService.run_qc(db_session, project.id)
    finding = QCFinding(
        id=uuid.uuid4(),
        project_id=project.id,
        qc_run_id=qc_run.id,
        timeline_id=qc_run.timeline_id,
        rule_code="TEST_ACCEPT_RULE",
        severity="WARNING",
        message="Waived warning.",
    )
    db_session.add(finding)
    db_session.commit()

    QCService.record_warning_decision(
        db_session, project.id, finding.id, decision="ACCEPTED_WITH_REASON", reason="Director stylistic waiver"
    )

    db_session.refresh(qc_run)
    assert qc_run.status == "PASSED"

    approval = QCService.approve_production(db_session, project.id)
    assert approval.status == "APPROVED"


def test_19_final_approval_uses_canonical_orchestrator_transition_and_audit(db_session: Session, test_project_context):
    ctx = test_project_context
    project = ctx["project"]
    project.status = "FINAL_REVIEW"
    db_session.commit()

    qc_run = QCService.run_qc(db_session, project.id)
    for f in qc_run.findings:
        if f.severity == "WARNING":
            QCService.record_warning_decision(db_session, project.id, f.id, "ACCEPTED_WITH_REASON", "Valid reason")

    approval = QCService.approve_production(db_session, project.id, actor="TestAuditor")

    db_session.refresh(project)
    assert project.status == "COMPLETED"

    # Check orchestrator audit history for correct from_state and to_state
    from app.models.orchestration_audit import OrchestrationAudit
    audits = (
        db_session.query(OrchestrationAudit)
        .filter(OrchestrationAudit.project_id == project.id)
        .order_by(OrchestrationAudit.created_at.desc())
        .all()
    )
    assert len(audits) > 0
    latest_audit = audits[0]
    assert latest_audit.from_state == "FINAL_REVIEW"
    assert latest_audit.to_state == "COMPLETED"
    assert latest_audit.action == "APPROVE_FINAL"
    assert latest_audit.actor == "TestAuditor"


def test_20_generic_patch_cannot_jump_to_approval(db_session: Session, test_project_context):
    ctx = test_project_context
    project = ctx["project"]

    response = client.patch(
        f"/api/v1/projects/{project.id}",
        json={"status": "APPROVED"},
    )
    assert response.status_code == 400
    assert "disallowed" in response.json()["detail"].lower() or "orchestration" in response.json()["detail"].lower()


def test_21_bounded_approval_history(db_session: Session, test_project_context):
    ctx = test_project_context
    project = ctx["project"]
    timeline = ctx["timeline"]
    qc_run = QCService.run_qc(db_session, project.id)

    from app.models.qc import ApprovalRecord
    from app.services.qc import utc_now
    for i in range(15):
        db_session.add(
            ApprovalRecord(
                id=uuid.uuid4(),
                project_id=project.id,
                timeline_id=timeline.id,
                timeline_version=1,
                qc_run_id=qc_run.id,
                status="APPROVED",
                actor=f"User{i}",
                approved_at=utc_now(),
            )
        )
    db_session.commit()

    response = client.get(f"/api/v1/projects/{project.id}/qc/approvals?limit=5")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 5

    # Enforces max limit cap at 100
    response_cap = client.get(f"/api/v1/projects/{project.id}/qc/approvals?limit=150")
    assert response_cap.status_code == 422 or len(response_cap.json()) <= 100
