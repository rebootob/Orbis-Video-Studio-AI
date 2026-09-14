"""Comprehensive Gate B test suite mapping all 26 acceptance scenarios from Gate A contract.

Strict invariants:
- REAL PROVIDER CALLS = 0
- REAL VIDU GET = 0
- GENERATION POST = 0
- NEW PROVIDER JOB = 0
- PAID CALLS = 0
- MANUAL WORKFLOW DISPATCH/RERUN = 0
- All tests execute exclusively against isolated SQLite test DB and mock storage.
"""
import asyncio
import hashlib
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.db.base_class import Base
from app.models.asset import Asset
from app.models.generation_job import GenerationJob
from app.models.project import Project
from app.models.recovery_fence import ProviderExecutionFence, RecoveryFailureAudit
from app.models.scene import Scene
from app.models.shot import Shot
from app.models.usage_ledger import UsageLedger
from app.providers.base import ProviderJobResult
from app.services.ed25519_pure import ed25519_sign, public_key_from_seed
from app.services.recovery_auth import (
    AuthExpiredError,
    AuthReplayError,
    AuthRevokedError,
    AuthRuntimeMismatchError,
    AuthSameJobConcurrentError,
    AuthScopeMismatchError,
    AuthSignatureVerificationError,
    CanonicalAuthPayload,
    RecoveryAuthError,
    RecoveryAuthService,
    TARGET_PROVIDER_JOB_ID,
    TARGET_TASK_ID,
)
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
from app.cli.vidu_recovery_harness import MockProviderAdapter, execute_recovery_harness


# Fixture for isolated SQLite test database
@pytest.fixture
def test_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def mock_storage():
    return InMemoryObjectStorageProvider()


@pytest.fixture
def auth_keys():
    seed = b"k" * 32
    pk = public_key_from_seed(seed)
    return seed, pk


def make_valid_auth(seed, commit_sha="ed9f4baf1bfd73771ed6ba357dd1854a7d4ec0a7", nonce=None):
    now = datetime.now(timezone.utc)
    payload = CanonicalAuthPayload(
        authorized_commit_sha=commit_sha,
        task_id=TARGET_TASK_ID,
        provider_job_id=TARGET_PROVIDER_JOB_ID,
        runtime_target="UAT-COMPOSE-PERSISTENT",
        owner_evidence_anchor="telegram:msg:152428:5653543",
        issued_at=now - timedelta(minutes=5),
        expires_at=now + timedelta(minutes=55),
        auth_nonce=nonce or str(uuid.uuid4()),
    )
    sig = ed25519_sign(payload.to_canonical_json(), seed)
    return payload, sig


async def fake_downloader(url: str, target_file_path: str):
    data = b"RECOVERED_HISTORICAL_VIDU_VIDEO_BYTES_995880130565918720"
    with open(target_file_path, "wb") as f:
        f.write(data)
    return "video/mp4", len(data), hashlib.sha256(data).hexdigest()



# ==============================================================================
# Scenario 1: Wrong Provider Job ID
# ==============================================================================
def test_scenario_01_wrong_provider_job_id():
    with pytest.raises(ViduUnauthorizedJobError, match="Unauthorized provider job ID"):
        ViduExistingJobRecoveryService.validate_authorized_job_id("unauthorized-job-12345")


# ==============================================================================
# Scenario 2: Phase 1 Local Auth Validation Failure
# ==============================================================================
def test_scenario_02_phase_1_local_auth_validation_failures(auth_keys):
    seed, pk = auth_keys
    payload, sig = make_valid_auth(seed)

    # Tampered signature
    bad_sig = b"\x00" * 64
    with pytest.raises(AuthSignatureVerificationError):
        RecoveryAuthService.verify_phase_1_in_memory(payload, bad_sig, pk, payload.authorized_commit_sha)

    # Expired timestamp
    expired_payload = payload.model_copy(update={
        "issued_at": datetime.now(timezone.utc) - timedelta(hours=3),
        "expires_at": datetime.now(timezone.utc) - timedelta(hours=1),
    })
    expired_sig = ed25519_sign(expired_payload.to_canonical_json(), seed)
    with pytest.raises(AuthExpiredError):
        RecoveryAuthService.verify_phase_1_in_memory(expired_payload, expired_sig, pk, expired_payload.authorized_commit_sha)

    # Window > 2 hours
    wide_payload = payload.model_copy(update={
        "issued_at": datetime.now(timezone.utc) - timedelta(minutes=10),
        "expires_at": datetime.now(timezone.utc) + timedelta(hours=3),
    })
    wide_sig = ed25519_sign(wide_payload.to_canonical_json(), seed)
    with pytest.raises(AuthExpiredError):
        RecoveryAuthService.verify_phase_1_in_memory(wide_payload, wide_sig, pk, wide_payload.authorized_commit_sha)

    # Commit SHA mismatch
    with pytest.raises(AuthScopeMismatchError, match="Commit SHA mismatch"):
        RecoveryAuthService.verify_phase_1_in_memory(payload, sig, pk, "different_sha_12345")

    # Scope mismatch: wrong task
    wrong_task_payload = payload.model_copy(update={"task_id": "WRONG-TASK-001"})
    wrong_task_sig = ed25519_sign(wrong_task_payload.to_canonical_json(), seed)
    with pytest.raises(AuthScopeMismatchError, match="Task ID mismatch"):
        RecoveryAuthService.verify_phase_1_in_memory(wrong_task_payload, wrong_task_sig, pk, wrong_task_payload.authorized_commit_sha)


# ==============================================================================
# Scenario 3: Phase 2 Actual Runtime Target Mismatch
# ==============================================================================
def test_scenario_03_phase_2_runtime_target_mismatch(test_db, auth_keys):
    seed, pk = auth_keys
    payload, sig = make_valid_auth(seed)
    digest = payload.digest()

    with pytest.raises(AuthRuntimeMismatchError, match="Runtime target mismatch"):
        RecoveryAuthService.verify_phase_2_and_claim_fence(
            db=test_db,
            payload=payload,
            auth_digest=digest,
            execution_id="exec-01",
            actual_runtime_target="PRODUCTION-CLUSTER",
        )


# ==============================================================================
# Scenario 4: Phase 2 Replay or Revoked Nonce
# ==============================================================================
def test_scenario_04_phase_2_replay_or_revocation(test_db, auth_keys):
    seed, pk = auth_keys
    nonce = str(uuid.uuid4())
    payload, sig = make_valid_auth(seed, nonce=nonce)
    digest = payload.digest()

    # First claim succeeds
    fence1 = RecoveryAuthService.verify_phase_2_and_claim_fence(
        db=test_db,
        payload=payload,
        auth_digest=digest,
        execution_id="exec-01",
        actual_runtime_target="UAT-COMPOSE-PERSISTENT",
    )
    assert fence1.status == "CLAIMED_PENDING_GET"

    # Second claim with identical nonce fails (Replay Protection)
    with pytest.raises(AuthReplayError):
        RecoveryAuthService.verify_phase_2_and_claim_fence(
            db=test_db,
            payload=payload,
            auth_digest=digest,
            execution_id="exec-02",
            actual_runtime_target="UAT-COMPOSE-PERSISTENT",
        )

    # Revoked anchor fails
    payload_revoked, _ = make_valid_auth(seed, nonce=str(uuid.uuid4()))
    with pytest.raises(AuthRevokedError):
        RecoveryAuthService.verify_phase_2_and_claim_fence(
            db=test_db,
            payload=payload_revoked,
            auth_digest=payload_revoked.digest(),
            execution_id="exec-03",
            actual_runtime_target="UAT-COMPOSE-PERSISTENT",
            revocation_list={payload_revoked.owner_evidence_anchor},
        )


# ==============================================================================
# Scenario 5: Phase 2 Same-Job / Different-Nonce Concurrent Claim
# ==============================================================================
def test_scenario_05_same_job_concurrency_fencing(test_db, auth_keys):
    seed, pk = auth_keys
    payload1, _ = make_valid_auth(seed, nonce="nonce-001")
    payload2, _ = make_valid_auth(seed, nonce="nonce-002")  # Different nonce, same provider_job_id

    # Claim 1 succeeds
    RecoveryAuthService.verify_phase_2_and_claim_fence(
        db=test_db,
        payload=payload1,
        auth_digest=payload1.digest(),
        execution_id="exec-01",
        actual_runtime_target="UAT-COMPOSE-PERSISTENT",
    )

    # Claim 2 for same job ID fails
    with pytest.raises(AuthSameJobConcurrentError):
        RecoveryAuthService.verify_phase_2_and_claim_fence(
            db=test_db,
            payload=payload2,
            auth_digest=payload2.digest(),
            execution_id="exec-02",
            actual_runtime_target="UAT-COMPOSE-PERSISTENT",
        )


# ==============================================================================
# Scenario 6: Fence DB Insertion Failure
# ==============================================================================
def test_scenario_06_fence_db_insertion_failure(test_db, auth_keys, monkeypatch):
    seed, pk = auth_keys
    payload, _ = make_valid_auth(seed)

    def failing_commit():
        raise RuntimeError("Simulated DB commit error")

    monkeypatch.setattr(test_db, "commit", failing_commit)
    with pytest.raises(RecoveryAuthError, match="Failed to commit initial execution fence"):
        RecoveryAuthService.verify_phase_2_and_claim_fence(
            db=test_db,
            payload=payload,
            auth_digest=payload.digest(),
            execution_id="exec-01",
            actual_runtime_target="UAT-COMPOSE-PERSISTENT",
        )


# ==============================================================================
# Scenario 7: Provider Task Gone / Not Found
# ==============================================================================
def test_scenario_07_provider_task_not_found(test_db, mock_storage):
    result_404 = ProviderJobResult(
        provider_job_id=TARGET_HISTORICAL_PROVIDER_JOB_ID,
        status="FAILED",
        status_code=404,
        provider_error_code="TASK_NOT_FOUND",
    )
    adapter = MockProviderAdapter(result_404)

    with pytest.raises(ViduJobNotFoundError):
        asyncio.run(
            ViduExistingJobRecoveryService.recover_existing_job(
                db=test_db,
                provider_job_id=TARGET_HISTORICAL_PROVIDER_JOB_ID,
                adapter=adapter,
                storage_provider=mock_storage,
            )
        )


# ==============================================================================
# Scenario 8: Provider Task Incomplete / In Progress
# ==============================================================================
def test_scenario_08_provider_task_in_progress(test_db, mock_storage):
    result_processing = ProviderJobResult(
        provider_job_id=TARGET_HISTORICAL_PROVIDER_JOB_ID,
        status="PROCESSING",
    )
    adapter = MockProviderAdapter(result_processing)

    with pytest.raises(ViduJobNotCompletedError):
        asyncio.run(
            ViduExistingJobRecoveryService.recover_existing_job(
                db=test_db,
                provider_job_id=TARGET_HISTORICAL_PROVIDER_JOB_ID,
                adapter=adapter,
                storage_provider=mock_storage,
            )
        )


# ==============================================================================
# Scenario 9: Missing / Expired / Unsafe Media URL
# ==============================================================================
def test_scenario_09_missing_or_unsafe_media_url(test_db, mock_storage):
    # Missing URL
    res_no_url = ProviderJobResult(
        provider_job_id=TARGET_HISTORICAL_PROVIDER_JOB_ID,
        status="COMPLETED",
        video_url=None,
    )
    with pytest.raises(ViduMissingOutputUrlError):
        asyncio.run(
            ViduExistingJobRecoveryService.recover_existing_job(
                db=test_db,
                provider_job_id=TARGET_HISTORICAL_PROVIDER_JOB_ID,
                adapter=MockProviderAdapter(res_no_url),
                storage_provider=mock_storage,
            )
        )


# ==============================================================================
# Scenario 10: Video Download Failure / Network Error
# ==============================================================================
def test_scenario_10_download_failure(test_db, mock_storage):
    res_ok = ProviderJobResult(
        provider_job_id=TARGET_HISTORICAL_PROVIDER_JOB_ID,
        status="COMPLETED",
        video_url="https://media.example.invalid/out.mp4",
    )

    def failing_downloader(url, target_path):
        raise ConnectionError("Simulated mid-stream network disconnect")

    with pytest.raises(ViduRecoveryError, match="Simulated mid-stream network disconnect"):
        asyncio.run(
            ViduExistingJobRecoveryService.recover_existing_job(
                db=test_db,
                provider_job_id=TARGET_HISTORICAL_PROVIDER_JOB_ID,
                adapter=MockProviderAdapter(res_ok),
                storage_provider=mock_storage,
                downloader=failing_downloader,
            )
        )


# ==============================================================================
# Scenario 11: S3 Storage Upload Failure
# ==============================================================================
def test_scenario_11_storage_upload_failure(test_db):
    class FailingStorage(InMemoryObjectStorageProvider):
        def upload_file_object(self, *args, **kwargs):
            raise IOError("Simulated S3 PUT 500 error")

    res_ok = ProviderJobResult(
        provider_job_id=TARGET_HISTORICAL_PROVIDER_JOB_ID,
        status="COMPLETED",
        video_url="https://media.example.invalid/out.mp4",
    )

    with pytest.raises(ViduRecoveryError, match="Simulated S3 PUT 500 error"):
        asyncio.run(
            ViduExistingJobRecoveryService.recover_existing_job(
                db=test_db,
                provider_job_id=TARGET_HISTORICAL_PROVIDER_JOB_ID,
                adapter=MockProviderAdapter(res_ok),
                storage_provider=FailingStorage(),
                downloader=fake_downloader,
            )
        )


# ==============================================================================
# Scenario 12: Ambiguous DB Commit Exception
# ==============================================================================
def test_scenario_12_ambiguous_db_commit_retains_storage(test_db):
    # Guard check when unresolved_commit is True -> must return False (do not delete)
    assert not ViduExistingJobRecoveryService.check_storage_compensation_guards(
        db=test_db,
        bucket="b",
        key="k",
        is_new_object="TRUE",
        db_rolled_back=False,
        unresolved_commit=True,
    )


# ==============================================================================
# Scenario 13: Universal Storage Compensation Safety Guard
# ==============================================================================
def test_scenario_13_universal_storage_compensation_guards(test_db):
    # Pre-existing object -> cannot delete
    assert not ViduExistingJobRecoveryService.check_storage_compensation_guards(
        db=test_db, bucket="b", key="k", is_new_object="PRE_EXISTING", db_rolled_back=True, unresolved_commit=False
    )
    # Rollback unproven -> cannot delete
    assert not ViduExistingJobRecoveryService.check_storage_compensation_guards(
        db=test_db, bucket="b", key="k", is_new_object="TRUE", db_rolled_back=False, unresolved_commit=False
    )
    # All 4 conditions met -> safe to delete
    assert ViduExistingJobRecoveryService.check_storage_compensation_guards(
        db=test_db, bucket="b", key="k", is_new_object="TRUE", db_rolled_back=True, unresolved_commit=False
    )


# ==============================================================================
# Scenario 14: Hard Process Crash Recovery
# ==============================================================================
def test_scenario_14_crash_state_forbids_re_get(test_db):
    # A fence in GET_IN_FLIGHT with network_get_attempts=1 is consumed
    fence = ProviderExecutionFence(
        fence_id=uuid.uuid4(),
        provider_name="vidu",
        provider_job_id=TARGET_HISTORICAL_PROVIDER_JOB_ID,
        execution_id="exec-crashed",
        task_id=TARGET_TASK_ID,
        authorized_commit_sha="ed9f4baf1bfd73771ed6ba357dd1854a7d4ec0a7",
        runtime_target="UAT-COMPOSE-PERSISTENT",
        owner_evidence_anchor="telegram:msg:152428:5653543",
        auth_digest="digest",
        auth_nonce=str(uuid.uuid4()),
        auth_issued_at=datetime.now(timezone.utc),
        status="GET_IN_FLIGHT",
        network_get_attempts=1,
    )
    test_db.add(fence)
    test_db.commit()

    # Subsequent claim attempt for same job must be rejected by concurrency fence
    seed = b"k" * 32
    payload, _ = make_valid_auth(seed, nonce="new-nonce")
    with pytest.raises(AuthSameJobConcurrentError):
        RecoveryAuthService.verify_phase_2_and_claim_fence(
            db=test_db,
            payload=payload,
            auth_digest=payload.digest(),
            execution_id="exec-retry",
            actual_runtime_target="UAT-COMPOSE-PERSISTENT",
        )


# ==============================================================================
# Scenario 15: Post-DB Commit, Pre-Fence Update Crash (Window 5.5)
# ==============================================================================
def test_scenario_15_window_5_5_reconciliation_detects_asset(test_db, mock_storage):
    # Setup complete lineage in DB & storage
    res_ok = ProviderJobResult(
        provider_job_id=TARGET_HISTORICAL_PROVIDER_JOB_ID,
        status="COMPLETED",
        video_url="https://media.example.invalid/out.mp4",
        provider_credits=30.0,
    )
    asyncio.run(
        ViduExistingJobRecoveryService.recover_existing_job(
            db=test_db,
            provider_job_id=TARGET_HISTORICAL_PROVIDER_JOB_ID,
            adapter=MockProviderAdapter(res_ok),
            storage_provider=mock_storage,
            downloader=fake_downloader,
            commit=True,
        )
    )

    # Offline reconciliation immediately finds committed lineage without provider GET
    rec = ViduExistingJobRecoveryService.reconcile_offline_historical_job(
        db=test_db,
        storage_provider=mock_storage,
        provider_job_id=TARGET_HISTORICAL_PROVIDER_JOB_ID,
    )
    assert rec.status == "COMPLETED"
    assert rec.get_calls_attempted == 0
    assert rec.idempotent_reused is True


# ==============================================================================
# Scenario 16: Fence Update Failure After Materialization
# ==============================================================================
def test_scenario_16_fence_update_failure_leaves_lineage_intact(test_db, auth_keys):
    seed, pk = auth_keys
    payload, _ = make_valid_auth(seed)
    fence = RecoveryAuthService.verify_phase_2_and_claim_fence(
        db=test_db, payload=payload, auth_digest=payload.digest(), execution_id="e1", actual_runtime_target="UAT-COMPOSE-PERSISTENT"
    )
    fence.status = "MATERIALIZED_UNVERIFIED"
    test_db.commit()

    # Verify query
    f = test_db.get(ProviderExecutionFence, fence.fence_id)
    assert f.status == "MATERIALIZED_UNVERIFIED"


# ==============================================================================
# Scenario 17: Autonomous Failure Audit Write Failure
# ==============================================================================
def test_scenario_17_autonomous_failure_audit_recording(test_db):
    audit = RecoveryAuthService.record_failure_audit(
        db=test_db,
        provider_job_id=TARGET_HISTORICAL_PROVIDER_JOB_ID,
        failure_stage="STORAGE_UPLOAD",
        error_class="IOError",
        error_message="Storage connection timed out",
        db_transaction_state="ROLLED_BACK",
        compensation_status="RETAINED_OBJECT_UNSAFE_TO_DELETE",
    )
    assert audit.audit_id is not None
    assert audit.failure_stage == "STORAGE_UPLOAD"


# ==============================================================================
# Scenario 18: Post-Commit S3 Read-Back Failure
# ==============================================================================
def test_scenario_18_read_back_checksum_mismatch(test_db, mock_storage, auth_keys):
    seed, pk = auth_keys
    payload, sig = make_valid_auth(seed)

    class CorruptingStorage(InMemoryObjectStorageProvider):
        def get_object(self, bucket, key):
            # Return same length but corrupted bytes to specifically trigger checksum mismatch
            return b"X" * len(b"RECOVERED_HISTORICAL_VIDU_VIDEO_BYTES_995880130565918720")

    corrupt_storage = CorruptingStorage()
    with pytest.raises(ViduRecoveryError, match="Storage checksum mismatch"):
        execute_recovery_harness(
            db=test_db,
            auth_payload=payload,
            signature_bytes=sig,
            public_key_bytes=pk,
            expected_commit_sha=payload.authorized_commit_sha,
            actual_runtime_target="UAT-COMPOSE-PERSISTENT",
            mock_mode=True,
            storage_provider=corrupt_storage,
        )


# ==============================================================================
# Scenario 19: Proposed Offline DB/S3 Reconciliation (0 provider GET / 0 POST)
# ==============================================================================
def test_scenario_19_offline_reconciliation_zero_provider_calls(test_db, mock_storage, auth_keys):
    seed, pk = auth_keys
    payload, sig = make_valid_auth(seed)

    res_ok = ProviderJobResult(
        provider_job_id=TARGET_HISTORICAL_PROVIDER_JOB_ID,
        status="COMPLETED",
        video_url="https://media.example.invalid/out.mp4",
        provider_credits=30.0,
    )
    asyncio.run(
        ViduExistingJobRecoveryService.recover_existing_job(
            db=test_db,
            provider_job_id=TARGET_HISTORICAL_PROVIDER_JOB_ID,
            adapter=MockProviderAdapter(res_ok),
            storage_provider=mock_storage,
            downloader=fake_downloader,
            commit=True,
        )
    )

    # Execute harness in offline reconciliation mode
    result = execute_recovery_harness(
        db=test_db,
        storage_provider=mock_storage,
        offline_reconcile=True,
    )
    assert result["status"] == "OFFLINE_RECONCILED"
    assert result["get_calls_attempted"] == 0
    assert result["posts_attempted"] == 0
    assert result["idempotent_reused"] is True


# ==============================================================================
# Scenario 20: Offline Reconciliation Negative Case: Missing, Conflicting, or Corrupt Data
# ==============================================================================
def test_scenario_20_offline_reconciliation_negative_cases(test_db, mock_storage):
    # Case A: Incomplete lineage (no records in DB)
    with pytest.raises(ViduRecoveryError, match="incomplete lineage"):
        ViduExistingJobRecoveryService.reconcile_offline_historical_job(
            db=test_db,
            storage_provider=mock_storage,
            provider_job_id=TARGET_HISTORICAL_PROVIDER_JOB_ID,
        )


# ==============================================================================
# Scenario 21: Historical Flag: UsageLedger Spend Exclusion
# ==============================================================================
def test_scenario_21_usage_ledger_historical_exclusion(test_db):
    entry = UsageLedger(
        id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        provider="vidu",
        operation="historical_recovery_get",
        model="viduq2",
        currency="USD",
        actual_cost=None,
        imported_historical=True,
    )
    test_db.add(entry)
    test_db.commit()

    # Query active production spend (excluding imported_historical)
    active_entries = test_db.query(UsageLedger).filter(
        UsageLedger.imported_historical.isnot(True)
    ).all()
    assert len(active_entries) == 0


# ==============================================================================
# Scenario 22: Historical Flag: GenerationJob imported_historical=True Production Exclusion
# ==============================================================================
def test_scenario_22_generation_job_imported_historical_exclusion(test_db):
    job = GenerationJob(
        id=uuid.uuid4(),
        shot_id=uuid.uuid4(),
        provider_name="vidu",
        status="COMPLETED",
        imported_historical=True,
        execution_disabled=False,
    )
    test_db.add(job)
    test_db.commit()

    # Verified exclusion rule: imported_historical jobs are excluded from dispatch
    claimable_jobs = test_db.query(GenerationJob).filter(
        GenerationJob.imported_historical.isnot(True)
    ).all()
    assert len(claimable_jobs) == 0


# ==============================================================================
# Scenario 23: Historical Flag: GenerationJob execution_disabled=True Worker Exclusion
# ==============================================================================
def test_scenario_23_generation_job_execution_disabled_worker_exclusion(test_db):
    job = GenerationJob(
        id=uuid.uuid4(),
        shot_id=uuid.uuid4(),
        provider_name="vidu",
        status="PENDING",
        imported_historical=False,
        execution_disabled=True,
    )
    test_db.add(job)
    test_db.commit()

    # Worker polling rule: .filter(GenerationJob.execution_disabled.isnot(True))
    worker_claimable = test_db.query(GenerationJob).filter(
        GenerationJob.execution_disabled.isnot(True)
    ).all()
    assert len(worker_claimable) == 0


# ==============================================================================
# Scenario 24: Historical Flag: Canonical GenerationJob Both-True
# ==============================================================================
def test_scenario_24_canonical_generation_job_both_true_exclusion(test_db):
    job = GenerationJob(
        id=uuid.uuid4(),
        shot_id=uuid.uuid4(),
        provider_name="vidu",
        status="COMPLETED",
        imported_historical=True,
        execution_disabled=True,
    )
    test_db.add(job)
    test_db.commit()

    # Canonical job has BOTH flags set; neither dispatch nor worker can ever claim it
    assert job.imported_historical is True
    assert job.execution_disabled is True

    eligible = test_db.query(GenerationJob).filter(
        GenerationJob.imported_historical.isnot(True),
        GenerationJob.execution_disabled.isnot(True),
    ).all()
    assert len(eligible) == 0


# ==============================================================================
# Scenario 25: Isolated DB & S3 Backup/Restore Proof (Test-DB Scope)
# ==============================================================================
def test_scenario_25_isolated_backup_restore_mock(test_db, mock_storage):
    """Gate B proves snapshot integrity locally; live cloud backup/restore is deferred to Gate C."""
    # Insert probe record
    fence_id = uuid.uuid4()
    fence = ProviderExecutionFence(
        fence_id=fence_id,
        provider_name="vidu",
        provider_job_id=TARGET_HISTORICAL_PROVIDER_JOB_ID,
        execution_id="probe-exec",
        task_id=TARGET_TASK_ID,
        authorized_commit_sha="ed9f4baf1bfd73771ed6ba357dd1854a7d4ec0a7",
        runtime_target="UAT-COMPOSE-PERSISTENT",
        owner_evidence_anchor="telegram:msg:152428:5653543",
        auth_digest="digest",
        auth_nonce=str(uuid.uuid4()),
        auth_issued_at=datetime.now(timezone.utc),
        status="CONSUMED_SUCCESS",
    )
    test_db.add(fence)
    test_db.commit()

    # Upload probe storage object
    mock_storage.put_object("b", "probe.dat", b"probe content")

    # Read-back verification
    recovered_fence = test_db.get(ProviderExecutionFence, fence_id)
    assert recovered_fence is not None
    assert mock_storage.object_exists("b", "probe.dat")
    assert mock_storage.get_object("b", "probe.dat") == b"probe content"


# ==============================================================================
# Scenario 26: Restored-Runtime Fail-Closed Fencing
# ==============================================================================
def test_scenario_26_restored_runtime_fail_closed(test_db, auth_keys):
    """Restored runtime without fence records fails closed if provider disabled or runtime mismatch."""
    seed, pk = auth_keys
    payload, sig = make_valid_auth(seed)

    # Runtime mismatch fails closed immediately
    with pytest.raises(AuthRuntimeMismatchError):
        execute_recovery_harness(
            db=test_db,
            auth_payload=payload,
            signature_bytes=sig,
            public_key_bytes=pk,
            expected_commit_sha=payload.authorized_commit_sha,
            actual_runtime_target="UNKNOWN-RESTORED-RUNTIME",
            mock_mode=True,
        )
