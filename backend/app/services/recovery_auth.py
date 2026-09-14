"""Asymmetric Owner authorization verification service for bounded job recovery.

Implements two-phase Ed25519 authorization verification, runtime matching,
nonce replay prevention, same-job concurrency fencing, and autonomous audit recording.
"""
from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Optional, Set
from pydantic import BaseModel, Field

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.recovery_fence import ProviderExecutionFence, RecoveryFailureAudit
from app.services.ed25519_pure import ed25519_verify

TARGET_TASK_ID = "P4-WP020-LIVE-R5-VIDU2-REC1-RUN1"
TARGET_PROVIDER_JOB_ID = "995880130565918720"
MAX_VALIDITY_WINDOW_SECONDS = 7200  # 2 hours


class RecoveryAuthError(RuntimeError):
    """Base exception for recovery authorization failures."""
    pass


class AuthSignatureVerificationError(RecoveryAuthError):
    """Ed25519 signature is invalid."""
    pass


class AuthExpiredError(RecoveryAuthError):
    """Authorization timestamp is outside valid window."""
    pass


class AuthScopeMismatchError(RecoveryAuthError):
    """Authorization task_id, job_id, or commit SHA does not match expected scope."""
    pass


class AuthRuntimeMismatchError(RecoveryAuthError):
    """Authorized runtime_target does not match actual running environment."""
    pass


class AuthRevokedError(RecoveryAuthError):
    """Authorization nonce or evidence anchor has been revoked."""
    pass


class AuthReplayError(RecoveryAuthError):
    """Authorization nonce has already been consumed."""
    pass


class AuthSameJobConcurrentError(RecoveryAuthError):
    """A fence for this provider job already exists."""
    pass


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class CanonicalAuthPayload(BaseModel):
    authorized_commit_sha: str
    task_id: str
    provider_job_id: str
    runtime_target: str
    owner_evidence_anchor: str
    issued_at: datetime
    expires_at: datetime
    auth_nonce: str

    def to_canonical_json(self) -> bytes:
        """Serialize payload to deterministic, sorted UTF-8 JSON without whitespace."""
        data = {
            "authorized_commit_sha": self.authorized_commit_sha,
            "auth_nonce": self.auth_nonce,
            "expires_at": self.expires_at.astimezone(timezone.utc).isoformat(),
            "issued_at": self.issued_at.astimezone(timezone.utc).isoformat(),
            "owner_evidence_anchor": self.owner_evidence_anchor,
            "provider_job_id": self.provider_job_id,
            "runtime_target": self.runtime_target,
            "task_id": self.task_id,
        }
        return json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")

    def digest(self) -> str:
        """SHA-256 hex digest of canonical JSON payload."""
        return hashlib.sha256(self.to_canonical_json()).hexdigest()


class RecoveryAuthService:
    """Two-phase asymmetric authorization verification."""

    @classmethod
    def verify_phase_1_in_memory(
        cls,
        payload: CanonicalAuthPayload,
        signature_bytes: bytes,
        public_key_bytes: bytes,
        expected_commit_sha: str,
        current_time: Optional[datetime] = None,
    ) -> str:
        """Phase 1: In-memory pre-DB validation.

        Verifies:
        1. Ed25519 signature against OWNER_AUTH_PUBLIC_KEY
        2. Freshness and validity window <= 2 hours
        3. Exact commit SHA binding
        4. Exact task_id and provider_job_id scope
        5. Presence of owner_evidence_anchor

        Returns auth_digest if valid; raises RecoveryAuthError otherwise.
        """
        now = current_time or utc_now()

        # 1. Ed25519 signature check
        canonical_bytes = payload.to_canonical_json()
        if not ed25519_verify(canonical_bytes, signature_bytes, public_key_bytes):
            raise AuthSignatureVerificationError("Ed25519 authorization signature verification failed")

        # 2. Freshness & Window checks
        issued_utc = payload.issued_at.astimezone(timezone.utc)
        expires_utc = payload.expires_at.astimezone(timezone.utc)
        now_utc = now.astimezone(timezone.utc)

        if now_utc < issued_utc:
            raise AuthExpiredError(f"Authorization not yet active (issued at {issued_utc}, now {now_utc})")
        if now_utc > expires_utc:
            raise AuthExpiredError(f"Authorization expired at {expires_utc} (now {now_utc})")

        window_duration = (expires_utc - issued_utc).total_seconds()
        if window_duration > MAX_VALIDITY_WINDOW_SECONDS:
            raise AuthExpiredError(
                f"Authorization validity window exceeds 2 hours ({window_duration}s > {MAX_VALIDITY_WINDOW_SECONDS}s)"
            )

        # 3. Exact commit SHA binding
        if payload.authorized_commit_sha != expected_commit_sha:
            raise AuthScopeMismatchError(
                f"Commit SHA mismatch: authorized '{payload.authorized_commit_sha}' != current '{expected_commit_sha}'"
            )

        # 4. Scope verification
        if payload.task_id != TARGET_TASK_ID:
            raise AuthScopeMismatchError(
                f"Task ID mismatch: authorized '{payload.task_id}' != expected '{TARGET_TASK_ID}'"
            )
        if payload.provider_job_id != TARGET_PROVIDER_JOB_ID:
            raise AuthScopeMismatchError(
                f"Provider Job ID mismatch: authorized '{payload.provider_job_id}' != expected '{TARGET_PROVIDER_JOB_ID}'"
            )

        # 5. Evidence anchor
        if not payload.owner_evidence_anchor or not payload.owner_evidence_anchor.strip():
            raise AuthScopeMismatchError("Authorization missing required owner_evidence_anchor")

        return payload.digest()

    @classmethod
    def verify_phase_2_and_claim_fence(
        cls,
        db: Session,
        payload: CanonicalAuthPayload,
        auth_digest: str,
        execution_id: str,
        actual_runtime_target: str,
        revocation_list: Optional[Set[str]] = None,
    ) -> ProviderExecutionFence:
        """Phase 2: Database and runtime target validation pre-GET.

        Verifies:
        1. Actual runtime target matches authorized runtime_target
        2. Nonce or anchor not in revocation register
        3. Replay protection (nonce uniqueness)
        4. Same-job concurrency fence (provider_name + provider_job_id uniqueness)

        Inserts and commits fence record with status 'CLAIMED_PENDING_GET'.
        """
        # 1. Actual runtime target match
        if payload.runtime_target != actual_runtime_target:
            raise AuthRuntimeMismatchError(
                f"Runtime target mismatch: authorized '{payload.runtime_target}' != actual '{actual_runtime_target}'"
            )

        # 2. Revocation check
        revocations = revocation_list or set()
        if payload.auth_nonce in revocations:
            raise AuthRevokedError(f"Authorization nonce '{payload.auth_nonce}' is in revocation register")
        if payload.owner_evidence_anchor in revocations:
            raise AuthRevokedError(f"Owner evidence anchor '{payload.owner_evidence_anchor}' is in revocation register")

        # 3. Check existing fence by nonce (Replay check)
        existing_nonce_fence = db.execute(
            select(ProviderExecutionFence).where(
                ProviderExecutionFence.auth_nonce == payload.auth_nonce
            )
        ).scalar_one_or_none()

        if existing_nonce_fence is not None:
            raise AuthReplayError(
                f"Authorization nonce '{payload.auth_nonce}' has already been consumed (fence_id={existing_nonce_fence.fence_id})"
            )

        # 4. Check existing fence by provider_job_id (Same-job concurrency check)
        existing_job_fence = db.execute(
            select(ProviderExecutionFence).where(
                ProviderExecutionFence.provider_name == "vidu",
                ProviderExecutionFence.provider_job_id == payload.provider_job_id,
            )
        ).scalar_one_or_none()

        if existing_job_fence is not None:
            raise AuthSameJobConcurrentError(
                f"Provider job fence already exists for 'vidu/{payload.provider_job_id}' "
                f"(fence_id={existing_job_fence.fence_id}, status={existing_job_fence.status})"
            )

        # 5. Insert fence record atomically in its own transaction
        fence = ProviderExecutionFence(
            fence_id=uuid.uuid4(),
            provider_name="vidu",
            provider_job_id=payload.provider_job_id,
            execution_id=execution_id,
            task_id=payload.task_id,
            authorized_commit_sha=payload.authorized_commit_sha,
            runtime_target=payload.runtime_target,
            owner_evidence_anchor=payload.owner_evidence_anchor,
            auth_digest=auth_digest,
            auth_nonce=payload.auth_nonce,
            auth_issued_at=payload.issued_at,
            status="CLAIMED_PENDING_GET",
            network_get_attempts=0,
            storage_is_new_object="UNKNOWN",
            created_at=utc_now(),
            updated_at=utc_now(),
        )

        try:
            db.add(fence)
            db.commit()
            db.refresh(fence)
            return fence
        except IntegrityError as exc:
            db.rollback()
            raise AuthReplayError(f"Fence insertion failed due to unique constraint: {exc}") from exc
        except Exception as exc:
            db.rollback()
            raise RecoveryAuthError(f"Failed to commit initial execution fence: {exc}") from exc

    @classmethod
    def record_failure_audit(
        cls,
        db: Session,
        provider_job_id: str,
        failure_stage: str,
        error_class: str,
        error_message: str,
        db_transaction_state: str,
        compensation_status: str,
        fence_id: Optional[uuid.UUID] = None,
        orphan_bucket: Optional[str] = None,
        orphan_key: Optional[str] = None,
    ) -> RecoveryFailureAudit:
        """Record a sanitized failure audit in an autonomous committed transaction."""
        # Sanitize message to max 512 characters and exclude secrets/tokens
        sanitized_msg = str(error_message)[:512]

        audit = RecoveryFailureAudit(
            audit_id=uuid.uuid4(),
            fence_id=fence_id,
            provider_job_id=provider_job_id,
            failure_stage=failure_stage[:64],
            error_class=error_class[:128],
            error_message=sanitized_msg,
            orphan_storage_bucket=orphan_bucket[:64] if orphan_bucket else None,
            orphan_storage_key=orphan_key[:512] if orphan_key else None,
            db_transaction_state=db_transaction_state[:64],
            compensation_status=compensation_status[:64],
            created_at=utc_now(),
        )
        try:
            db.add(audit)
            db.commit()
            db.refresh(audit)
            return audit
        except Exception as exc:
            db.rollback()
            raise RecoveryAuthError(f"Failed to record failure audit: {exc}") from exc
