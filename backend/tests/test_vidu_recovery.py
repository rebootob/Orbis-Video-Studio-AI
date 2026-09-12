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
from app.services.job_dispatch import JobDispatchService
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

    # Canonical claiming fence: claim_next_job excludes execution_disabled / imported_historical
    claimed = JobDispatchService.claim_next_job(db_session, worker_id="test-worker")
    assert claimed is None

    # Canonical queue querying fence: eligible query excludes imported_historical and execution_disabled
    eligible_jobs = (
        db_session.query(GenerationJob)
        .filter(
            GenerationJob.id == job.id,
            GenerationJob.imported_historical.isnot(True),
            GenerationJob.execution_disabled.isnot(True),
        )
        .all()
    )
    assert len(eligible_jobs) == 0

    # Active production jobs query fence: excludes imported_historical and execution_disabled
    active_production_jobs = (
        db_session.query(GenerationJob)
        .filter(
            GenerationJob.shot_id == job.shot_id,
            GenerationJob.status.in_(["PENDING", "CLAIMED", "PROCESSING", "POLLING"]),
            GenerationJob.imported_historical.isnot(True),
            GenerationJob.execution_disabled.isnot(True),
        )
        .all()
    )
    assert len(active_production_jobs) == 0

    # Polling status fence: poll_job_status rejects imported_historical / execution_disabled
    can_poll = (
        job.status in ["PENDING", "CLAIMED", "PROCESSING", "POLLING"]
        and bool(job.provider_job_id)
        and not job.imported_historical
        and not job.execution_disabled
    )
    assert can_poll is False


# =========================================================================
# 3. Transaction Atomicity / Clean Rollback (Zero Ghost Lineage)
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


def test_unsafe_private_url_leaves_zero_lineage_and_storage(clean_db, mock_storage):
    """Private / loopback / SSRF URLs are rejected leaving 0 DB records and 0 storage objects."""
    db_session = clean_db
    job_result = ProviderJobResult(
        provider_job_id=TARGET_HISTORICAL_PROVIDER_JOB_ID,
        status="COMPLETED",
        video_url="https://127.0.0.1/private_video.mp4",
    )
    adapter = MockViduAdapter(job_result)

    with pytest.raises(ViduRecoveryError, match="URL validation failed"):
        asyncio.run(
            ViduExistingJobRecoveryService.recover_existing_job(
                db_session,
                TARGET_HISTORICAL_PROVIDER_JOB_ID,
                adapter=adapter,
                storage_provider=mock_storage,
                downloader=None,  # Trigger real URL validation
                commit=False,
            )
        )

    assert db_session.query(Project).count() == 0
    assert db_session.query(Scene).count() == 0
    assert db_session.query(Shot).count() == 0
    assert db_session.query(GenerationJob).count() == 0
    assert db_session.query(Asset).count() == 0
    assert db_session.query(UsageLedger).count() == 0


def test_storage_upload_failure_rolls_back_cleanly(clean_db):
    """If storage upload fails, DB rolls back and 0 DB records remain."""
    db_session = clean_db
    job_result = ProviderJobResult(
        provider_job_id=TARGET_HISTORICAL_PROVIDER_JOB_ID,
        status="COMPLETED",
        video_url="https://video.example.invalid/out.mp4",
    )
    adapter = MockViduAdapter(job_result)

    class FailingStorage(InMemoryObjectStorageProvider):
        def upload_file_object(self, *args, **kwargs):
            raise IOError("S3 network write timeout")

    failing_storage = FailingStorage()

    with pytest.raises(ViduRecoveryError, match="S3 network write timeout"):
        asyncio.run(
            ViduExistingJobRecoveryService.recover_existing_job(
                db_session,
                TARGET_HISTORICAL_PROVIDER_JOB_ID,
                adapter=adapter,
                storage_provider=failing_storage,
                downloader=fake_downloader,
                commit=False,
            )
        )

    assert db_session.query(Project).count() == 0
    assert db_session.query(Scene).count() == 0
    assert db_session.query(Shot).count() == 0
    assert db_session.query(GenerationJob).count() == 0
    assert db_session.query(Asset).count() == 0
    assert db_session.query(UsageLedger).count() == 0


def test_db_commit_failure_after_new_upload_cleans_new_storage_object(clean_db, mock_storage):
    """If upload succeeds but commit fails, storage compensation deletes the new object and rolls back DB."""
    db_session = clean_db
    job_result = ProviderJobResult(
        provider_job_id=TARGET_HISTORICAL_PROVIDER_JOB_ID,
        status="COMPLETED",
        video_url="https://video.example.invalid/out.mp4",
    )
    adapter = MockViduAdapter(job_result)

    with patch.object(db_session, "commit", side_effect=RuntimeError("Database lock conflict on commit")):
        with pytest.raises(ViduRecoveryError, match="Database lock conflict on commit"):
            asyncio.run(
                ViduExistingJobRecoveryService.recover_existing_job(
                    db_session,
                    TARGET_HISTORICAL_PROVIDER_JOB_ID,
                    adapter=adapter,
                    storage_provider=mock_storage,
                    downloader=fake_downloader,
                    commit=True,
                )
            )

    # Invariants: 0 DB records, 0 orphaned objects in storage
    assert db_session.query(Project).count() == 0
    assert db_session.query(Scene).count() == 0
    assert db_session.query(Shot).count() == 0
    assert db_session.query(GenerationJob).count() == 0
    assert db_session.query(Asset).count() == 0
    assert db_session.query(UsageLedger).count() == 0
    assert len(mock_storage._store) == 0


# =========================================================================
# 4. Durable Provider & Billing Audit Truth (Zero Spend Added)
# =========================================================================

def test_durable_audit_truth_and_budget_isolation(clean_db, mock_storage):
    """Proves conservative audit metadata, cost_status=UNKNOWN, 0 added spend, and idempotency."""
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

    assert res1.get_calls_attempted == 1
    assert res1.provider_credits_reported == 30.0

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
    assert entry.cost_status == "UNKNOWN"

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
    # Accurate GET count
    assert res2.get_calls_attempted == 1
    assert len(adapter.check_status_calls) == 2

    # Invariant: still only 1 ledger entry, 0 new spend
    assert (
        db_session.query(UsageLedger)
        .filter(UsageLedger.provider_event_id == TARGET_HISTORICAL_PROVIDER_JOB_ID)
        .count()
        == 1
    )
    assert BudgetService.get_project_committed_cost(db_session, res1.project_id) == 0.0


def test_idempotent_path_with_missing_provider_credits_retains_none(clean_db, mock_storage):
    """When provider omits credits, provider_credits_reported remains None, never hardcoded."""
    db_session = clean_db
    job_result = ProviderJobResult(
        provider_job_id=TARGET_HISTORICAL_PROVIDER_JOB_ID,
        status="COMPLETED",
        video_url="https://video.example.invalid/out.mp4",
        provider_credits=None,
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
    assert res1.provider_credits_reported is None

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
    assert res2.provider_credits_reported is None
    assert res2.idempotent_reused is True


def test_idempotent_audit_evidence_repair(clean_db, mock_storage):
    """Non-conflicting incomplete fencing or audit state is safely repaired during idempotent recovery."""
    db_session = clean_db
    job_result = ProviderJobResult(
        provider_job_id=TARGET_HISTORICAL_PROVIDER_JOB_ID,
        status="COMPLETED",
        video_url="https://video.example.invalid/out.mp4",
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

    # Intentionally degrade non-conflicting fields
    job = db_session.get(GenerationJob, res1.generation_job_id)
    job.imported_historical = False
    job.execution_disabled = False
    shot = db_session.get(Shot, res1.shot_id)
    shot.source_asset_id = None
    ledger = db_session.query(UsageLedger).first()
    db_session.delete(ledger)
    db_session.flush()

    # Second recovery pass repairs the missing audit/fencing state
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

    repaired_job = db_session.get(GenerationJob, res2.generation_job_id)
    assert repaired_job.imported_historical is True
    assert repaired_job.execution_disabled is True
    repaired_shot = db_session.get(Shot, res2.shot_id)
    assert repaired_shot.source_asset_id == res2.asset_id
    repaired_ledger = db_session.query(UsageLedger).first()
    assert repaired_ledger is not None
    assert repaired_ledger.cost_status == "UNKNOWN"
    assert repaired_ledger.imported_historical is True


# =========================================================================
# 5. Lineage Integrity (Fail Closed on Conflicts)
# =========================================================================

def test_conflicting_lineage_scene_project_id_fails_closed(clean_db, mock_storage):
    """Existing Scene with mismatched project_id fails closed without silent mutation."""
    db_session = clean_db
    other_project_id = uuid.uuid4()
    other_project = Project(id=other_project_id, title="Other Project", video_mode="STORY")
    db_session.add(other_project)
    db_session.flush()

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


def test_conflicting_lineage_shot_scene_id_fails_closed(clean_db, mock_storage):
    """Existing Shot with mismatched scene_id fails closed without silent mutation."""
    db_session = clean_db
    project_id = uuid.uuid5(uuid.NAMESPACE_URL, f"orbis://vidu-recovery/project/{TARGET_HISTORICAL_PROVIDER_JOB_ID}")
    other_scene_id = uuid.uuid4()

    shot_id = uuid.uuid5(uuid.NAMESPACE_URL, f"orbis://vidu-recovery/shot/{TARGET_HISTORICAL_PROVIDER_JOB_ID}/1")
    conflicting_shot = Shot(id=shot_id, scene_id=other_scene_id, shot_number=1, shot_type="VIDEO")
    db_session.add(conflicting_shot)
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


def test_conflicting_generation_job_provider_id_fails_closed(clean_db, mock_storage):
    """Existing GenerationJob with mismatched provider_job_id fails closed."""
    db_session = clean_db
    job_id = uuid.uuid5(uuid.NAMESPACE_URL, f"orbis://vidu-recovery/job/{TARGET_HISTORICAL_PROVIDER_JOB_ID}")
    asset_id = uuid.uuid5(uuid.NAMESPACE_URL, f"orbis://video-generation/{job_id}")
    project_id = uuid.uuid5(uuid.NAMESPACE_URL, f"orbis://vidu-recovery/project/{TARGET_HISTORICAL_PROVIDER_JOB_ID}")
    shot_id = uuid.uuid5(uuid.NAMESPACE_URL, f"orbis://vidu-recovery/shot/{TARGET_HISTORICAL_PROVIDER_JOB_ID}/1")

    job = GenerationJob(
        id=job_id,
        shot_id=shot_id,
        job_type="VIDEO",
        provider_name="vidu",
        provider_job_id="OTHER_PROVIDER_JOB_ID",
        output_asset_id=asset_id,
        status="COMPLETED",
    )
    asset = Asset(
        id=asset_id,
        project_id=project_id,
        name="Recovered",
        original_filename="rec.mp4",
        asset_type="VIDEO",
        content_type="video/mp4",
        file_size_bytes=100,
        checksum_sha256="abc",
        storage_bucket="orbis-assets",
        storage_key="test",
    )
    db_session.add(job)
    db_session.add(asset)
    db_session.flush()

    job_result = ProviderJobResult(
        provider_job_id=TARGET_HISTORICAL_PROVIDER_JOB_ID,
        status="COMPLETED",
        video_url="https://video.example.invalid/out.mp4",
    )
    adapter = MockViduAdapter(job_result)

    with pytest.raises(ViduConflictingLineageError, match="has provider_job_id"):
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


def test_conflicting_asset_project_id_fails_closed(clean_db, mock_storage):
    """Existing Asset with mismatched project_id fails closed."""
    db_session = clean_db
    job_id = uuid.uuid5(uuid.NAMESPACE_URL, f"orbis://vidu-recovery/job/{TARGET_HISTORICAL_PROVIDER_JOB_ID}")
    asset_id = uuid.uuid5(uuid.NAMESPACE_URL, f"orbis://video-generation/{job_id}")
    other_project_id = uuid.uuid4()
    shot_id = uuid.uuid5(uuid.NAMESPACE_URL, f"orbis://vidu-recovery/shot/{TARGET_HISTORICAL_PROVIDER_JOB_ID}/1")

    job = GenerationJob(
        id=job_id,
        shot_id=shot_id,
        job_type="VIDEO",
        provider_name="vidu",
        provider_job_id=TARGET_HISTORICAL_PROVIDER_JOB_ID,
        output_asset_id=asset_id,
        status="COMPLETED",
    )
    asset = Asset(
        id=asset_id,
        project_id=other_project_id,
        name="Recovered",
        original_filename="rec.mp4",
        asset_type="VIDEO",
        content_type="video/mp4",
        file_size_bytes=100,
        checksum_sha256="abc",
        storage_bucket="orbis-assets",
        storage_key="test",
    )
    db_session.add(job)
    db_session.add(asset)
    db_session.flush()

    job_result = ProviderJobResult(
        provider_job_id=TARGET_HISTORICAL_PROVIDER_JOB_ID,
        status="COMPLETED",
        video_url="https://video.example.invalid/out.mp4",
    )
    adapter = MockViduAdapter(job_result)

def test_returned_provider_job_id_mismatch_fails_closed(clean_db, mock_storage):
    """If provider returns mismatched provider_job_id, recovery fails closed."""
    db_session = clean_db
    job_result = ProviderJobResult(
        provider_job_id="DIFFERENT_RETURNED_ID",
        status="COMPLETED",
        video_url="https://video.example.invalid/out.mp4",
    )
    adapter = MockViduAdapter(job_result)

    with pytest.raises(ViduConflictingLineageError, match="mismatched provider_job_id"):
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


def test_exception_after_successful_durable_commit_leaves_storage_and_db_intact(clean_db, mock_storage):
    """If post-commit result construction or notification fails, DB records and storage object remain intact."""
    db_session = clean_db
    job_result = ProviderJobResult(
        provider_job_id=TARGET_HISTORICAL_PROVIDER_JOB_ID,
        status="COMPLETED",
        video_url="https://video.example.invalid/out.mp4",
        provider_credits=30.0,
    )
    adapter = MockViduAdapter(job_result)

    with patch.object(ViduExistingJobRecoveryService, "_post_commit_hook", side_effect=RuntimeError("Post-commit packaging failure")):
        with pytest.raises(ViduRecoveryError, match="Post-commit packaging failure"):
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

    # Invariants: Committed DB records remain, storage object remains, no dangling reference
    assert db_session.query(Project).count() == 1
    assert db_session.query(Scene).count() == 1
    assert db_session.query(Shot).count() == 1
    assert db_session.query(GenerationJob).count() == 1
    assert db_session.query(Asset).count() == 1
    assert db_session.query(UsageLedger).count() == 1
    assert len(mock_storage._store) == 1


def test_first_get_credits_30_followed_by_get_credits_none_preserves_durable_credits(clean_db, mock_storage):
    """If first recovery records credits=30.0, a later idempotent GET with credits=None preserves retained 30.0."""
    db_session = clean_db
    job_result_with_credits = ProviderJobResult(
        provider_job_id=TARGET_HISTORICAL_PROVIDER_JOB_ID,
        status="COMPLETED",
        video_url="https://video.example.invalid/out.mp4",
        provider_credits=30.0,
    )
    adapter1 = MockViduAdapter(job_result_with_credits)

    res1 = asyncio.run(
        ViduExistingJobRecoveryService.recover_existing_job(
            db_session,
            TARGET_HISTORICAL_PROVIDER_JOB_ID,
            adapter=adapter1,
            storage_provider=mock_storage,
            downloader=fake_downloader,
            commit=False,
        )
    )
    assert res1.provider_credits_reported == 30.0

    # Second recovery where provider omits credits
    job_result_without_credits = ProviderJobResult(
        provider_job_id=TARGET_HISTORICAL_PROVIDER_JOB_ID,
        status="COMPLETED",
        video_url="https://video.example.invalid/out.mp4",
        provider_credits=None,
    )
    adapter2 = MockViduAdapter(job_result_without_credits)

    res2 = asyncio.run(
        ViduExistingJobRecoveryService.recover_existing_job(
            db_session,
            TARGET_HISTORICAL_PROVIDER_JOB_ID,
            adapter=adapter2,
            storage_provider=mock_storage,
            downloader=fake_downloader,
            commit=False,
        )
    )
    assert res2.idempotent_reused is True
    # Retained credit evidence is preserved
    assert res2.provider_credits_reported == 30.0
    job = db_session.get(GenerationJob, res2.generation_job_id)
    assert job.result["provider_credits_reported"] == 30.0


def test_no_credit_history_remains_none_when_credits_were_never_reported(clean_db, mock_storage):
    """If credits were never reported, credits remain None across repeated idempotent recovery."""
    db_session = clean_db
    job_result_none = ProviderJobResult(
        provider_job_id=TARGET_HISTORICAL_PROVIDER_JOB_ID,
        status="COMPLETED",
        video_url="https://video.example.invalid/out.mp4",
        provider_credits=None,
    )
    adapter = MockViduAdapter(job_result_none)

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
    assert res1.provider_credits_reported is None

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
    assert res2.provider_credits_reported is None
    job = db_session.get(GenerationJob, res2.generation_job_id)
    assert job.result["provider_credits_reported"] is None


def test_conflicting_usage_ledger_bindings_fail_closed(clean_db, mock_storage):
    """Conflicting UsageLedger fields cause idempotent recovery to fail closed."""
    db_session = clean_db
    job_result = ProviderJobResult(
        provider_job_id=TARGET_HISTORICAL_PROVIDER_JOB_ID,
        status="COMPLETED",
        video_url="https://video.example.invalid/out.mp4",
        provider_credits=30.0,
    )
    adapter = MockViduAdapter(job_result)

    # Initial successful recovery
    res = asyncio.run(
        ViduExistingJobRecoveryService.recover_existing_job(
            db_session,
            TARGET_HISTORICAL_PROVIDER_JOB_ID,
            adapter=adapter,
            storage_provider=mock_storage,
            downloader=fake_downloader,
            commit=False,
        )
    )

    ledger = db_session.query(UsageLedger).first()
    # Tamper with provider binding to trigger conflict
    ledger.provider = "other_provider"
    db_session.flush()

    with pytest.raises(ViduConflictingLineageError, match="provider 'other_provider' != 'vidu'"):
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


def test_conflicting_asset_type_fails_closed(clean_db, mock_storage):
    """Conflicting Asset asset_type causes idempotent recovery to fail closed."""
    db_session = clean_db
    job_result = ProviderJobResult(
        provider_job_id=TARGET_HISTORICAL_PROVIDER_JOB_ID,
        status="COMPLETED",
        video_url="https://video.example.invalid/out.mp4",
        provider_credits=30.0,
    )
    adapter = MockViduAdapter(job_result)

    res = asyncio.run(
        ViduExistingJobRecoveryService.recover_existing_job(
            db_session,
            TARGET_HISTORICAL_PROVIDER_JOB_ID,
            adapter=adapter,
            storage_provider=mock_storage,
            downloader=fake_downloader,
            commit=False,
        )
    )

    asset = db_session.get(Asset, res.asset_id)
    asset.asset_type = "AUDIO"
    db_session.flush()

    with pytest.raises(ViduConflictingLineageError, match="asset_type 'AUDIO' != 'VIDEO'"):
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

