"""Focused unit and integration tests for P2-WP009: Cost Control & Granular Usage Audit Ledger."""
import uuid
import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.project import Project
from app.models.scene import Scene
from app.models.shot import Shot
from app.models.generation_job import GenerationJob
from app.models.usage_ledger import UsageLedger, LedgerAdjustment
from app.services.pricing import ProviderPricingService, ProviderPricingRule, CostStatus
from app.services.budget import BudgetService
from app.services.cost_ledger import CostLedgerService
from app.services.job_dispatch import JobDispatchService


@pytest.fixture
def test_project(db_session: Session) -> Project:
    project = Project(
        id=uuid.uuid4(),
        title="Cost Control Test Project",
        description="Testing usage ledger and budgets",
        video_mode="SCENE",
        budget_limit=10.0,
        budget_currency="USD",
        budget_threshold_percentage=80.0,
    )
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    return project


@pytest.fixture
def test_shot(db_session: Session, test_project: Project) -> Shot:
    scene = Scene(
        id=uuid.uuid4(),
        project_id=test_project.id,
        scene_number=1,
        heading="Scene 1",
    )
    db_session.add(scene)
    db_session.commit()

    shot = Shot(
        id=uuid.uuid4(),
        scene_id=scene.id,
        shot_number=1,
        shot_type="AI_GENERATED",
        visual_prompt="A futuristic flying car over Neo Bangkok",
        duration_seconds=4.0,
    )
    db_session.add(shot)
    db_session.commit()
    db_session.refresh(shot)
    return shot


def test_provider_pricing_registry_defaults():
    # 1. Known vidu pricing
    cost, curr, status = ProviderPricingService.estimate_cost(
        "vidu", "VIDEO_GENERATION", params={"duration_seconds": 4.0}
    )
    assert status == CostStatus.ESTIMATED
    assert curr == "USD"
    assert cost == pytest.approx(0.20, rel=1e-3)

    # 2. Unknown provider returns UNKNOWN without inventing numbers
    cost_unk, curr_unk, status_unk = ProviderPricingService.estimate_cost(
        "unregistered_unknown_provider", "SOME_OPERATION"
    )
    assert status_unk == CostStatus.UNKNOWN
    assert cost_unk is None

    # 3. Dynamic rule registration works without altering core domain logic
    ProviderPricingRule_custom = ProviderPricingRule(
        provider="custom_ai",
        operation="VOICE_GEN",
        cost_per_second=0.01,
        currency="USD",
    )
    ProviderPricingService.register_rule(ProviderPricingRule_custom)
    c_cost, c_curr, c_status = ProviderPricingService.estimate_cost(
        "custom_ai", "VOICE_GEN", params={"duration_seconds": 10.0}
    )
    assert c_status == CostStatus.ESTIMATED
    assert c_cost == pytest.approx(0.10, rel=1e-3)


def test_record_usage_ledger_entry_and_query_summary(db_session: Session, test_project: Project, test_shot: Shot):
    entry = CostLedgerService.record_entry(
        db=db_session,
        project_id=test_project.id,
        provider="vidu",
        operation="VIDEO_GENERATION",
        shot_id=test_shot.id,
        usage_units={"duration_seconds": 4.0},
        estimated_cost=0.20,
        currency="USD",
        cost_status=CostStatus.ESTIMATED,
    )
    assert entry.id is not None
    assert entry.cost_status == CostStatus.ESTIMATED
    assert entry.estimated_cost == 0.20

    summary = CostLedgerService.get_project_summary(db_session, test_project.id)
    assert summary["total_estimated_cost"] == 0.20
    assert summary["total_confirmed_cost"] == 0.0
    assert summary["total_actual_cost"] == 0.0
    assert summary["total_committed_cost"] == 0.20
    assert len(summary["by_provider"]) == 1
    assert summary["by_provider"][0]["provider"] == "vidu"
    assert summary["by_provider"][0]["total_cost"] == 0.20


def test_idempotent_event_recording_no_duplicate_charge(db_session: Session, test_project: Project, test_shot: Shot):
    idempotency_key = "idem-key-unique-123"

    # Record first time
    e1 = CostLedgerService.record_entry(
        db=db_session,
        project_id=test_project.id,
        provider="vidu",
        operation="VIDEO_GENERATION",
        shot_id=test_shot.id,
        estimated_cost=0.20,
        cost_status=CostStatus.ESTIMATED,
        idempotency_key=idempotency_key,
    )

    # Repeat record with same idempotency_key
    e2 = CostLedgerService.record_entry(
        db=db_session,
        project_id=test_project.id,
        provider="vidu",
        operation="VIDEO_GENERATION",
        shot_id=test_shot.id,
        estimated_cost=0.20,
        cost_status=CostStatus.ESTIMATED,
        idempotency_key=idempotency_key,
    )

    assert e1.id == e2.id
    all_entries = db_session.query(UsageLedger).filter(UsageLedger.project_id == test_project.id).all()
    assert len(all_entries) == 1

    summary = CostLedgerService.get_project_summary(db_session, test_project.id)
    assert summary["total_estimated_cost"] == 0.20


def test_estimated_to_confirmed_transition(db_session: Session, test_project: Project, test_shot: Shot):
    job = GenerationJob(
        id=uuid.uuid4(),
        shot_id=test_shot.id,
        provider_name="vidu",
        status="PENDING",
    )
    db_session.add(job)
    db_session.commit()

    CostLedgerService.record_entry(
        db=db_session,
        project_id=test_project.id,
        provider="vidu",
        operation="VIDEO_GENERATION",
        shot_id=test_shot.id,
        job_id=job.id,
        estimated_cost=0.20,
        cost_status=CostStatus.ESTIMATED,
    )

    # Confirm cost upon job completion
    confirmed_entry = CostLedgerService.confirm_job_cost(
        db=db_session,
        job_id=job.id,
        actual_cost=0.18,
        provider_event_id="provider-task-999",
    )
    assert confirmed_entry is not None
    assert confirmed_entry.cost_status == CostStatus.CONFIRMED
    assert confirmed_entry.actual_cost == 0.18
    assert confirmed_entry.provider_event_id == "provider-task-999"

    summary = CostLedgerService.get_project_summary(db_session, test_project.id)
    assert summary["total_confirmed_cost"] == 0.18
    assert summary["total_estimated_cost"] == 0.0
    assert summary["total_actual_cost"] == 0.18


def test_unknown_cost_stays_unknown(db_session: Session, test_project: Project):
    entry = CostLedgerService.record_entry(
        db=db_session,
        project_id=test_project.id,
        provider="obscure_provider",
        operation="OBSCURE_OP",
        estimated_cost=None,
        actual_cost=None,
    )
    assert entry.cost_status == CostStatus.UNKNOWN
    assert entry.estimated_cost is None
    assert entry.actual_cost is None

    summary = CostLedgerService.get_project_summary(db_session, test_project.id)
    assert summary["unknown_cost_count"] == 1
    assert summary["total_committed_cost"] == 0.0


def test_hard_budget_blocks_chargeable_dispatch(db_session: Session, test_project: Project, test_shot: Shot):
    # Set low budget of $0.30
    BudgetService.update_budget(db_session, test_project.id, budget_limit=0.30)

    # 1. First dispatch requires $0.20 (4s * $0.05). Should succeed.
    job1 = JobDispatchService.create_and_dispatch_job(
        db=db_session,
        shot_id=test_shot.id,
        provider_name="vidu",
    )
    assert job1.status == "PENDING"

    # 2. Second dispatch would require another $0.20 (total $0.40 > $0.30). Must fail closed.
    with pytest.raises(HTTPException) as exc_info:
        JobDispatchService.create_and_dispatch_job(
            db=db_session,
            shot_id=test_shot.id,
            provider_name="vidu",
        )
    assert exc_info.value.status_code == 400
    assert "Project budget exceeded" in exc_info.value.detail


def test_soft_budget_threshold_warning(db_session: Session, test_project: Project):
    # Limit $10.00, Threshold 80% ($8.00)
    BudgetService.update_budget(
        db_session, test_project.id, budget_limit=10.0, budget_threshold_percentage=80.0
    )

    status_initial = BudgetService.get_budget_status(db_session, test_project.id)
    assert not status_initial["is_soft_limit_exceeded"]
    assert not status_initial["is_hard_limit_exceeded"]

    # Record $8.50 confirmed cost
    CostLedgerService.record_entry(
        db=db_session,
        project_id=test_project.id,
        provider="vidu",
        operation="VIDEO_GENERATION",
        actual_cost=8.50,
        cost_status=CostStatus.CONFIRMED,
    )

    status_after = BudgetService.get_budget_status(db_session, test_project.id)
    assert status_after["is_soft_limit_exceeded"] is True
    assert status_after["is_hard_limit_exceeded"] is False
    assert status_after["remaining_budget"] == 1.50


def test_cross_project_access_rejected(db_session: Session, test_project: Project, test_shot: Shot):
    # Project B
    project_b = Project(
        id=uuid.uuid4(),
        title="Project B",
        video_mode="SCENE",
    )
    db_session.add(project_b)
    db_session.commit()

    # Project B cannot record shot belonging to Project A
    with pytest.raises(HTTPException) as exc_info:
        CostLedgerService.record_entry(
            db=db_session,
            project_id=project_b.id,
            provider="vidu",
            operation="VIDEO_GENERATION",
            shot_id=test_shot.id,  # belongs to Project A
        )
    assert exc_info.value.status_code == 400
    assert "Shot does not belong to specified project" in exc_info.value.detail

    # Project B cannot adjust ledger entry belonging to Project A
    entry_a = CostLedgerService.record_entry(
        db=db_session,
        project_id=test_project.id,
        provider="vidu",
        operation="VIDEO_GENERATION",
        shot_id=test_shot.id,
        estimated_cost=0.50,
    )
    with pytest.raises(HTTPException) as exc_info2:
        CostLedgerService.record_adjustment(
            db=db_session,
            project_id=project_b.id,
            ledger_id=entry_a.id,
            actor="attacker",
            reason="hack",
            adjusted_cost=0.0,
        )
    assert exc_info2.value.status_code == 400
    assert "Ledger entry does not belong to specified project" in exc_info2.value.detail


def test_manual_adjustment_audit_trail(db_session: Session, test_project: Project, test_shot: Shot):
    entry = CostLedgerService.record_entry(
        db=db_session,
        project_id=test_project.id,
        provider="vidu",
        operation="VIDEO_GENERATION",
        shot_id=test_shot.id,
        estimated_cost=1.00,
        cost_status=CostStatus.ESTIMATED,
    )

    adjustment = CostLedgerService.record_adjustment(
        db=db_session,
        project_id=test_project.id,
        ledger_id=entry.id,
        actor="finance_reviewer",
        reason="Vidu platform promotional credit applied",
        adjusted_cost=0.60,
    )
    assert adjustment.previous_cost == 1.00
    assert adjustment.adjusted_cost == 0.60
    assert adjustment.actor == "finance_reviewer"

    # Verify parent entry was updated to ADJUSTED with corrected actual_cost
    db_session.refresh(entry)
    assert entry.cost_status == CostStatus.ADJUSTED
    assert entry.actual_cost == 0.60

    # Verify history is preserved
    assert len(entry.adjustments) == 1
    assert entry.adjustments[0].reason == "Vidu platform promotional credit applied"


def test_secret_safety_in_ledger_and_adjustment(db_session: Session, test_project: Project):
    secret_key = "Bearer vidu_secret_key_123456789"

    with pytest.raises(HTTPException) as exc_info:
        CostLedgerService.record_entry(
            db=db_session,
            project_id=test_project.id,
            provider=secret_key,
            operation="VIDEO_GENERATION",
        )
    assert exc_info.value.status_code == 400

    entry = CostLedgerService.record_entry(
        db=db_session,
        project_id=test_project.id,
        provider="vidu",
        operation="VIDEO_GENERATION",
        estimated_cost=0.50,
    )

    with pytest.raises(HTTPException) as exc_info2:
        CostLedgerService.record_adjustment(
            db=db_session,
            project_id=test_project.id,
            ledger_id=entry.id,
            actor="finance",
            reason=f"Applied secret {secret_key}",
            adjusted_cost=0.10,
        )
    assert exc_info2.value.status_code == 400


def test_poll_and_cancel_do_not_create_charges(db_session: Session, test_project: Project, test_shot: Shot):
    job = JobDispatchService.create_and_dispatch_job(
        db=db_session,
        shot_id=test_shot.id,
        provider_name="vidu",
    )
    entries_before = db_session.query(UsageLedger).filter(UsageLedger.project_id == test_project.id).all()
    assert len(entries_before) == 1

    # Cancellation should not create a second ledger entry
    import asyncio
    asyncio.run(JobDispatchService.cancel_job(db_session, job.id))

    entries_after = db_session.query(UsageLedger).filter(UsageLedger.project_id == test_project.id).all()
    assert len(entries_after) == 1


def test_cost_ledger_api_endpoints(client, test_project: Project, test_shot: Shot):
    # 1. Get Budget
    resp = client.get(f"/api/v1/projects/{test_project.id}/budget")
    assert resp.status_code == 200
    data = resp.json()
    assert data["project_id"] == str(test_project.id)
    assert data["budget_limit"] == 10.0

    # 2. Update Budget
    put_resp = client.put(
        f"/api/v1/projects/{test_project.id}/budget",
        json={"budget_limit": 25.0, "budget_threshold_percentage": 75.0},
    )
    assert put_resp.status_code == 200
    assert put_resp.json()["budget_limit"] == 25.0
    assert put_resp.json()["budget_threshold_percentage"] == 75.0

    # 3. Create job to create a ledger entry
    job = JobDispatchService.create_and_dispatch_job(
        db=pytest.db_session if hasattr(pytest, "db_session") else client.app.dependency_overrides.get(test_project, None) or test_shot._sa_instance_state.session,
        shot_id=test_shot.id,
        provider_name="vidu",
    )

    # 4. Get Cost Summary
    summary_resp = client.get(f"/api/v1/projects/{test_project.id}/costs/summary")
    assert summary_resp.status_code == 200
    summary_data = summary_resp.json()
    assert summary_data["total_committed_cost"] > 0

    # 5. List Ledger Entries
    list_resp = client.get(f"/api/v1/projects/{test_project.id}/costs/ledger")
    assert list_resp.status_code == 200
    entries = list_resp.json()
    assert len(entries) >= 1
    ledger_id = entries[0]["id"]

    # 6. Record Manual Adjustment via API
    adj_resp = client.post(
        f"/api/v1/projects/{test_project.id}/costs/ledger/{ledger_id}/adjustments",
        json={
            "actor": "admin_auditor",
            "reason": "Test reconciliation adjustment",
            "adjusted_cost": 0.15,
        },
    )
    assert adj_resp.status_code == 200
    adj_data = adj_resp.json()
    assert adj_data["adjusted_cost"] == 0.15
    assert adj_data["actor"] == "admin_auditor"
