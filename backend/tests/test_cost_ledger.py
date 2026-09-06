"""Focused unit, integration, and concurrency tests for P2-WP009: Cost Control & Granular Usage Audit Ledger."""
import uuid
import pytest
from unittest.mock import patch
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.project import Project
from app.models.scene import Scene
from app.models.shot import Shot
from app.models.generation_job import GenerationJob
from app.models.generation_audit import GenerationAuditLog
from app.models.usage_ledger import UsageLedger, LedgerAdjustment
from app.services.pricing import ProviderPricingService, ProviderPricingRule, CostStatus
from app.services.budget import BudgetService
from app.services.cost_ledger import CostLedgerService
from app.services.job_dispatch import JobDispatchService
from app.services.creative_generation.service import StoryGenerationService
from app.services.creative_generation.fake_provider import FakeCreativeGenerationProvider
from app.services.creative_generation.base import CreativeGenerationError


@pytest.fixture(autouse=True)
def clean_pricing_registry():
    ProviderPricingService.reset()
    yield
    ProviderPricingService.reset()


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


def test_provider_pricing_no_fabricated_rates_returns_unknown():
    # 1. Without registered pricing, provider rates are UNKNOWN, not fabricated
    cost_unk, curr_unk, status_unk = ProviderPricingService.estimate_cost(
        "vidu", "VIDEO_GENERATION", params={"duration_seconds": 4.0}
    )
    assert status_unk == CostStatus.UNKNOWN
    assert cost_unk is None

    # 2. Dynamic rule registration works without altering core domain logic
    ProviderPricingRule_custom = ProviderPricingRule(
        provider="vidu",
        operation="VIDEO_GENERATION",
        cost_per_second=0.05,
        currency="USD",
    )
    ProviderPricingService.register_rule(ProviderPricingRule_custom)
    c_cost, c_curr, c_status = ProviderPricingService.estimate_cost(
        "vidu", "VIDEO_GENERATION", params={"duration_seconds": 4.0}
    )
    assert c_status == CostStatus.ESTIMATED
    assert c_curr == "USD"
    assert c_cost == pytest.approx(0.20, rel=1e-3)


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
    # Register pricing
    ProviderPricingService.register_rule(
        ProviderPricingRule(provider="vidu", operation="VIDEO_GENERATION", cost_per_second=0.05)
    )

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


def test_atomic_reservation_rollback_on_ledger_failure(db_session: Session, test_project: Project, test_shot: Shot):
    ProviderPricingService.register_rule(
        ProviderPricingRule(provider="vidu", operation="VIDEO_GENERATION", cost_per_second=0.05)
    )
    shot_id = test_shot.id
    project_id = test_project.id

    # Simulate unexpected ledger failure during atomic dispatch
    with patch.object(CostLedgerService, "record_entry", side_effect=RuntimeError("Simulated ledger write error")):
        with pytest.raises(RuntimeError):
            JobDispatchService.create_and_dispatch_job(
                db=db_session,
                shot_id=shot_id,
                provider_name="vidu",
            )

    # Verify no orphan GenerationJob or partial record exists
    jobs = db_session.query(GenerationJob).filter(GenerationJob.shot_id == shot_id).all()
    assert len(jobs) == 0

    ledger_entries = db_session.query(UsageLedger).filter(UsageLedger.project_id == project_id).all()
    assert len(ledger_entries) == 0


def test_soft_budget_threshold_warning(db_session: Session, test_project: Project):
    BudgetService.update_budget(
        db_session, test_project.id, budget_limit=10.0, budget_threshold_percentage=80.0
    )

    status_initial = BudgetService.get_budget_status(db_session, test_project.id)
    assert not status_initial["is_soft_limit_exceeded"]
    assert not status_initial["is_hard_limit_exceeded"]

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
    project_b = Project(
        id=uuid.uuid4(),
        title="Project B",
        video_mode="SCENE",
    )
    db_session.add(project_b)
    db_session.commit()

    with pytest.raises(HTTPException) as exc_info:
        CostLedgerService.record_entry(
            db=db_session,
            project_id=project_b.id,
            provider="vidu",
            operation="VIDEO_GENERATION",
            shot_id=test_shot.id,
        )
    assert exc_info.value.status_code == 400
    assert "Shot does not belong to specified project" in exc_info.value.detail

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

    db_session.refresh(entry)
    assert entry.cost_status == CostStatus.ADJUSTED
    assert entry.actual_cost == 0.60
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

    import asyncio
    asyncio.run(JobDispatchService.cancel_job(db_session, job.id))

    entries_after = db_session.query(UsageLedger).filter(UsageLedger.project_id == test_project.id).all()
    assert len(entries_after) == 1


def test_creative_generation_ledger_failure_is_observable_and_not_swallowed(db_session: Session, test_project: Project):
    project_id = test_project.id
    fake_provider = FakeCreativeGenerationProvider()
    service = StoryGenerationService(db=db_session, provider=fake_provider)

    with patch.object(CostLedgerService, "record_entry", side_effect=RuntimeError("Simulated ledger persistence error")):
        with pytest.raises(CreativeGenerationError) as exc_info:
            service.generate_project_story(
                project_id=project_id,
                custom_instructions="Create a test story",
            )
        assert exc_info.value.code == "LEDGER_RECORDING_FAILED"
        assert "Simulated ledger persistence error" in exc_info.value.message

    # Verify audit log recorded the failure deterministically
    audit = db_session.query(GenerationAuditLog).filter(GenerationAuditLog.project_id == project_id).first()
    assert audit is not None
    assert audit.status == "ACCOUNTING_FAILED"
    assert "Usage ledger recording failed" in audit.error_message


def test_known_pre_dispatch_openai_cost_enforced(db_session: Session, test_project: Project):
    # Register pricing for openai story generation: high cost ($0.10/1k prompt tokens)
    ProviderPricingService.register_rule(
        ProviderPricingRule(
            provider="openai",
            operation="STORY_GENERATION",
            model="gpt-4o",
            cost_per_1k_prompt_tokens=10.0,
            cost_per_1k_completion_tokens=10.0,
        )
    )

    # Set project budget to $0.05
    BudgetService.update_budget(db_session, test_project.id, budget_limit=0.05)

    fake_provider = FakeCreativeGenerationProvider()
    service = StoryGenerationService(db=db_session, provider=fake_provider)

    # Prompt will produce > 100 tokens, requiring > $1.00 at $10/1k tokens -> exceeds $0.05 budget
    with pytest.raises(CreativeGenerationError) as exc_info:
        service.generate_project_story(
            project_id=test_project.id,
            custom_instructions="A long story with detailed requirements that costs more than budget",
        )
    assert exc_info.value.code == "BUDGET_EXCEEDED"
    assert "Project budget exceeded" in exc_info.value.message


def test_concurrent_dispatch_budget_race_protection(tmp_path):
    """Concurrency test showing parallel dispatch cannot exceed the hard cap."""
    import concurrent.futures
    from sqlalchemy import create_engine, event
    from sqlalchemy.orm import sessionmaker
    from app.db.base_class import Base

    db_file = tmp_path / "concurrent_budget.db"
    engine = create_engine(f"sqlite:///{db_file}", connect_args={"timeout": 30})

    @event.listens_for(engine, "begin")
    def do_begin(conn):
        conn.exec_driver_sql("BEGIN IMMEDIATE")

    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

    project_id = uuid.uuid4()
    shot_id = uuid.uuid4()
    scene_id = uuid.uuid4()

    with SessionLocal() as db:
        project = Project(
            id=project_id,
            title="Concurrent Budget Project",
            description="Testing concurrency",
            video_mode="SCENE",
            budget_limit=0.30,
            budget_currency="USD",
            budget_threshold_percentage=80.0,
        )
        scene = Scene(id=scene_id, project_id=project_id, scene_number=1, heading="Scene 1")
        shot = Shot(
            id=shot_id,
            scene_id=scene_id,
            shot_number=1,
            shot_type="AI_GENERATED",
            video_prompt="Test shot",
            duration_seconds=4.0,
        )
        db.add_all([project, scene, shot])
        db.commit()

    # Register pricing: $0.20 per dispatch ($0.05/sec * 4s = $0.20)
    ProviderPricingService.register_rule(
        ProviderPricingRule(provider="vidu", operation="VIDEO_GENERATION", cost_per_second=0.05)
    )

    results = []

    def dispatch_worker(worker_num):
        with SessionLocal() as db:
            try:
                job = JobDispatchService.create_and_dispatch_job(
                    db=db,
                    shot_id=shot_id,
                    provider_name="vidu",
                    idempotency_key=f"concurrent-key-{worker_num}",
                )
                return ("SUCCESS", str(job.id))
            except HTTPException as e:
                return ("EXCEEDED", e.detail)

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        f1 = executor.submit(dispatch_worker, 1)
        f2 = executor.submit(dispatch_worker, 2)
        f3 = executor.submit(dispatch_worker, 3)
        for f in concurrent.futures.as_completed([f1, f2, f3]):
            results.append(f.result())

    successes = [r for r in results if r[0] == "SUCCESS"]
    exceededs = [r for r in results if r[0] == "EXCEEDED"]

    # Exactly 1 can fit within $0.30 cap; other 2 must be blocked
    assert len(successes) == 1
    assert len(exceededs) == 2
    assert all("Project budget exceeded" in r[1] or "Project budget limit reached" in r[1] for r in exceededs)

    with SessionLocal() as db:
        committed = BudgetService.get_project_committed_cost(db, project_id)
        assert committed <= 0.30

    engine.dispose()
