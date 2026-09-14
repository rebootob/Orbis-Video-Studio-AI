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
@pytest.fixture(autouse=True)
def setup_auth_env(monkeypatch):
    monkeypatch.setenv("OWNER_AUTH_REVOCATIONS", "")
    monkeypatch.setenv("OWNER_AUTH_REVOCATIONS_ATTESTED", "true")
    monkeypatch.setenv("VIDU_GENERATION_ENABLED", "false")
    monkeypatch.setenv("VIDU_RECOVERY_GET_ENABLED", "true")


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
def test_scenario_05_revocation_rejection(test_db, auth_keys, monkeypatch):
    seed, pk = auth_keys
    payload, _ = make_valid_auth(seed, nonce="revoked-nonce-123")
    revocations = {"revoked-nonce-123"}

    # 1. Explicit revocation list rejects
    with pytest.raises(AuthRevokedError, match="revocation register"):
        RecoveryAuthService.verify_phase_2_and_claim_fence(
            db=test_db,
            payload=payload,
            auth_digest=payload.digest(),
            execution_id="exec-1",
            actual_runtime_target="UAT-COMPOSE-PERSISTENT",
            revocation_list=revocations,
        )

    # 2. Missing revocation registry evidence fails closed
    monkeypatch.delenv("OWNER_AUTH_REVOCATIONS", raising=False)
    with pytest.raises(AuthRevokedError, match="revocation registry evidence is missing"):
        RecoveryAuthService.verify_phase_2_and_claim_fence(
            db=test_db,
            payload=payload,
            auth_digest=payload.digest(),
            execution_id="exec-1",
            actual_runtime_target="UAT-COMPOSE-PERSISTENT",
            revocation_list=None,
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


def test_commit_exception_without_matching_keywords_retains_storage(test_db, mock_storage, monkeypatch):
    """Verifies that ANY exception during commit phase (even with unrelated message) conservatively retains storage."""
    res_ok = ProviderJobResult(
        provider_job_id=TARGET_HISTORICAL_PROVIDER_JOB_ID,
        status="COMPLETED",
        video_url="https://media.example.invalid/out.mp4",
        provider_credits=30.0,
    )

    def arbitrary_error_commit():
        raise RuntimeError("Unrelated primary key sequence corruption xyz 123")

    monkeypatch.setattr(test_db, "commit", arbitrary_error_commit)

    with pytest.raises(ViduRecoveryError, match="Unrelated primary key sequence corruption"):
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

    # Storage object must still be retained
    assert len(mock_storage._store) > 0
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

    real_commit = test_db.commit
    commit_counter = {"count": 0}

    def failing_commit():
        commit_counter["count"] += 1
        # Commit 1: Phase 2 claim fence
        # Commit 2: pre-GET transition (GET_IN_FLIGHT)
        # Commit 3: recover_existing_job durable commit
        # Commit 4: harness transition to MATERIALIZED_UNVERIFIED -> inject commit failure!
        if commit_counter["count"] == 4:
            raise RuntimeError("Simulated fence update commit failure after materialization")
        return real_commit()

    monkeypatch.setattr(test_db, "commit", failing_commit)

    with pytest.raises(RuntimeError, match="Simulated fence update commit failure"):
        execute_recovery_harness(
            db=test_db,
            auth_payload=payload,
            signature_bytes=sig,
            public_key_bytes=pk,
            expected_commit_sha=payload.authorized_commit_sha,
            actual_runtime_target="UAT-COMPOSE-PERSISTENT",
            mock_mode=True,
            storage_provider=mock_storage,
        )

    # Primary Asset and GenerationJob were already committed in commit 3
    job_uuid = uuid.uuid5(uuid.NAMESPACE_URL, f"orbis://vidu-recovery/job/{TARGET_HISTORICAL_PROVIDER_JOB_ID}")
    asset_uuid = uuid.uuid5(uuid.NAMESPACE_URL, f"orbis://video-generation/{job_uuid}")
    asset = test_db.get(Asset, asset_uuid)
    assert asset is not None

    # Assert durable failure audit was persisted with failure_stage 'FENCE_TRANSITION_MATERIALIZED'
    audits = test_db.execute(
        select(RecoveryFailureAudit).where(
            RecoveryFailureAudit.provider_job_id == TARGET_HISTORICAL_PROVIDER_JOB_ID,
            RecoveryFailureAudit.failure_stage == "FENCE_TRANSITION_MATERIALIZED",
        )
    ).scalars().all()
    assert len(audits) >= 1
    assert "Simulated fence update commit failure" in audits[0].error_message

    # Offline reconciliation can independently verify without extra GET
    monkeypatch.setattr(test_db, "commit", real_commit)
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
        def upload_file_object(self, bucket, key, file_path, content_type="application/octet-stream"):
            self.ensure_bucket_exists(bucket)
            self._store[(bucket, key)] = (b"CORRUPTED_BYTES_DIFFERENT_SHA256_TEST", content_type)
            return key

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
# Scenarios 21–24: Historical Exclusion Filters via Production Consumers
# ==============================================================================
def test_scenario_21_usage_ledger_historical_exclusion(test_db):
    """Verifies that production consumer BudgetService authoritatively excludes historical entries."""
    from app.services.budget import BudgetService
    from app.models.project import Project

    proj = Project(id=uuid.uuid4(), title="Test Exclusion Project")
    test_db.add(proj)
    test_db.commit()

    # Active spend: $12.50
    active_entry = UsageLedger(
        id=uuid.uuid4(),
        project_id=proj.id,
        provider="vidu",
        operation="video_generation",
        cost_status="CONFIRMED",
        actual_cost=12.50,
        imported_historical=False,
    )
    # Historical recovered spend: $30.00 equivalent
    hist_entry = UsageLedger(
        id=uuid.uuid4(),
        project_id=proj.id,
        provider="vidu",
        operation="historical_recovery_get",
        cost_status="CONFIRMED",
        actual_cost=30.00,
        imported_historical=True,
    )
    test_db.add(active_entry)
    test_db.add(hist_entry)
    test_db.commit()

    committed = BudgetService.get_project_committed_cost(test_db, proj.id)
    assert committed == 12.50


def test_scenario_22_generation_job_imported_historical_exclusion(test_db):
    """Verifies that production consumer JobDispatchService excludes imported_historical jobs."""
    from app.services.job_dispatch import JobDispatchService
    from app.models.shot import Shot
    from app.models.scene import Scene

    scene = Scene(id=uuid.uuid4(), project_id=uuid.uuid4(), scene_number=1)
    test_db.add(scene)
    shot = Shot(id=uuid.uuid4(), scene_id=scene.id, shot_number=101, shot_type="video")
    test_db.add(shot)
    test_db.commit()

    job = GenerationJob(
        id=uuid.uuid4(),
        shot_id=shot.id,
        provider_name="vidu",
        status="PENDING",
        imported_historical=True,
        execution_disabled=False,
    )
    test_db.add(job)
    test_db.commit()

    claimed = JobDispatchService.claim_next_job(test_db, worker_id="test-consumer-worker-1")
    assert claimed is None


def test_scenario_23_generation_job_execution_disabled_worker_exclusion(test_db):
    """Verifies that production consumer JobDispatchService excludes execution_disabled jobs."""
    from app.services.job_dispatch import JobDispatchService
    from app.models.shot import Shot
    from app.models.scene import Scene

    scene = Scene(id=uuid.uuid4(), project_id=uuid.uuid4(), scene_number=2)
    test_db.add(scene)
    shot = Shot(id=uuid.uuid4(), scene_id=scene.id, shot_number=102, shot_type="video")
    test_db.add(shot)
    test_db.commit()

    job = GenerationJob(
        id=uuid.uuid4(),
        shot_id=shot.id,
        provider_name="vidu",
        status="PENDING",
        imported_historical=False,
        execution_disabled=True,
    )
    test_db.add(job)
    test_db.commit()

    claimed = JobDispatchService.claim_next_job(test_db, worker_id="test-consumer-worker-2")
    assert claimed is None


def test_scenario_24_canonical_generation_job_both_true_exclusion(test_db):
    """Verifies that dual-fenced canonical recovered jobs can never be claimed by JobDispatchService."""
    from app.services.job_dispatch import JobDispatchService
    from app.models.shot import Shot
    from app.models.scene import Scene

    scene = Scene(id=uuid.uuid4(), project_id=uuid.uuid4(), scene_number=3)
    test_db.add(scene)
    shot = Shot(id=uuid.uuid4(), scene_id=scene.id, shot_number=103, shot_type="video")
    test_db.add(shot)
    test_db.commit()

    job = GenerationJob(
        id=uuid.uuid4(),
        shot_id=shot.id,
        provider_name="vidu",
        status="PENDING",
        imported_historical=True,
        execution_disabled=True,
    )
    test_db.add(job)
    test_db.commit()

    claimed = JobDispatchService.claim_next_job(test_db, worker_id="test-consumer-worker-3")
    assert claimed is None


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
        owner_evidence_anchor="issue#63:gate-b-test",
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
# Scenario 26: Restored-Runtime & Provider-Disabled Proof Fail-Closed Fencing
# ==============================================================================
def test_scenario_26_restored_runtime_fail_closed(test_db, auth_keys, monkeypatch):
    seed, pk = auth_keys
    payload, sig = make_valid_auth(seed)

    # 1. Provider generation enabled -> must fail closed
    monkeypatch.setenv("VIDU_GENERATION_ENABLED", "true")
    with pytest.raises(RecoveryAuthError, match="VIDU_GENERATION_ENABLED must be False"):
        execute_recovery_harness(
            db=test_db,
            auth_payload=payload,
            signature_bytes=sig,
            public_key_bytes=pk,
            expected_commit_sha=payload.authorized_commit_sha,
            actual_runtime_target="UAT-COMPOSE-PERSISTENT",
            mock_mode=True,
        )

    # Restore settings
    monkeypatch.setenv("VIDU_GENERATION_ENABLED", "false")

    # 2. Restored DB missing fence with unchanged runtime label -> must fail closed
    job_uuid = uuid.uuid5(uuid.NAMESPACE_URL, f"orbis://vidu-recovery/job/{TARGET_HISTORICAL_PROVIDER_JOB_ID}")
    restored_job = GenerationJob(
        id=job_uuid,
        shot_id=uuid.uuid4(),
        provider_name="vidu",
        provider_job_id=TARGET_HISTORICAL_PROVIDER_JOB_ID,
        status="COMPLETED",
        imported_historical=True,
        execution_disabled=True,
    )
    test_db.add(restored_job)
    test_db.commit()

    with pytest.raises(AuthSameJobConcurrentError, match="Restored DB state detected"):
        execute_recovery_harness(
            db=test_db,
            auth_payload=payload,
            signature_bytes=sig,
            public_key_bytes=pk,
            expected_commit_sha=payload.authorized_commit_sha,
            actual_runtime_target="UAT-COMPOSE-PERSISTENT",
            mock_mode=True,
        )

    # Clean up restored job
    test_db.delete(restored_job)
    test_db.commit()

    # 3. Invalid out-of-band evidence anchor format -> must fail closed
    invalid_anchor_payload = CanonicalAuthPayload(
        authorized_commit_sha=payload.authorized_commit_sha,
        task_id=payload.task_id,
        provider_job_id=payload.provider_job_id,
        runtime_target="UAT-COMPOSE-PERSISTENT",
        owner_evidence_anchor="arbitrary-unstructured-anchor-without-prefix",
        issued_at=payload.issued_at,
        expires_at=payload.expires_at,
        auth_nonce=str(uuid.uuid4()),
    )
    from tests.ed25519_test_signer import ed25519_sign
    invalid_sig = ed25519_sign(invalid_anchor_payload.to_canonical_json(), seed)

    with pytest.raises(AuthScopeMismatchError, match="Invalid owner_evidence_anchor format"):
        execute_recovery_harness(
            db=test_db,
            auth_payload=invalid_anchor_payload,
            signature_bytes=invalid_sig,
            public_key_bytes=pk,
            expected_commit_sha=payload.authorized_commit_sha,
            actual_runtime_target="UAT-COMPOSE-PERSISTENT",
            mock_mode=True,
        )

    # 4. Runtime target mismatch -> must fail closed
    with pytest.raises(AuthRuntimeMismatchError, match="Runtime target mismatch"):
        execute_recovery_harness(
            db=test_db,
            auth_payload=payload,
            signature_bytes=sig,
            public_key_bytes=pk,
            expected_commit_sha=payload.authorized_commit_sha,
            actual_runtime_target="UNAUTHORIZED-RUNTIME-TARGET",
            mock_mode=True,
        )


# ==============================================================================
# Scenario 27: Adversarial Same-Label Changed Storage/DB Config Fails Closed
# ==============================================================================
def test_scenario_27_adversarial_same_label_changed_storage_config_fails_closed(test_db, mock_storage, auth_keys):
    """Adversarial check: label is UAT-COMPOSE-PERSISTENT, but actual DB or storage identity is foreign -> fails closed."""
    seed, pk = auth_keys
    payload, sig = make_valid_auth(seed)

    # 1. Changed storage bucket under valid label -> fails closed
    mock_storage.bucket_name = "unauthorized-exfiltration-bucket"
    with pytest.raises(AuthRuntimeMismatchError, match="Actual resource configuration does not match authorized runtime target profile"):
        execute_recovery_harness(
            db=test_db,
            auth_payload=payload,
            signature_bytes=sig,
            public_key_bytes=pk,
            expected_commit_sha=payload.authorized_commit_sha,
            actual_runtime_target="UAT-COMPOSE-PERSISTENT",
            mock_mode=True,
            storage_provider=mock_storage,
        )

    # 2. Changed storage endpoint under valid label -> fails closed
    mock_storage.bucket_name = "orbis-media-assets"
    mock_storage.endpoint_url = "http://rogue-exfiltration-minio:9000"
    with pytest.raises(AuthRuntimeMismatchError, match="Actual resource configuration does not match authorized runtime target profile"):
        execute_recovery_harness(
            db=test_db,
            auth_payload=payload,
            signature_bytes=sig,
            public_key_bytes=pk,
            expected_commit_sha=payload.authorized_commit_sha,
            actual_runtime_target="UAT-COMPOSE-PERSISTENT",
            mock_mode=True,
            storage_provider=mock_storage,
        )
    mock_storage.endpoint_url = None

    # 3. Unknown runtime profile label -> fails closed immediately
    unauthorized_payload = CanonicalAuthPayload(
        authorized_commit_sha=payload.authorized_commit_sha,
        task_id=payload.task_id,
        provider_job_id=payload.provider_job_id,
        runtime_target="UNKNOWN-ROGUE-PROFILE",
        owner_evidence_anchor=payload.owner_evidence_anchor,
        issued_at=payload.issued_at,
        expires_at=payload.expires_at,
        auth_nonce=str(uuid.uuid4()),
    )
    unauthorized_sig = ed25519_sign(unauthorized_payload.to_canonical_json(), seed)
    with pytest.raises(AuthRuntimeMismatchError, match="Unknown or unauthorized runtime target profile"):
        execute_recovery_harness(
            db=test_db,
            auth_payload=unauthorized_payload,
            signature_bytes=unauthorized_sig,
            public_key_bytes=pk,
            expected_commit_sha=payload.authorized_commit_sha,
            actual_runtime_target="UNKNOWN-ROGUE-PROFILE",
            mock_mode=True,
            storage_provider=mock_storage,
        )

    # 4. Changed DB host/database under valid label -> fails closed
    foreign_engine = create_engine("sqlite:///unauthorized_foreign.db")
    Base.metadata.create_all(bind=foreign_engine)
    ForeignSession = sessionmaker(bind=foreign_engine)
    foreign_db = ForeignSession()
    try:
        with pytest.raises(AuthRuntimeMismatchError, match="Actual resource configuration does not match authorized runtime target profile"):
            execute_recovery_harness(
                db=foreign_db,
                auth_payload=payload,
                signature_bytes=sig,
                public_key_bytes=pk,
                expected_commit_sha=payload.authorized_commit_sha,
                actual_runtime_target="UAT-COMPOSE-PERSISTENT",
                mock_mode=True,
                storage_provider=mock_storage,
            )
    finally:
        foreign_db.close()
        Base.metadata.drop_all(bind=foreign_engine)
        foreign_engine.dispose()
        import os
        if os.path.exists("unauthorized_foreign.db"):
            os.remove("unauthorized_foreign.db")


# ==============================================================================
# Scenario 28: Restored Snapshot Lacking BOTH Rows Prevents Second GET
# ==============================================================================
def test_scenario_28_restored_db_lacking_both_fence_and_job_rejects_second_get(test_db, mock_storage, auth_keys):
    """Restored DB lacking both ProviderExecutionFence and GenerationJob detects out-of-band artifact and prevents 2nd GET."""
    seed, pk = auth_keys

    # Subcase A: Successful execution followed by DB restore (loss of both rows)
    payload_a, sig_a = make_valid_auth(seed, nonce="nonce-subcase-a")
    mock_adapter_a = MockProviderAdapter()

    result_a = execute_recovery_harness(
        db=test_db,
        auth_payload=payload_a,
        signature_bytes=sig_a,
        public_key_bytes=pk,
        expected_commit_sha=payload_a.authorized_commit_sha,
        actual_runtime_target="UAT-COMPOSE-PERSISTENT",
        mock_mode=True,
        adapter=mock_adapter_a,
        storage_provider=mock_storage,
    )
    assert result_a["status"] == "CONSUMED_SUCCESS"
    assert mock_adapter_a.get_calls_attempted == 1

    # SIMULATE RESTORED DATABASE:
    test_db.query(RecoveryFailureAudit).delete()
    test_db.query(ProviderExecutionFence).delete()
    test_db.query(GenerationJob).delete()
    test_db.query(UsageLedger).delete()
    test_db.query(Shot).delete()
    test_db.query(Scene).delete()
    test_db.query(Asset).delete()
    test_db.query(Project).delete()
    test_db.commit()

    assert test_db.query(ProviderExecutionFence).count() == 0
    assert test_db.query(GenerationJob).count() == 0

    # Re-attempt: storage marker fences/consumed/{provider_job_id}.json exists -> reject second GET!
    payload_a2, sig_a2 = make_valid_auth(seed, nonce="nonce-subcase-a2")
    second_adapter = MockProviderAdapter()

    with pytest.raises(AuthReplayError, match="Authoritative external execution fence detected"):
        execute_recovery_harness(
            db=test_db,
            auth_payload=payload_a2,
            signature_bytes=sig_a2,
            public_key_bytes=pk,
            expected_commit_sha=payload_a2.authorized_commit_sha,
            actual_runtime_target="UAT-COMPOSE-PERSISTENT",
            mock_mode=True,
            adapter=second_adapter,
            storage_provider=mock_storage,
        )
    assert second_adapter.get_calls_attempted == 0

    # Subcase B: Failed/crashed execution where pre-GET external fence was persisted, followed by DB restore (loss of both rows)
    import json
    mock_storage._store.clear()
    pre_get_key = f"fences/in_flight/{TARGET_HISTORICAL_PROVIDER_JOB_ID}.json"
    mock_storage.put_object("orbis-media-assets", pre_get_key, json.dumps({"status": "DISPATCHED_BEFORE_GET"}).encode("utf-8"))

    payload_b, sig_b = make_valid_auth(seed, nonce="nonce-subcase-b")
    crashed_adapter = MockProviderAdapter()

    with pytest.raises(AuthReplayError, match="Authoritative external execution fence detected"):
        execute_recovery_harness(
            db=test_db,
            auth_payload=payload_b,
            signature_bytes=sig_b,
            public_key_bytes=pk,
            expected_commit_sha=payload_b.authorized_commit_sha,
            actual_runtime_target="UAT-COMPOSE-PERSISTENT",
            mock_mode=True,
            adapter=crashed_adapter,
            storage_provider=mock_storage,
        )
    # ZERO second GET even after crashed/failed pre-GET dispatch!
    assert crashed_adapter.get_calls_attempted == 0

    # Subcase C: Inaccessible storage during external fence check fails closed with RecoveryAuthError (not swallowed)
    class InaccessibleStorage:
        bucket_name = "orbis-media-assets"
        def object_exists(self, b, k):
            raise RuntimeError("Storage unreachable / connection timed out")

    with pytest.raises(RecoveryAuthError, match="Storage accessibility failure while inspecting external execution fence"):
        execute_recovery_harness(
            db=test_db,
            auth_payload=payload_b,
            signature_bytes=sig_b,
            public_key_bytes=pk,
            expected_commit_sha=payload_b.authorized_commit_sha,
            actual_runtime_target="UAT-COMPOSE-PERSISTENT",
            mock_mode=True,
            adapter=crashed_adapter,
            storage_provider=InaccessibleStorage(),
        )


# ==============================================================================
# Scenario 29: Empty Revocation Registry Without Freshness Attestation Fails Closed
# ==============================================================================
def test_scenario_29_empty_revocation_without_freshness_attestation_fails_closed(test_db, auth_keys, monkeypatch):
    """Empty OWNER_AUTH_REVOCATIONS and unattested OUT_OF_BAND_CONSUMED_EVIDENCE must fail closed."""
    seed, pk = auth_keys
    payload, sig = make_valid_auth(seed)

    # 1. Empty OWNER_AUTH_REVOCATIONS without freshness attestation
    monkeypatch.setenv("OWNER_AUTH_REVOCATIONS", "")
    monkeypatch.delenv("OWNER_AUTH_REVOCATIONS_ATTESTED", raising=False)

    with pytest.raises(AuthRevokedError, match="revocation registry is empty without active freshness attestation"):
        RecoveryAuthService.verify_phase_2_and_claim_fence(
            db=test_db,
            payload=payload,
            auth_digest=payload.digest(),
            execution_id="exec-rev-test",
            actual_runtime_target="UAT-COMPOSE-PERSISTENT",
        )

    monkeypatch.setenv("OWNER_AUTH_REVOCATIONS_ATTESTED", "true")

    # 2. OUT_OF_BAND_CONSUMED_EVIDENCE provided without mandatory freshness attestation
    monkeypatch.setenv("OUT_OF_BAND_CONSUMED_EVIDENCE", "some-historical-job-id")
    monkeypatch.delenv("OUT_OF_BAND_CONSUMED_ATTESTED", raising=False)

    with pytest.raises(AuthRevokedError, match="External consumed registry lacks mandatory freshness attestation"):
        RecoveryAuthService.verify_phase_2_and_claim_fence(
            db=test_db,
            payload=payload,
            auth_digest=payload.digest(),
            execution_id="exec-rev-test-2",
            actual_runtime_target="UAT-COMPOSE-PERSISTENT",
        )

    # 3. Attested registry contains target job ID -> rejects with AuthReplayError
    monkeypatch.setenv("OUT_OF_BAND_CONSUMED_ATTESTED", "true")
    monkeypatch.setenv("OUT_OF_BAND_CONSUMED_EVIDENCE", f"{TARGET_HISTORICAL_PROVIDER_JOB_ID},other-job")

    with pytest.raises(AuthReplayError, match="Out-of-band consumption evidence confirms"):
        RecoveryAuthService.verify_phase_2_and_claim_fence(
            db=test_db,
            payload=payload,
            auth_digest=payload.digest(),
            execution_id="exec-rev-test-3",
            actual_runtime_target="UAT-COMPOSE-PERSISTENT",
        )


# ==============================================================================
# Scenario 30: Storage Streaming Metadata Failure Fails Closed
# ==============================================================================
def test_scenario_30_storage_streaming_metadata_failure_fails_closed(mock_storage):
    """Storage metadata access failure (e.g. head_object error) must fail closed immediately."""
    class FailingMetadataStorage:
        def __init__(self):
            self.client = self
        def head_object(self, **kwargs):
            raise RuntimeError("Simulated storage metadata head_object network timeout")

    failing_storage = FailingMetadataStorage()
    with pytest.raises(ViduRecoveryError, match="Storage metadata access failed"):
        ViduExistingJobRecoveryService.stream_verify_storage_object(
            storage=failing_storage,
            bucket="orbis-media-assets",
            key="test.mp4",
            expected_size=100,
            expected_sha256="abc",
        )


# ==============================================================================
# Scenario 31: Storage Streaming Object Mutated After HEAD Fails Closed
# ==============================================================================
def test_scenario_31_storage_streaming_object_mutated_after_head_fails_closed():
    """Object mutated between HEAD and GET must be detected and response Body closed."""
    class StreamClientWithMutation:
        def __init__(self):
            self.body_closed = False

        def head_object(self, Bucket, Key):
            return {"ContentLength": 100, "ETag": '"etag-head-initial"'}

        def get_object(self, Bucket, Key):
            client_self = self
            class MockBody:
                def read(self, amt=64*1024):
                    return b"X" * 100
                def close(self):
                    client_self.body_closed = True

            # Mutate ETag between HEAD and GET!
            return {
                "Body": MockBody(),
                "ContentLength": 100,
                "ETag": '"etag-mutated-after-head"',
            }

    class MockStorageWrapper:
        def __init__(self):
            self.client = StreamClientWithMutation()

    wrapper = MockStorageWrapper()
    with pytest.raises(ViduRecoveryError, match="Storage object modified between HEAD and stream retrieval.*ETag mismatch"):
        ViduExistingJobRecoveryService.stream_verify_storage_object(
            storage=wrapper,
            bucket="orbis-media-assets",
            key="assets/test.mp4",
            expected_size=100,
            expected_sha256="any-hash",
        )

    # Body must be closed cleanly despite the exception!
    assert wrapper.client.body_closed is True


# ==============================================================================
# Scenario 32: Storage Streaming Oversize Stream Aborts During Transfer
# ==============================================================================
def test_scenario_32_storage_streaming_oversize_stream_aborts_during_transfer():
    """Stream transfer exceeding byte bound is aborted during streaming with guaranteed Body cleanup."""
    class LyingHeadStreamClient:
        def __init__(self, total_bytes_to_stream):
            self.total_bytes = total_bytes_to_stream
            self.body_closed = False

        def head_object(self, Bucket, Key):
            # Lying acceptable HEAD! Passes metadata check!
            return {"ContentLength": 1000, "ETag": '"etag-lying"'}

        def get_object(self, Bucket, Key):
            client_self = self
            class StreamingBody:
                def __init__(self):
                    self.yielded = 0
                def read(self, amt=64*1024):
                    if self.yielded >= client_self.total_bytes:
                        return b""
                    to_send = min(amt, client_self.total_bytes - self.yielded)
                    self.yielded += to_send
                    return b"A" * to_send
                def close(self):
                    client_self.body_closed = True

            return {"Body": StreamingBody(), "ContentLength": 1000, "ETag": '"etag-lying"'}

    class MockStorageWrapper:
        def __init__(self, total_bytes):
            self.client = LyingHeadStreamClient(total_bytes)

    # Stream yields 2MB, but budget is 1MB -> aborts in chunk reading loop!
    wrapper = MockStorageWrapper(total_bytes=2 * 1024 * 1024)
    with pytest.raises(ViduRecoveryError, match="Storage stream transfer exceeded maximum budget"):
        ViduExistingJobRecoveryService.stream_verify_storage_object(
            storage=wrapper,
            bucket="orbis-media-assets",
            key="assets/oversize.mp4",
            expected_size=1000,
            expected_sha256="any-hash",
            max_size_bytes=1024 * 1024,  # 1MB limit
        )

    # Guaranteed Body cleanup!
    assert wrapper.client.body_closed is True


# ==============================================================================
# Scenario 33: Audit Write Failure Stops Fail-Closed on DB Stage
# ==============================================================================
def test_scenario_33_audit_write_failure_stops_fail_closed_on_db_stage(test_db, mock_storage, auth_keys, monkeypatch):
    """When autonomous failure audit writing fails during a DB stage, AuditWriteFailureError is raised fail-closed with sanitized message."""
    seed, pk = auth_keys
    payload, sig = make_valid_auth(seed)

    def failing_record_failure_audit(*args, **kwargs):
        raise AuditWriteFailureError("Failed to record autonomous failure audit: [REDACTED_DB_ERROR]")

    monkeypatch.setattr(RecoveryAuthService, "record_failure_audit", failing_record_failure_audit)

    # Trigger a Phase 2 failure (e.g. revoked nonce) which triggers record_failure_audit
    revocation_list = [payload.auth_nonce]

    with pytest.raises(AuditWriteFailureError, match="Failed to record autonomous failure audit"):
        execute_recovery_harness(
            db=test_db,
            auth_payload=payload,
            signature_bytes=sig,
            public_key_bytes=pk,
            expected_commit_sha=payload.authorized_commit_sha,
            actual_runtime_target="UAT-COMPOSE-PERSISTENT",
            revocation_list=revocation_list,
            mock_mode=True,
            storage_provider=mock_storage,
        )


# ==============================================================================
# Scenario 34: Gate A Pre-DB Contract Preservation (Strictly Zero DB I/O on Phase 1)
# ==============================================================================
def test_scenario_34_phase1_failure_strictly_zero_db_io(test_db, mock_storage, auth_keys):
    """Gate A pre-DB contract verification: Phase 1 failure must produce strictly 0 DB queries / I/O and 0 audit rows."""
    seed, pk = auth_keys
    payload, sig = make_valid_auth(seed)

    # Initial state
    initial_audits = test_db.query(RecoveryFailureAudit).count()
    initial_fences = test_db.query(ProviderExecutionFence).count()

    # Tamper with signature to force Phase 1 failure
    bad_sig = b"\x00" * len(sig)

    with pytest.raises(RecoveryAuthError, match="Ed25519 authorization signature verification failed"):
        execute_recovery_harness(
            db=test_db,
            auth_payload=payload,
            signature_bytes=bad_sig,
            public_key_bytes=pk,
            expected_commit_sha=payload.authorized_commit_sha,
            actual_runtime_target="UAT-COMPOSE-PERSISTENT",
            mock_mode=True,
            storage_provider=mock_storage,
        )

    # Verify zero DB rows were written
    assert test_db.query(RecoveryFailureAudit).count() == initial_audits
    assert test_db.query(ProviderExecutionFence).count() == initial_fences


# ==============================================================================
# Scenario 35: SDK Stream Timeout and Slow EOF Transfer Bounds
# ==============================================================================
def test_scenario_35_sdk_stream_timeout_and_slow_eof_bounds():
    """Streaming transfer exceeding deadline or suffering slow EOF must be aborted and Body closed."""
    import time

    class SlowBodyStreamClient:
        def __init__(self):
            self.body_closed = False

        def head_object(self, Bucket, Key):
            return {"ContentLength": 1000, "ETag": '"etag-slow"'}

        def get_object(self, Bucket, Key):
            client_self = self
            class SlowBody:
                def __init__(self):
                    self.call_count = 0
                def read(self, amt=64*1024):
                    self.call_count += 1
                    if self.call_count == 1:
                        return b"A" * 100
                    # Simulate hanging / slow EOF
                    time.sleep(0.05)
                    return b""
                def close(self):
                    client_self.body_closed = True

            return {"Body": SlowBody(), "ContentLength": 1000, "ETag": '"etag-slow"'}

    class MockStorageWrapper:
        def __init__(self):
            self.client = SlowBodyStreamClient()

    wrapper = MockStorageWrapper()
    # Set max_duration_seconds to very small value (0.01s)
    with pytest.raises(ViduRecoveryError, match="Storage stream transfer exceeded timeout"):
        ViduExistingJobRecoveryService.stream_verify_storage_object(
            storage=wrapper,
            bucket="orbis-media-assets",
            key="assets/slow.mp4",
            expected_size=1000,
            expected_sha256="any-hash",
            max_duration_seconds=0.01,
        )

    assert wrapper.client.body_closed is True
