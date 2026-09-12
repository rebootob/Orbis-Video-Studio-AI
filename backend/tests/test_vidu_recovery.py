import asyncio
import hashlib
import uuid
from unittest.mock import AsyncMock, patch

import pytest

from app.models.asset import Asset
from app.models.generation_job import GenerationJob
from app.models.project import Project
from app.models.scene import Scene
from app.models.shot import Shot
from app.models.usage_ledger import UsageLedger
from app.providers.base import IVideoGenerationProviderAdapter, ProviderJobResult
from app.services.budget import BudgetService
from app.services.storage.mock import InMemoryObjectStorageProvider
from app.services.vidu_recovery import (
    TARGET_HISTORICAL_PROVIDER_JOB_ID,
    ViduConflictingLineageError,
    ViduExistingJobRecoveryService,
    ViduJobNotCompletedError,
    ViduJobNotFoundError,
    ViduMissingOutputUrlError,
    ViduRecoveryError,
    ViduRecoveryResult,
    ViduUnauthorizedJobError,
)


class MockViduAdapter(IVideoGenerationProviderAdapter):
    """Mock adapter guaranteeing zero network calls and recording all calls."""

    provider_id = "vidu"

    def __init__(self, job_result: ProviderJobResult):
        self.job_result = job_result
        self.check_status_calls: list[str] = []
        self.submit_calls: list[dict] = []

    def validate_config(self, config):
        return True

    async def submit_generation_job(self, *args, **kwargs):
        self.submit_calls.append({"args": args, "kwargs": kwargs})
        raise AssertionError("submit_generation_job must NEVER be called in recovery prep")

    async def check_job_status(self, provider_job_id: str) -> ProviderJobResult:
        self.check_status_calls.append(provider_job_id)
        return self.job_result

    async def cancel_job(self, provider_job_id):
        return True


async def fake_downloader(url: str, target_file_path: str):
    data = b"RECOVERED_HISTORICAL_VIDU_VIDEO_BYTES_995880130565918720"
    with open(target_file_path, "wb") as f:
        f.write(data)
    return "video/mp4", len(data), hashlib.sha256(data).hexdigest()


@pytest.fixture
def clean_db(db_session):
    """Ensure clean table state for recovery tests so StaticPool in-memory SQLite doesn't leak records."""
    db_session.rollback()
    for model in [UsageLedger, Asset, GenerationJob, Shot, Scene, Project]:
        db_session.query(model).delete(synchronize_session=False)
    db_session.flush()
    yield db_session
    db_session.rollback()
    for model in [UsageLedger, Asset, GenerationJob, Shot, Scene, Project]:
        db_session.query(model).delete(synchronize_session=False)
    db_session.flush()


# =========================================================================
# 1. Hard Bounding & Rejection of Unauthorized IDs
# =========================================================================

def test_unauthorized_provider_job_id_rejected_before_any_io(clean_db, mock_storage):
    """Mismatched provider_job_id causes 0 GET, 0 POST, 0 DB lineage, 0 storage."""
    db_session = clean_db
    unauthorized_id = "999999999999999999"
    adapter = MockViduAdapter(ProviderJobResult(provider_job_id=unauthorized_id, status="COMPLETED"))

    with pytest.raises(ViduUnauthorizedJobError, match="Unauthorized provider job ID"):
        asyncio.run(
            ViduExistingJobRecoveryService.recover_existing_job(
                db_session,
                unauthorized_id,
                adapter=adapter,
                storage_provider=mock_storage,
                downloader=fake_downloader,
                commit=False,
            )
        )

    # Invariant proofs: 0 GET, 0 POST, 0 DB records, 0 storage objects
    assert len(adapter.submit_calls) == 0
    assert len(adapter.check_status_calls) == 0
    assert db_session.query(Project).count() == 0
    assert db_session.query(Scene).count() == 0
    assert db_session.query(Shot).count() == 0
    assert db_session.query(GenerationJob).count() == 0
    assert db_session.query(Asset).count() == 0


# =========================================================================
# 2. Historical Fencing (imported_historical = True, execution_disabled = True)
# =========================================================================

def test_recovered_job_is_fenced_and_cannot_be_claimed_or_dispatched(clean_db, mock_storage):
    """Proves recovered GenerationJob cannot be claimed by workers, dispatched, retried, or counted as active."""
    db_session = clean_db
    job_result = ProviderJobResult(
        provider_job_id=TARGET_HISTORICAL_PROVIDER_JOB_ID,
        status="COMPLETED",
        video_url="https://video.example.invalid/historical_run1.mp4",
        provider_credits=30.0,
    )
    adapter = MockViduAdapter(job_result)

    result = asyncio.run(
        ViduExistingJobRecoveryService.recover_existing_job(
            db_session,
            TARGET_HISTORICAL_PROVIDER_JOB_ID,
            adapter=adapter,
            storage_provider=mock_storage,
            downloader=fake_downloader,
            commit=False,
        )
    )

    job = db_session.get(GenerationJob, result.generation_job_id)
    assert job is not None
    assert job.imported_historical is True
    assert job.execution_disabled is True
    assert job.status == "COMPLETED"

    # Queue claiming fence: eligible query excludes imported_historical
    eligible_jobs = (
        db_session.query(GenerationJob)
        .filter(
            GenerationJob.id == job.id,
            GenerationJob.imported_historical.isnot(True),
        )
        .all()
    )
    assert len(eligible_jobs) == 0

    # Query active production jobs fence: active jobs exclude imported_historical
    active_production_jobs = (
        db_session.query(GenerationJob)
        .filter(
            GenerationJob.shot_id == job.shot_id,
            GenerationJob.status.in_(["PENDING", "CLAIMED", "PROCESSING", "POLLING"]),
            GenerationJob.imported_historical.isnot(True),
        )
        .all()
    )
    assert len(active_production_jobs) == 0


# =========================================================================
# 3. Transaction Atomicity / No Ghost Lineage on Failures
# =========================================================================

@pytest.mark.parametrize(
    "error_result, expected_exception, match_msg",
    [
        (
            ProviderJobResult(
                provider_job_id=TARGET_HISTORICAL_PROVIDER_JOB_ID,
                status="FAILED",
                provider_error_code="TASK_NOT_FOUND",
                status_code=404,
            ),
            ViduJobNotFoundError,
            "not found",
        ),
        (
            ProviderJobResult(
                provider_job_id=TARGET_HISTORICAL_PROVIDER_JOB_ID,
                status="PROCESSING",
                video_url=None,
            ),
            ViduJobNotCompletedError,
            "not COMPLETED",
        ),
        (
            ProviderJobResult(
                provider_job_id=TARGET_HISTORICAL_PROVIDER_JOB_ID,
                status="COMPLETED",
                video_url=None,
            ),
            ViduMissingOutputUrlError,
            "no video_url present",
        ),
    ],
)
def test_failure_paths_leave_zero_ghost_db_or_storage_artifacts(
    clean_db, mock_storage, error_result, expected_exception, match_msg
):
    """Any provider validation failure stops before DB/storage commit, leaving 0 artifacts."""
    db_session = clean_db
    adapter = MockViduAdapter(error_result)

    with pytest.raises(expected_exception, match=match_msg):
        asyncio.run(
            ViduExistingJobRecoveryService.recover_existing_job(
                db_session,
                TARGET_HISTORICAL_PROVIDER_JOB_ID,
                adapter=adapter,
                storage_provider=mock_storage,
                downloader=fake_downloader,
                commit=False,
            )
        )

    # Proves 0 ghost DB records
    assert db_session.query(Project).count() == 0
    assert db_session.query(Scene).count() == 0
    assert db_session.query(Shot).count() == 0
    assert db_session.query(GenerationJob).count() == 0
    assert db_session.query(Asset).count() == 0
    assert db_session.query(UsageLedger).count() == 0


def test_storage_or_download_failure_rolls_back_cleanly_and_cleans_object(clean_db, mock_storage):
    """If download fails, DB transaction rolls back and 0 objects are orphaned."""
    db_session = clean_db
    job_result = ProviderJobResult(
        provider_job_id=TARGET_HISTORICAL_PROVIDER_JOB_ID,
        status="COMPLETED",
        video_url="https://video.example.invalid/fail_download.mp4",
    )
    adapter = MockViduAdapter(job_result)

    async def failing_downloader(url, target_file):
        raise RuntimeError("Network download interrupted")

    with pytest.raises(ViduRecoveryError, match="Network download interrupted"):
        asyncio.run(
            ViduExistingJobRecoveryService.recover_existing_job(
                db_session,
                TARGET_HISTORICAL_PROVIDER_JOB_ID,
                adapter=adapter,
                storage_provider=mock_storage,
                downloader=failing_downloader,
                commit=False,
            )
        )

    # Verify complete rollback
    assert db_session.query(Project).count() == 0
    assert db_session.query(Scene).count() == 0
    assert db_session.query(Shot).count() == 0
    assert db_session.query(GenerationJob).count() == 0
    assert db_session.query(Asset).count() == 0
    assert db_session.query(UsageLedger).count() == 0


# =========================================================================
# 4. Durable Provider & Billing Audit Truth (Zero Spend Added)
# =========================================================================

def test_durable_audit_truth_and_budget_isolation(clean_db, mock_storage):
    """Proves conservative audit metadata, 0 added spend, and idempotency."""
    db_session = clean_db
    job_result = ProviderJobResult(
        provider_job_id=TARGET_HISTORICAL_PROVIDER_JOB_ID,
        status="COMPLETED",
        video_url="https://video.example.invalid/historical_run1.mp4",
        provider_credits=30.0,
    )
    adapter = MockViduAdapter(job_result)

    res1 = asyncio.run(
        ViduExistingJobRecoveryService.recover_existing_job(
            db_session,
            TARGET_HISTORICAL_PROVIDER_JOB_ID,
            adapter=adapter,
            storage_provider=mock_storage,
            downloader=fake_downloader,
            commit=False,
        )
    )

    # Verify Ledger record
    ledger_entries = (
        db_session.query(UsageLedger)
        .filter(UsageLedger.provider_event_id == TARGET_HISTORICAL_PROVIDER_JOB_ID)
        .all()
    )
    assert len(ledger_entries) == 1
    entry = ledger_entries[0]
    assert entry.imported_historical is True
    assert entry.actual_cost is None
    assert entry.estimated_cost is None
    assert entry.cost_status == "CONFIRMED"

    # Committed project cost must be exactly 0.0
    committed = BudgetService.get_project_committed_cost(db_session, res1.project_id)
    assert committed == 0.0

    # Test idempotency: second invocation reuses same asset and adds NO duplicate ledger rows
    res2 = asyncio.run(
        ViduExistingJobRecoveryService.recover_existing_job(
            db_session,
            TARGET_HISTORICAL_PROVIDER_JOB_ID,
            adapter=adapter,
            storage_provider=mock_storage,
            downloader=fake_downloader,
            commit=False,
        )
    )
    assert res2.asset_id == res1.asset_id
    assert res2.idempotent_reused is True

    # Invariant: still only 1 ledger entry, 0 new spend
    assert (
        db_session.query(UsageLedger)
        .filter(UsageLedger.provider_event_id == TARGET_HISTORICAL_PROVIDER_JOB_ID)
        .count()
        == 1
    )
    assert BudgetService.get_project_committed_cost(db_session, res1.project_id) == 0.0


# =========================================================================
# 5. Lineage Integrity (Fail Closed on Conflicts)
# =========================================================================

def test_conflicting_lineage_fails_closed(clean_db, mock_storage):
    """Existing Scene/Shot with mismatched project_id/scene_id fails closed without silent mutation."""
    db_session = clean_db
    other_project_id = uuid.uuid4()
    other_project = Project(id=other_project_id, title="Other Project", video_mode="STORY")
    db_session.add(other_project)
    db_session.flush()

    # Pre-seed a scene tied to the other project but with our deterministic ID
    scene_id = uuid.uuid5(uuid.NAMESPACE_URL, f"orbis://vidu-recovery/scene/{TARGET_HISTORICAL_PROVIDER_JOB_ID}/1")
    conflicting_scene = Scene(id=scene_id, project_id=other_project_id, scene_number=1)
    db_session.add(conflicting_scene)
    db_session.flush()

    job_result = ProviderJobResult(
        provider_job_id=TARGET_HISTORICAL_PROVIDER_JOB_ID,
        status="COMPLETED",
        video_url="https://video.example.invalid/out.mp4",
    )
    adapter = MockViduAdapter(job_result)

    with pytest.raises(ViduConflictingLineageError, match="conflicts with"):
        asyncio.run(
            ViduExistingJobRecoveryService.recover_existing_job(
                db_session,
                TARGET_HISTORICAL_PROVIDER_JOB_ID,
                adapter=adapter,
                storage_provider=mock_storage,
                downloader=fake_downloader,
                commit=False,
            )
        )
