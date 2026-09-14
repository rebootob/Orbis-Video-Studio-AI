"""Single-purpose bounded CLI harness for historical Vidu job recovery.

Target: strictly bounded to TARGET_HISTORICAL_PROVIDER_JOB_ID ("995880130565918720").
Zero public API routes. Zero generic agent integration.
Enforces two-phase Ed25519 authorization, atomic one-shot state machine,
durable fence tracking, universal storage compensation, and read-back verification.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import logging
import os
import sys
import uuid
from datetime import datetime, timezone
from typing import Optional, Set

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.asset import Asset
from app.models.generation_job import GenerationJob
from app.models.recovery_fence import ProviderExecutionFence
from app.providers.base import IVideoGenerationProviderAdapter, ProviderJobResult
from app.services.recovery_auth import (
    CanonicalAuthPayload,
    RecoveryAuthError,
    RecoveryAuthService,
    TARGET_PROVIDER_JOB_ID,
    TARGET_TASK_ID,
)
from app.services.storage import ObjectStorageProvider, get_storage_provider
from app.services.vidu_recovery import (
    TARGET_HISTORICAL_PROVIDER_JOB_ID,
    ViduConflictingLineageError,
    ViduExistingJobRecoveryService,
    ViduRecoveryError,
    ViduRecoveryResult,
    ViduUnauthorizedJobError,
)

logger = logging.getLogger("vidu_recovery_harness")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class MockProviderAdapter(IVideoGenerationProviderAdapter):
    """Safe mock adapter for tests and dry-runs; zero outbound network calls."""

    def __init__(self, result: Optional[ProviderJobResult] = None):
        self._result = result or ProviderJobResult(
            provider_job_id=TARGET_HISTORICAL_PROVIDER_JOB_ID,
            status="COMPLETED",
            video_url="https://media.example.invalid/historical_mock_vidu.mp4",
            provider_credits=None,
        )

    @property
    def provider_id(self) -> str:
        return "vidu"

    async def submit_generation_job(self, *args, **kwargs):
        raise RuntimeError("POST / submit_generation_job is strictly forbidden in recovery harness")

    async def check_job_status(self, provider_job_id: str) -> ProviderJobResult:
        if provider_job_id != TARGET_HISTORICAL_PROVIDER_JOB_ID:
            raise ViduUnauthorizedJobError(f"Unauthorized provider job ID: {provider_job_id}")
        return self._result

    async def cancel_job(self, provider_job_id: str) -> bool:
        return True

    def validate_config(self, config: dict) -> bool:
        return True


def execute_recovery_harness(
    *,
    db: Session,
    auth_payload: Optional[CanonicalAuthPayload] = None,
    signature_bytes: Optional[bytes] = None,
    public_key_bytes: Optional[bytes] = None,
    expected_commit_sha: Optional[str] = None,
    actual_runtime_target: str = "UAT-COMPOSE-PERSISTENT",
    execution_id: Optional[str] = None,
    adapter: Optional[IVideoGenerationProviderAdapter] = None,
    storage_provider: Optional[ObjectStorageProvider] = None,
    revocation_list: Optional[Set[str]] = None,
    offline_reconcile: bool = False,
    mock_mode: bool = False,
    auto_compensate_storage: bool = True,
    current_time: Optional[datetime] = None,
) -> dict:
    """Execute the bounded recovery harness through strict gate phases.

    Returns dict with execution summary and status.
    """
    exec_id = execution_id or f"rec1-exec-{uuid.uuid4().hex[:12]}"
    now = current_time or utc_now()

    # 1. Bounded job ID validation
    ViduExistingJobRecoveryService.validate_authorized_job_id(TARGET_HISTORICAL_PROVIDER_JOB_ID)

    # 2. Offline Reconciliation Path (Zero provider GET/POST)
    if offline_reconcile:
        logger.info("Executing dedicated offline reconciliation (0 provider GET/POST)")
        rec_result = ViduExistingJobRecoveryService.reconcile_offline_historical_job(
            db=db,
            storage_provider=storage_provider,
            provider_job_id=TARGET_HISTORICAL_PROVIDER_JOB_ID,
        )
        return {
            "status": "OFFLINE_RECONCILED",
            "provider_job_id": TARGET_HISTORICAL_PROVIDER_JOB_ID,
            "get_calls_attempted": 0,
            "posts_attempted": 0,
            "idempotent_reused": True,
            "asset_id": str(rec_result.asset_id),
            "generation_job_id": str(rec_result.generation_job_id),
            "storage_bucket": rec_result.storage_bucket,
            "storage_key": rec_result.storage_key,
            "checksum_sha256": rec_result.checksum_sha256,
        }

    # 3. Phase 1: Local In-Memory Authorization Validation (Pre-DB)
    if not auth_payload or not signature_bytes or not public_key_bytes or not expected_commit_sha:
        raise RecoveryAuthError("Phase 1 verification requires auth_payload, signature, public_key, and expected_commit_sha")

    auth_digest = RecoveryAuthService.verify_phase_1_in_memory(
        payload=auth_payload,
        signature_bytes=signature_bytes,
        public_key_bytes=public_key_bytes,
        expected_commit_sha=expected_commit_sha,
        current_time=now,
    )
    logger.info("Phase 1 authorization verified successfully (digest=%s)", auth_digest)

    # 4. Phase 2: Database & Runtime Target Validation pre-GET
    fence = RecoveryAuthService.verify_phase_2_and_claim_fence(
        db=db,
        payload=auth_payload,
        auth_digest=auth_digest,
        execution_id=exec_id,
        actual_runtime_target=actual_runtime_target,
        revocation_list=revocation_list,
    )
    logger.info("Phase 2 fence claimed successfully (fence_id=%s, status=%s)", fence.fence_id, fence.status)

    # 5. Pre-GET Atomic State Transition: GET_IN_FLIGHT
    from app.core.config import settings
    storage = storage_provider or get_storage_provider()
    bucket_name = getattr(storage, "bucket_name", None) or getattr(settings, "OBJECT_STORAGE_BUCKET", "orbis-media-assets")
    job_uuid = uuid.uuid5(uuid.NAMESPACE_URL, f"orbis://vidu-recovery/job/{TARGET_HISTORICAL_PROVIDER_JOB_ID}")
    asset_uuid = uuid.uuid5(uuid.NAMESPACE_URL, f"orbis://video-generation/{job_uuid}")
    project_uuid = uuid.uuid5(uuid.NAMESPACE_URL, f"orbis://vidu-recovery/project/{TARGET_HISTORICAL_PROVIDER_JOB_ID}")

    fence.status = "GET_IN_FLIGHT"
    fence.network_get_attempts = 1
    fence.storage_intent_bucket = bucket_name
    fence.storage_intent_key = f"assets/video/{project_uuid}/{asset_uuid}.mp4"
    fence.target_asset_id = asset_uuid
    fence.target_job_id = job_uuid
    fence.target_project_id = project_uuid
    fence.updated_at = utc_now()
    db.commit()
    db.refresh(fence)

    # 6. Execute Recovery
    chosen_adapter = adapter
    downloader_to_use = None
    if mock_mode:
        if chosen_adapter is None:
            chosen_adapter = MockProviderAdapter()

        async def _mock_dl(url: str, target_file_path: str):
            data = b"RECOVERED_HISTORICAL_VIDU_VIDEO_BYTES_995880130565918720"
            with open(target_file_path, "wb") as f:
                f.write(data)
            return "video/mp4", len(data), hashlib.sha256(data).hexdigest()

        downloader_to_use = _mock_dl

    recovery_result: Optional[ViduRecoveryResult] = None
    try:
        recovery_result = asyncio.run(
            ViduExistingJobRecoveryService.recover_existing_job(
                db=db,
                provider_job_id=TARGET_HISTORICAL_PROVIDER_JOB_ID,
                adapter=chosen_adapter,
                storage_provider=storage,
                downloader=downloader_to_use,
                commit=True,
                auto_compensate_storage=auto_compensate_storage,
                fence_id=fence.fence_id,
                seed_historical_credits=True,
            )
        )
        # Advance fence to MATERIALIZED_UNVERIFIED
        fence.status = "MATERIALIZED_UNVERIFIED"
        fence.storage_is_new_object = "FALSE" if recovery_result.idempotent_reused else "TRUE"
        fence.storage_intent_sha256 = recovery_result.checksum_sha256
        fence.storage_intent_bytes = recovery_result.file_size_bytes
        fence.updated_at = utc_now()
        db.commit()
        db.refresh(fence)
    except Exception as exc:
        fence.status = "CONSUMED_TERMINAL_FAILURE"
        fence.updated_at = utc_now()
        try:
            db.commit()
        except Exception:
            db.rollback()
        raise

    # 7. Post-Materialization Read-Back Verification
    logger.info("Executing post-materialization read-back verification")
    db_asset = db.get(Asset, asset_uuid)
    db_job = db.get(GenerationJob, job_uuid)
    if not db_asset or not db_job:
        fence.status = "CONSUMED_TERMINAL_FAILURE"
        db.commit()
        raise ViduRecoveryError("Read-back verification failed: DB Asset or GenerationJob missing")

    if not storage.object_exists(db_asset.storage_bucket, db_asset.storage_key):
        fence.status = "CONSUMED_TERMINAL_FAILURE"
        db.commit()
        raise ViduRecoveryError("Read-back verification failed: Storage object missing")

    stored_bytes = storage.get_object(db_asset.storage_bucket, db_asset.storage_key)
    if len(stored_bytes) != db_asset.file_size_bytes:
        fence.status = "CONSUMED_TERMINAL_FAILURE"
        db.commit()
        raise ViduRecoveryError("Read-back verification failed: Storage byte length mismatch")

    stored_sha256 = hashlib.sha256(stored_bytes).hexdigest()
    if stored_sha256 != db_asset.checksum_sha256:
        fence.status = "CONSUMED_TERMINAL_FAILURE"
        db.commit()
        raise ViduRecoveryError("Read-back verification failed: Storage checksum mismatch")

    # 8. All verifications passed: CONSUMED_SUCCESS
    fence.status = "CONSUMED_SUCCESS"
    fence.updated_at = utc_now()
    db.commit()
    db.refresh(fence)
    logger.info("Recovery completed successfully with fence state CONSUMED_SUCCESS")

    return {
        "status": "CONSUMED_SUCCESS",
        "fence_id": str(fence.fence_id),
        "provider_job_id": TARGET_HISTORICAL_PROVIDER_JOB_ID,
        "get_calls_attempted": 1,
        "posts_attempted": 0,
        "asset_id": str(recovery_result.asset_id),
        "generation_job_id": str(recovery_result.generation_job_id),
        "checksum_sha256": recovery_result.checksum_sha256,
        "provider_credits_reported": recovery_result.provider_credits_reported,
        "idempotent_reused": recovery_result.idempotent_reused,
    }


def main():
    parser = argparse.ArgumentParser(description="Bounded Vidu Recovery Harness CLI")
    parser.add_argument("--auth-payload", help="JSON string or path to auth payload file")
    parser.add_argument("--signature", help="Hex encoded Ed25519 signature")
    parser.add_argument("--public-key", help="Hex encoded Ed25519 public key")
    parser.add_argument("--expected-commit", help="Authorized commit SHA")
    parser.add_argument("--runtime-target", default="UAT-COMPOSE-PERSISTENT", help="Runtime target identifier")
    parser.add_argument("--offline-reconcile", action="store_true", help="Run dedicated offline reconciliation")
    parser.add_argument("--mock", action="store_true", help="Run with mock provider (no outbound network)")

    args = parser.parse_args()

    db: Session = SessionLocal()
    try:
        if args.offline_reconcile:
            result = execute_recovery_harness(
                db=db,
                offline_reconcile=True,
            )
            print(json.dumps(result, indent=2))
            sys.exit(0)

        if not args.auth_payload or not args.signature:
            print("Error: --auth-payload and --signature are required for live/mock recovery runs", file=sys.stderr)
            sys.exit(1)

        payload_str = args.auth_payload
        if os.path.exists(payload_str):
            with open(payload_str, "r", encoding="utf-8") as f:
                payload_str = f.read()

        payload_dict = json.loads(payload_str)
        payload = CanonicalAuthPayload(**payload_dict)

        sig_bytes = bytes.fromhex(args.signature)
        pk_hex = args.public_key or os.environ.get("OWNER_AUTH_PUBLIC_KEY", "")
        if not pk_hex:
            print("Error: --public-key or OWNER_AUTH_PUBLIC_KEY environment variable required", file=sys.stderr)
            sys.exit(1)
        pk_bytes = bytes.fromhex(pk_hex)

        result = execute_recovery_harness(
            db=db,
            auth_payload=payload,
            signature_bytes=sig_bytes,
            public_key_bytes=pk_bytes,
            expected_commit_sha=args.expected_commit or payload.authorized_commit_sha,
            actual_runtime_target=args.runtime_target,
            mock_mode=args.mock,
        )
        print(json.dumps(result, indent=2))
        sys.exit(0)
    except Exception as exc:
        print(f"Harness execution aborted: {exc}", file=sys.stderr)
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
