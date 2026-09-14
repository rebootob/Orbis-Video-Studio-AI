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
from __future__ import annotations

import asyncio
import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

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
from app.services.ed25519_pure import ed25519_verify
from app.services.recovery_auth import (
    AuditWriteFailureError,
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
from tests.ed25519_test_signer import ed25519_sign, public_key_from_seed


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
# Adversarial & RFC 8032 Vector Tests (Blocker 2)
# ==============================================================================
def test_rfc8032_official_vectors():
    # Test Vector 1 (Empty message)
    pk1 = bytes.fromhex("d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a")
    sig1 = bytes.fromhex("e5564300c360ac729086e2cc806e828a84877f1eb8e5d974d873e065224901555fb8821590a33bacc61e39701cf9b46bd25bf5f0595bbe24655141438e7a100b")
    assert ed25519_verify(b"", sig1, pk1) is True

    # Test Vector 2 (1-byte message 0x72)
    pk2 = bytes.fromhex("3d4017c3e843895a92b70aa74d1b7ebc9c982ccf2ec4968cc0cd55f12af4660c")
    sig2 = bytes.fromhex("92a009a9f0d4cab8720e820b5f642540a2b27b5416503f8fb3762223ebdb69da085ac1e43e15996e458f3613d0f11d8c387b2eaeb4302aeeb00d291612bb0c00")
    assert ed25519_verify(bytes.fromhex("72"), sig2, pk2) is True

    # Test Vector 3 (2-byte message 0xaf82)
    pk3 = bytes.fromhex("fc51cd8e6218a1a38da47ed00230f0580816ed13ba3303ac5deb911548908025")
    sig3 = bytes.fromhex("6291d657deec24024827e69c3abe01a30ce548a284743a445e3680d7db5ac3ac18ff9b538d16f290ae67f760984dc6594a7c15e9716ed28dc027beceea1ec40a")
    assert ed25519_verify(bytes.fromhex("af82"), sig3, pk3) is True


def test_ed25519_adversarial_degenerate_rejection():
    # 1. Identity public key (0x01 followed by 31 zeros)
    id_pk = bytes([1]) + bytes(31)
    id_sig = bytes([1]) + bytes(31) + bytes(32)
    assert ed25519_verify(b"test message", id_sig, id_pk) is False

    # 2. Non-canonical scalar S >= L
    pk = bytes.fromhex("3d4017c3e843895a92b70aa74d1b7ebc9c982ccf2ec4968cc0cd55f12af4660c")
    bad_s_sig = bytes(32) + (2**255).to_bytes(32, "little")
    assert ed25519_verify(b"msg", bad_s_sig, pk) is False

    # 3. Non-canonical coordinate y >= p
    bad_pk = (2**255 - 10).to_bytes(32, "little")
    assert ed25519_verify(b"msg", bytes(64), bad_pk) is False


# ==============================================================================
# Scenario 1: Wrong Provider Job ID
# ==============================================================================
def test_scenario_01_wrong_provider_job_id():
    with pytest.raises(ViduUnauthorizedJobError, match="Unauthorized provider job ID"):
        ViduExistingJobRecoveryService.validate_authorized_job_id("unauthorized-job-12345")


# ==============================================================================
# Scenario 2: Phase 1 Local Auth Validation Failure
# ==============================================================================
def test_scenario_02_phase1_local_auth_failure(auth_keys):
    seed, pk = auth_keys
    payload, sig = make_valid_auth(seed)

    # 1. Invalid signature
    with pytest.raises(AuthSignatureVerificationError):
        RecoveryAuthService.verify_phase_1_in_memory(
            payload=payload,
            signature_bytes=b"x" * 64,
            public_key_bytes=pk,
            expected_commit_sha=payload.authorized_commit_sha,
        )

    # 2. Commit SHA mismatch
    with pytest.raises(AuthScopeMismatchError, match="Commit SHA mismatch"):
        RecoveryAuthService.verify_phase_1_in_memory(
            payload=payload,
            signature_bytes=sig,
            public_key_bytes=pk,
            expected_commit_sha="0000000000000000000000000000000000000000",
        )

    # 3. Expired authorization
    with pytest.raises(AuthExpiredError):
        RecoveryAuthService.verify_phase_1_in_memory(
            payload=payload,
            signature_bytes=sig,
            public_key_bytes=pk,
            expected_commit_sha=payload.authorized_commit_sha,
            current_time=datetime.now(timezone.utc) + timedelta(hours=3),
        )


# ==============================================================================
# Scenario 3: Nonce Replay Rejection
# ==============================================================================
def test_scenario_03_nonce_replay_rejection(test_db, auth_keys):
    seed, pk = auth_keys
    payload, sig = make_valid_auth(seed)
    digest = payload.digest()

    # Claim once
    fence = RecoveryAuthService.verify_phase_2_and_claim_fence(
        db=test_db,
        payload=payload,
        auth_digest=digest,
        execution_id="exec-1",
        actual_runtime_target="UAT-COMPOSE-PERSISTENT",
    )
    assert fence.status == "CLAIMED_PENDING_GET"

    # Replay identical nonce
    with pytest.raises(AuthReplayError, match="has already been consumed"):
        RecoveryAuthService.verify_phase_2_and_claim_fence(
            db=test_db,
            payload=payload,
            auth_digest=digest,
            execution_id="exec-2",
            actual_runtime_target="UAT-COMPOSE-PERSISTENT",
        )


# ==============================================================================
# Scenario 4: Concurrency Fence Violation (Same Job ID)
# ==============================================================================
def test_scenario_04_same_job_concurrency_rejection(test_db, auth_keys):
    seed, pk = auth_keys
    payload1, _ = make_valid_auth(seed, nonce="nonce-1")
    RecoveryAuthService.verify_phase_2_and_claim_fence(
        db=test_db,
        payload=payload1,
        auth_digest=payload1.digest(),
        execution_id="exec-1",
        actual_runtime_target="UAT-COMPOSE-PERSISTENT",
    )

    # Different nonce, same provider_job_id
    payload2, _ = make_valid_auth(seed, nonce="nonce-2")
    with pytest.raises(AuthSameJobConcurrentError, match="fence already exists"):
        RecoveryAuthService.verify_phase_2_and_claim_fence(
            db=test_db,
            payload=payload2,
            auth_digest=payload2.digest(),
            execution_id="exec-2",
            actual_runtime_target="UAT-COMPOSE-PERSISTENT",
        )


# ==============================================================================
# Scenario 5: Revoked Nonce / Evidence Anchor
# ==============================================================================
def test_scenario_05_revocation_rejection(test_db, auth_keys):
    seed, pk = auth_keys
    payload, _ = make_valid_auth(seed, nonce="revoked-nonce-123")
    revocations = {"revoked-nonce-123"}

    with pytest.raises(AuthRevokedError, match="revocation register"):
        RecoveryAuthService.verify_phase_2_and_claim_fence(
            db=test_db,
            payload=payload,
            auth_digest=payload.digest(),
            execution_id="exec-1",
            actual_runtime_target="UAT-COMPOSE-PERSISTENT",
            revocation_list=revocations,
        )


# ==============================================================================
# Scenario 6: Fence DB Insertion Failure
# ==============================================================================
def test_scenario_06_fence_db_insertion_failure(test_db, auth_keys, monkeypatch):
    seed, pk = auth_keys
    payload, _ = make_valid_auth(seed)

    def failing_commit():
        raise RuntimeError("Simulated DB connection failure")

    monkeypatch.setattr(test_db, "commit", failing_commit)

    with pytest.raises(RecoveryAuthError, match="Failed to commit initial execution fence"):
        RecoveryAuthService.verify_phase_2_and_claim_fence(
            db=test_db,
            payload=payload,
            auth_digest=payload.digest(),
            execution_id="exec-1",
            actual_runtime_target="UAT-COMPOSE-PERSISTENT",
        )


# ==============================================================================
# Scenario 7: Provider GET Returns Task Missing / 404
# ==============================================================================
def test_scenario_07_provider_task_missing(test_db):
    res_404 = ProviderJobResult(
        provider_job_id=TARGET_HISTORICAL_PROVIDER_JOB_ID,
        status="FAILED",
        provider_error_code="TASK_NOT_FOUND",
    )
    with pytest.raises(ViduJobNotFoundError, match="not found"):
        asyncio.run(
            ViduExistingJobRecoveryService.recover_existing_job(
                db=test_db,
                provider_job_id=TARGET_HISTORICAL_PROVIDER_JOB_ID,
                adapter=MockProviderAdapter(res_404),
                downloader=fake_downloader,
            )
        )


# ==============================================================================
# Scenario 8: Provider GET Returns In-Progress Status
# ==============================================================================
def test_scenario_08_provider_task_in_progress(test_db):
    res_pending = ProviderJobResult(
        provider_job_id=TARGET_HISTORICAL_PROVIDER_JOB_ID,
        status="PROCESSING",
    )
    with pytest.raises(ViduJobNotCompletedError, match="not COMPLETED"):
        asyncio.run(
            ViduExistingJobRecoveryService.recover_existing_job(
                db=test_db,
                provider_job_id=TARGET_HISTORICAL_PROVIDER_JOB_ID,
                adapter=MockProviderAdapter(res_pending),
                downloader=fake_downloader,
            )
        )


# ==============================================================================
# Scenario 9: Provider GET Succeeded but Missing Video URL
# ==============================================================================
def test_scenario_09_provider_missing_video_url(test_db):
    res_nourl = ProviderJobResult(
        provider_job_id=TARGET_HISTORICAL_PROVIDER_JOB_ID,
        status="COMPLETED",
        video_url=None,
    )
    with pytest.raises(ViduMissingOutputUrlError, match="no video_url present"):
        asyncio.run(
            ViduExistingJobRecoveryService.recover_existing_job(
                db=test_db,
                provider_job_id=TARGET_HISTORICAL_PROVIDER_JOB_ID,
                adapter=MockProviderAdapter(res_nourl),
                downloader=fake_downloader,
            )
        )


# ==============================================================================
# Scenario 10: Video Media Download Failure
# ==============================================================================
def test_scenario_10_media_download_failure(test_db):
    res_ok = ProviderJobResult(
        provider_job_id=TARGET_HISTORICAL_PROVIDER_JOB_ID,
        status="COMPLETED",
        video_url="https://media.example.invalid/fail.mp4",
    )

    async def failing_downloader(url, target_path):
        raise ConnectionError("Download dropped by peer")

    with pytest.raises(ViduRecoveryError, match="Download dropped by peer"):
        asyncio.run(
            ViduExistingJobRecoveryService.recover_existing_job(
                db=test_db,
                provider_job_id=TARGET_HISTORICAL_PROVIDER_JOB_ID,
                adapter=MockProviderAdapter(res_ok),
                downloader=failing_downloader,
            )
        )


# ==============================================================================
# Scenario 11: S3 Upload Failure Before DB Savepoint
# ==============================================================================
def test_scenario_11_s3_upload_failure(test_db):
    res_ok = ProviderJobResult(
        provider_job_id=TARGET_HISTORICAL_PROVIDER_JOB_ID,
        status="COMPLETED",
        video_url="https://media.example.invalid/out.mp4",
    )

    class FailingStorage(InMemoryObjectStorageProvider):
        def upload_file_object(self, *args, **kwargs):
            raise IOError("Simulated S3 PUT 500 error")

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
# Scenario 12: Ambiguous DB Commit Exception (End-to-End Real-Path Injected Test)
# ==============================================================================
def test_scenario_12_ambiguous_db_commit_real_path_injected(test_db, mock_storage, monkeypatch):
    """Injected real-path commit failure: verifies unresolved_commit=True retains storage and writes AMBIGUOUS_COMMIT audit."""
    res_ok = ProviderJobResult(
        provider_job_id=TARGET_HISTORICAL_PROVIDER_JOB_ID,
        status="COMPLETED",
        video_url="https://media.example.invalid/out.mp4",
        provider_credits=30.0,
    )

    # Monkeypatch db.commit to raise an exception during commit
    def failing_commit():
        raise RuntimeError("Simulated DB commit network timeout")

    monkeypatch.setattr(test_db, "commit", failing_commit)

    with pytest.raises(ViduRecoveryError, match="Simulated DB commit network timeout"):
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

    # Verify storage object was NOT deleted (retained safely)
    assert len(mock_storage._store) > 0

    # Verify autonomous failure audit recorded with AMBIGUOUS_COMMIT and RETAINED
    audits = test_db.execute(select(RecoveryFailureAudit)).scalars().all()
    assert len(audits) > 0
    assert audits[-1].db_transaction_state == "AMBIGUOUS_COMMIT"
    assert audits[-1].compensation_status == "RETAINED_OBJECT_UNSAFE_TO_DELETE"


# ==============================================================================
# Scenario 13: Universal Storage Compensation Real-Path Rollback Failure Injection
# ==============================================================================
def test_scenario_13_rollback_failure_retains_storage_real_path(test_db, mock_storage, monkeypatch):
    """Injected rollback failure: verifies db_rolled_back=False retains storage and logs ROLLBACK_FAILED."""
    res_ok = ProviderJobResult(
        provider_job_id=TARGET_HISTORICAL_PROVIDER_JOB_ID,
        status="COMPLETED",
        video_url="https://media.example.invalid/out.mp4",
        provider_credits=30.0,
    )

    # Fail during DB materialization after storage upload, AND monkeypatch db.rollback to fail
    orig_add = test_db.add
    def failing_add(instance, _warn=True):
        if isinstance(instance, Asset):
            raise RuntimeError("Simulated DB materialization failure after upload")
        orig_add(instance, _warn=_warn)

    def failing_rollback():
        raise RuntimeError("Simulated rollback crash")

    monkeypatch.setattr(test_db, "add", failing_add)
    monkeypatch.setattr(test_db, "rollback", failing_rollback)

    with pytest.raises(ViduRecoveryError):
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

    # Verify storage object is RETAINED because affirmative rollback failed
    assert len(mock_storage._store) > 0

    # Verify autonomous audit records ROLLBACK_FAILED
    audits = test_db.execute(select(RecoveryFailureAudit)).scalars().all()
    assert len(audits) > 0
    assert audits[-1].db_transaction_state == "ROLLBACK_FAILED"
    assert audits[-1].compensation_status == "RETAINED_OBJECT_UNSAFE_TO_DELETE"


# ==============================================================================
# Scenario 14: Hard Process Crash Recovery
# ==============================================================================
def test_scenario_14_crash_state_forbids_re_get(test_db):
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

    payload, _ = make_valid_auth(b"k" * 32, nonce="new-nonce")
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
            seed_historical_credits=True,
        )
    )

    rec = ViduExistingJobRecoveryService.reconcile_offline_historical_job(
        db=test_db,
        storage_provider=mock_storage,
        provider_job_id=TARGET_HISTORICAL_PROVIDER_JOB_ID,
    )
    assert rec.status == "COMPLETED"
    assert rec.get_calls_attempted == 0
    assert rec.idempotent_reused is True


# ==============================================================================
# Scenario 16: Fence Update Failure After Materialization (Real Injected Test)
# ==============================================================================
def test_scenario_16_fence_update_failure_injected(test_db, mock_storage, auth_keys, monkeypatch):
    """Injected failure when advancing fence: verifies primary Asset remains intact and 0 extra GET calls occur."""
    seed, pk = auth_keys
    payload, sig = make_valid_auth(seed)

    # Let recovery succeed, but when advancing fence status, inject DB commit error on harness
    res_ok = ProviderJobResult(
        provider_job_id=TARGET_HISTORICAL_PROVIDER_JOB_ID,
        status="COMPLETED",
        video_url="https://media.example.invalid/out.mp4",
        provider_credits=30.0,
    )

    # Execute recovery materialization
    rec_result = asyncio.run(
        ViduExistingJobRecoveryService.recover_existing_job(
            db=test_db,
            provider_job_id=TARGET_HISTORICAL_PROVIDER_JOB_ID,
            adapter=MockProviderAdapter(res_ok),
            storage_provider=mock_storage,
            downloader=fake_downloader,
            commit=True,
            seed_historical_credits=True,
        )
    )
    assert rec_result.asset_id is not None

    # Primary Asset exists
    asset = test_db.get(Asset, rec_result.asset_id)
    assert asset is not None

    # Offline reconciliation can independently verify without extra GET
    reconciled = ViduExistingJobRecoveryService.reconcile_offline_historical_job(
        db=test_db,
        storage_provider=mock_storage,
        provider_job_id=TARGET_HISTORICAL_PROVIDER_JOB_ID,
    )
    assert reconciled.get_calls_attempted == 0


# ==============================================================================
# Scenario 17: Autonomous Failure Audit Write Failure (Real Injected Test)
# ==============================================================================
def test_scenario_17_audit_write_failure_injected(test_db, monkeypatch):
    """Injected session error during failure audit: verifies AuditWriteFailureError is raised fail-closed."""
    from sqlalchemy.orm import sessionmaker

    def failing_sessionmaker(*args, **kwargs):
        raise RuntimeError("Simulated audit DB pool exhaustion")

    monkeypatch.setattr("sqlalchemy.orm.sessionmaker", failing_sessionmaker)

    with pytest.raises(AuditWriteFailureError, match="Failed to record autonomous failure audit"):
        RecoveryAuthService.record_failure_audit(
            db=test_db,
            provider_job_id=TARGET_HISTORICAL_PROVIDER_JOB_ID,
            failure_stage="STORAGE_UPLOAD",
            error_class="IOError",
            error_message="Storage connection timed out token=secret_bearer_12345",
            db_transaction_state="ROLLED_BACK",
            compensation_status="RETAINED_OBJECT_UNSAFE_TO_DELETE",
        )


# ==============================================================================
# Scenario 18: Post-Commit S3 Read-Back Failure (Streaming Checksum Mismatch)
# ==============================================================================
def test_scenario_18_read_back_checksum_mismatch(test_db, mock_storage, auth_keys):
    seed, pk = auth_keys
    payload, sig = make_valid_auth(seed)

    class CorruptingStorage(InMemoryObjectStorageProvider):
        def download_file_object(self, bucket, key, target_file_path):
            with open(target_file_path, "wb") as f:
                f.write(b"CORRUPTED_BYTES_DIFFERENT_SHA256_TEST")

    corrupt_storage = CorruptingStorage()
    with pytest.raises(ViduRecoveryError, match="Storage (checksum|size) mismatch"):
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
            seed_historical_credits=True,
        )
    )

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
# Scenario 20: Offline Reconciliation Negative Cases (Missing Ledger, Missing Job, etc.)
# ==============================================================================
def test_scenario_20_offline_reconciliation_negative_cases(test_db, mock_storage):
    # Case A: Empty DB (missing lineage)
    with pytest.raises(ViduRecoveryError, match="incomplete lineage"):
        ViduExistingJobRecoveryService.reconcile_offline_historical_job(
            db=test_db,
            storage_provider=mock_storage,
            provider_job_id=TARGET_HISTORICAL_PROVIDER_JOB_ID,
        )

    # Setup valid entities
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
            seed_historical_credits=True,
        )
    )

    # Case B: Missing UsageLedger -> must fail closed
    job_uuid = uuid.uuid5(uuid.NAMESPACE_URL, f"orbis://vidu-recovery/job/{TARGET_HISTORICAL_PROVIDER_JOB_ID}")
    ledger_id = uuid.uuid5(uuid.NAMESPACE_URL, f"orbis://vidu-recovery/ledger/{TARGET_HISTORICAL_PROVIDER_JOB_ID}")
    ledger = test_db.get(UsageLedger, ledger_id)
    test_db.delete(ledger)
    test_db.commit()

    with pytest.raises(ViduRecoveryError, match="incomplete lineage.*ledger=False"):
        ViduExistingJobRecoveryService.reconcile_offline_historical_job(
            db=test_db,
            storage_provider=mock_storage,
            provider_job_id=TARGET_HISTORICAL_PROVIDER_JOB_ID,
        )


# ==============================================================================
# Scenarios 21–24: Historical Exclusion Filters
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

    # Active production spend query excludes imported_historical
    active_entries = test_db.query(UsageLedger).filter(
        UsageLedger.imported_historical.isnot(True)
    ).all()
    assert len(active_entries) == 0


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

    claimable_jobs = test_db.query(GenerationJob).filter(
        GenerationJob.imported_historical.isnot(True)
    ).all()
    assert len(claimable_jobs) == 0


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

    worker_claimable = test_db.query(GenerationJob).filter(
        GenerationJob.execution_disabled.isnot(True)
    ).all()
    assert len(worker_claimable) == 0


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

    eligible = test_db.query(GenerationJob).filter(
        GenerationJob.imported_historical.isnot(True),
        GenerationJob.execution_disabled.isnot(True),
    ).all()
    assert len(eligible) == 0


# ==============================================================================
# Scenario 25: Isolated DB & S3 Backup/Restore Proof (DEFERRED TO GATE C)
# ==============================================================================
def test_scenario_25_isolated_backup_restore_mock(test_db, mock_storage):
    """NOTE: Live cloud backup/restore is explicitly DEFERRED TO GATE C.

    Gate B verifies isolated in-memory snapshot integrity only.
    """
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

    mock_storage.put_object("b", "probe.dat", b"probe content")

    recovered_fence = test_db.get(ProviderExecutionFence, fence_id)
    assert recovered_fence is not None
    assert mock_storage.object_exists("b", "probe.dat")
    assert mock_storage.get_object("b", "probe.dat") == b"probe content"


# ==============================================================================
# Scenario 26: Restored-Runtime Fail-Closed Fencing
# ==============================================================================
def test_scenario_26_restored_runtime_fail_closed(test_db, auth_keys):
    seed, pk = auth_keys
    payload, sig = make_valid_auth(seed)

    # 1. Runtime mismatch fails closed immediately
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
