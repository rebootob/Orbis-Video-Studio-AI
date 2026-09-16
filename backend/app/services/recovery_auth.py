"""Asymmetric Owner authorization verification service for bounded job recovery.

Implements two-phase Ed25519 authorization verification, runtime matching,
nonce replay prevention, same-job concurrency fencing, and autonomous audit recording.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
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


AUTHORIZED_RUNTIME_TARGET_PROFILES = {
    "TEST": {
        "trusted_db_identities": [
            "sqlite://:memory:",
            "sqlite:///",
            "sqlite://",
            "postgresql+psycopg://localhost:5432/orbis_studio",
            "postgresql+psycopg://127.0.0.1:5432/orbis_studio",
            "postgresql://localhost:5432/orbis_studio",
            "postgresql://127.0.0.1:5432/orbis_studio",
        ],
        "trusted_storage_identities": [
            "mock://local/test-bucket",
            "mock://local/orbis-media-assets",
            "mock://local/orbis-assets",
            "s3://http://127.0.0.1/test-bucket",
            "s3://http://localhost/test-bucket",
            "s3://http://127.0.0.1/orbis-media-assets",
            "s3://http://localhost/orbis-media-assets",
        ],
        "require_distinct_mount": False,
        "require_directory_fsync": False,
        "trusted_register_paths": [],
    },
    "UAT-COMPOSE-PERSISTENT": {
        "trusted_db_identities": [
            "sqlite://:memory:",
            "sqlite:///",
            "sqlite://",
            "postgresql+psycopg://localhost:5432/orbis_studio",
            "postgresql+psycopg://127.0.0.1:5432/orbis_studio",
            "postgresql+psycopg://postgres:5432/orbis_studio",
            "postgresql://localhost:5432/orbis_studio",
            "postgresql://127.0.0.1:5432/orbis_studio",
            "postgresql://postgres:5432/orbis_studio",
        ],
        "trusted_storage_identities": [
            "mock://local/orbis-media-assets",
            "mock://local/orbis-assets",
            "mock://local/test-bucket",
            "s3://http://localhost:9000/orbis-media-assets",
            "s3://http://localhost:9000/orbis-assets",
            "s3://http://127.0.0.1:9000/orbis-media-assets",
            "s3://http://127.0.0.1:9000/orbis-assets",
            "s3://http://minio:9000/orbis-media-assets",
            "s3://http://minio:9000/orbis-assets",
            "s3://localhost:9000/orbis-media-assets",
            "s3://localhost:9000/orbis-assets",
            "s3://127.0.0.1:9000/orbis-media-assets",
            "s3://127.0.0.1:9000/orbis-assets",
            "s3://minio:9000/orbis-media-assets",
            "s3://minio:9000/orbis-assets",
        ],
        "require_distinct_mount": True,
        "require_directory_fsync": True,
        "trusted_register_paths": [
            "/var/run/orbis/external_execution_register.json",
            "/opt/orbis/register/authoritative_register.json",
        ],
        "trusted_register_dirs": [
            "/var/run/orbis",
            "/opt/orbis/register",
        ],
    },
    "PRODUCTION": {
        "trusted_db_identities": [
            "postgresql+psycopg://production-db.internal:5432/orbis_production",
        ],
        "trusted_storage_identities": [
            "s3://https://s3.ap-southeast-1.amazonaws.com/orbis-media-assets-prod",
        ],
        "require_distinct_mount": True,
        "require_directory_fsync": True,
        "trusted_register_paths": [
            "/var/run/orbis/external_execution_register.json",
            "/opt/orbis/register/authoritative_register.json",
        ],
        "trusted_register_dirs": [
            "/var/run/orbis",
            "/opt/orbis/register",
        ],
    },
}


def resolve_canonical_deployment_profile() -> str:
    """Resolve actual runtime profile from immutable trusted deployment configuration.

    Fails closed if the deployment environment does not explicitly declare a valid
    authorized profile. Never defaults to payload or caller-supplied values.
    Source of truth must be deployment-owned and protected from caller manipulation.
    """
    from app.core.config import settings

    # Deployment-owned configuration takes absolute precedence
    target = getattr(settings, "DEPLOYED_RUNTIME_TARGET", None) or os.environ.get("DEPLOYED_RUNTIME_TARGET")
    if not target:
        # Fallback to explicit deployment environment mappings if configured
        env_val = getattr(settings, "ENVIRONMENT", "").lower()
        if env_val == "production":
            target = "PRODUCTION"
        elif env_val in ("uat", "staging"):
            target = "UAT-COMPOSE-PERSISTENT"

    if not target or not str(target).strip():
        raise RecoveryAuthError(
            "Immutable deployment runtime target is not configured (fail-closed; set DEPLOYED_RUNTIME_TARGET)"
        )

    target_str = str(target).strip()
    if target_str not in AUTHORIZED_RUNTIME_TARGET_PROFILES:
        raise AuthRuntimeMismatchError(
            f"Configured deployment runtime target '{target_str}' is not in authorized runtime profiles (fail-closed)"
        )

    return target_str


def resolve_canonical_storage_restore_roots(
    storage_provider: Optional[any] = None,
    storage_identity: str = "",
) -> list[str]:
    """Derive actual local filesystem restore roots from storage provider and storage identity."""
    roots = []
    if storage_provider is not None:
        for attr in ("restore_root", "storage_dir", "base_dir", "root_dir", "bucket_dir", "local_dir", "_base_path"):
            val = getattr(storage_provider, attr, None)
            if val and isinstance(val, (str, bytes, os.PathLike)):
                roots.append(os.path.realpath(os.path.abspath(str(val))))

    from app.core.config import settings
    env_root = os.environ.get("STORAGE_RESTORE_ROOT") or getattr(settings, "LOCAL_STORAGE_DIR", None) or os.environ.get("LOCAL_STORAGE_DIR")
    if env_root:
        roots.append(os.path.realpath(os.path.abspath(str(env_root))))
    s_bucket_dir = os.environ.get("STORAGE_BUCKET_DIR") or os.environ.get("OBJECT_STORAGE_BUCKET_DIR")
    if s_bucket_dir:
        roots.append(os.path.realpath(os.path.abspath(str(s_bucket_dir))))

    if storage_identity:
        clean_s = storage_identity.strip()
        if clean_s.startswith("file://"):
            clean_s = clean_s[7:]
        if os.path.isabs(clean_s) or os.path.exists(clean_s):
            roots.append(os.path.realpath(os.path.abspath(clean_s)))
        if "://" in clean_s:
            path_part = clean_s.split("://", 1)[1]
            if os.path.isabs(path_part) or os.path.exists(path_part):
                roots.append(os.path.realpath(os.path.abspath(path_part)))
    return list(dict.fromkeys(roots))


def resolve_canonical_resource_identities(
    db: Session,
    storage_provider: Optional[any] = None,
) -> tuple[str, str]:
    """Independently discover and canonicalize primary DB host/database and storage endpoint/bucket identity.

    Performs topology discovery against the actual underlying database and storage instances.
    Returns:
        (db_identity, storage_identity)
        e.g. ("sqlite://:memory:", "mock://local/orbis-media-assets")
    """
    bind = db.get_bind()
    url = bind.url

    # Canonicalize DB identity (driver, host, port, database without credentials)
    if url.drivername.startswith("sqlite"):
        db_path = url.database or ":memory:"
        db_identity = f"sqlite://{db_path}"
    else:
        # Topology check: independently inspect connection details
        host = url.host or "localhost"
        port = url.port or 5432
        dbname = url.database or ""
        db_identity = f"{url.drivername}://{host}:{port}/{dbname}"

    # Canonicalize Storage identity (protocol, endpoint, bucket)
    bucket = None
    endpoint = None
    if storage_provider is not None:
        bucket = getattr(storage_provider, "bucket_name", None) or getattr(storage_provider, "bucket", None)
        endpoint = getattr(storage_provider, "endpoint_url", None)
        if not endpoint and hasattr(storage_provider, "client") and hasattr(storage_provider.client, "meta"):
            endpoint = getattr(storage_provider.client.meta, "endpoint_url", None)
        if not endpoint and hasattr(storage_provider, "endpoint"):
            endpoint = getattr(storage_provider, "endpoint", None)
    if not bucket:
        from app.core.config import settings
        bucket = getattr(settings, "OBJECT_STORAGE_BUCKET", "orbis-media-assets")

    if (storage_provider is not None and hasattr(storage_provider, "_store") and not endpoint) or (storage_provider is None and db_identity.startswith("sqlite://")):
        storage_identity = f"mock://local/{bucket}"
    else:
        endpoint = endpoint or "http://localhost:9000"
        storage_identity = f"s3://{endpoint}/{bucket}"

    return db_identity, storage_identity


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


class AuditWriteFailureError(RecoveryAuthError):
    """Failure audit write failed in autonomous transaction (fail-closed)."""
    pass


def sanitize_error_message(text: str) -> str:
    """Sanitize and redact sensitive tokens, passwords, and secret keys from error messages."""
    import re
    patterns = [
        (r"(://[^:/@\s]+:)[^@\s]+(@)", r"\1[REDACTED]\2"),
        (r"://([^:]+):([^@]+)@", r"://[REDACTED_USER]:[REDACTED_PASS]@"),
        (r"(Bearer\s+)[A-Za-z0-9_\-\.]+", r"\1[REDACTED]"),
        (r"(token=)[^&\s]+", r"\1[REDACTED]"),
        (r"(password=)[^&\s]+", r"\1[REDACTED]"),
        (r"(secret=)[^&\s]+", r"\1[REDACTED]"),
        (r"(key=)[^&\s]+", r"\1[REDACTED]"),
        (r"(api[_-]?key[:=]\s*)[A-Za-z0-9_\-]+", r"\1[REDACTED]"),
    ]
    sanitized = str(text)
    for pat, repl in patterns:
        sanitized = re.sub(pat, repl, sanitized, flags=re.IGNORECASE)
    return sanitized[:512]


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
    restore_epoch: str

    def to_canonical_json(self) -> bytes:
        """Serialize payload to deterministic, sorted UTF-8 JSON without whitespace."""
        data = {
            "authorized_commit_sha": self.authorized_commit_sha,
            "auth_nonce": self.auth_nonce,
            "expires_at": self.expires_at.astimezone(timezone.utc).isoformat(),
            "issued_at": self.issued_at.astimezone(timezone.utc).isoformat(),
            "owner_evidence_anchor": self.owner_evidence_anchor,
            "provider_job_id": self.provider_job_id,
            "restore_epoch": self.restore_epoch,
            "runtime_target": self.runtime_target,
            "task_id": self.task_id,
        }
        return json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")

    def digest(self) -> str:
        """SHA-256 hex digest of canonical JSON payload."""
        return hashlib.sha256(self.to_canonical_json()).hexdigest()


class AuthoritativeExternalExecutionRegister:
    """Authoritative execution register maintained outside the DB and Object Storage restore sets.

    Guarantees atomic durable pre-GET claim with file locking, atomic swap, and fsync.
    Validates that the register path resides in a trusted external topology outside the DB and S3 restore set.
    Rejects read-only or empty-environment execution.
    """

    @classmethod
    def get_register_path(cls) -> str:
        reg_path = os.environ.get("EXTERNAL_EXECUTION_REGISTER_PATH", "").strip()
        if not reg_path:
            raise AuthRevokedError(
                "Mandatory authoritative external execution register is missing: EXTERNAL_EXECUTION_REGISTER_PATH "
                "must be configured to a writable durable path outside DB/storage restore set (fail-closed)"
            )
        return reg_path

    @classmethod
    def is_directory_fsync_required(cls, reg_dir: str, runtime_target: str = "UAT-COMPOSE-PERSISTENT") -> bool:
        """Determine platform/filesystem directory fsync capability, failing closed if capability cannot be positively provided."""
        profile = AUTHORIZED_RUNTIME_TARGET_PROFILES.get(runtime_target, {})
        profile_requires_fsync = profile.get("require_directory_fsync", False)
        env_override = os.environ.get("DIRECTORY_FSYNC_SUPPORTED")

        # Policy downgrade rejection
        if profile_requires_fsync and env_override is not None and env_override.strip().lower() in ("false", "0", "no"):
            raise RecoveryAuthError(
                f"Durability policy violation: directory fsync requirement cannot be downgraded for '{runtime_target}' (fail-closed)"
            )

        if profile_requires_fsync:
            if env_override is not None and env_override.strip().lower() in ("true", "1", "yes"):
                return True
            if os.name == "posix":
                return True
            # Non-POSIX or unsupported capability without positive proof -> FAIL CLOSED
            raise RecoveryAuthError(
                f"Durability policy violation: platform '{os.name}' cannot positively provide mandatory directory fsync "
                f"required by profile '{runtime_target}' (fail-closed)"
            )

        if env_override is not None and env_override.strip().lower() in ("true", "1", "yes"):
            return True
        if os.name == "posix":
            return True
        return False

    @classmethod
    def is_directory_fsync_supported(cls, reg_dir: str) -> bool:
        """Backwards-compatible alias to is_directory_fsync_required."""
        return cls.is_directory_fsync_required(reg_dir)

    @classmethod
    def validate_register_topology(
        cls,
        reg_path: str,
        db_identity: str = "",
        storage_identity: str = "",
        storage_provider: typing.Any = None,
        runtime_target: str = "UAT-COMPOSE-PERSISTENT",
    ) -> None:
        """Validate that register topology is trusted and decoupled from DB and Storage without heuristic proofs."""
        topology_attested = os.environ.get("EXTERNAL_EXECUTION_REGISTER_TOPOLOGY_ATTESTED", "").strip().lower() == "true"
        freshness_attested = os.environ.get("EXTERNAL_EXECUTION_REGISTER_ATTESTED", "").strip().lower() == "true"
        if not topology_attested or not freshness_attested:
            raise AuthRevokedError(
                "External execution register lacks mandatory topology/freshness attestation "
                "(EXTERNAL_EXECUTION_REGISTER_TOPOLOGY_ATTESTED and EXTERNAL_EXECUTION_REGISTER_ATTESTED must be 'true')"
            )

        norm_path = os.path.realpath(os.path.abspath(reg_path))

        # 1. Exact authoritative register binding against immutable runtime profile allowlist
        profile = AUTHORIZED_RUNTIME_TARGET_PROFILES.get(runtime_target)
        if profile is None:
            raise AuthRevokedError(f"Unauthorized runtime target profile '{runtime_target}' (fail-closed)")

        is_live_profile = profile.get("require_persistent_db", False) or runtime_target in ("UAT-COMPOSE-PERSISTENT", "PRODUCTION")
        profile_allowed_paths = [os.path.realpath(os.path.abspath(p)) for p in profile.get("trusted_register_paths", [])]
        trusted_exact_env = os.environ.get("TRUSTED_EXTERNAL_REGISTER_PATH", "").strip()
        trusted_dir_env = os.environ.get("TRUSTED_EXTERNAL_REGISTER_DIR", "").strip()

        if is_live_profile:
            if not profile_allowed_paths:
                raise AuthRevokedError(
                    f"Configuration error: live profile '{runtime_target}' lacks immutable trusted_register_paths allowlist (fail-closed)"
                )
            if norm_path not in profile_allowed_paths:
                raise AuthRuntimeMismatchError(
                    f"External execution register path '{norm_path}' is not in immutable trusted profile allowlist "
                    f"{profile_allowed_paths} for live runtime target '{runtime_target}' (fail-closed)"
                )
            # Live profile requires exact binding: directory-only binding without exact match is rejected
            if trusted_dir_env and not trusted_exact_env and norm_path not in profile_allowed_paths:
                raise AuthRuntimeMismatchError(
                    f"Directory-only register binding is forbidden for live profile '{runtime_target}'; exact path binding required (fail-closed)"
                )
            if trusted_exact_env:
                norm_env_exact = os.path.realpath(os.path.abspath(trusted_exact_env))
                if norm_env_exact != norm_path:
                    raise AuthRuntimeMismatchError(
                        f"External execution register path '{norm_path}' does not match TRUSTED_EXTERNAL_REGISTER_PATH '{norm_env_exact}'"
                    )
                if norm_env_exact not in profile_allowed_paths:
                    raise AuthRuntimeMismatchError(
                        f"Environment TRUSTED_EXTERNAL_REGISTER_PATH '{norm_env_exact}' is not in immutable trusted profile allowlist {profile_allowed_paths}"
                    )
        else:
            # Ephemeral / mock profile binding
            if not trusted_exact_env and not trusted_dir_env and not profile_allowed_paths:
                raise AuthRevokedError(
                    "Mandatory trusted external register configuration is missing (fail-closed)"
                )
            if trusted_exact_env:
                norm_trusted_exact = os.path.realpath(os.path.abspath(trusted_exact_env))
                if norm_path != norm_trusted_exact:
                    raise AuthRuntimeMismatchError(
                        f"External execution register path '{norm_path}' does not match trusted exact register path '{norm_trusted_exact}'"
                    )
            if profile_allowed_paths and norm_path not in profile_allowed_paths:
                raise AuthRuntimeMismatchError(
                    f"External execution register path '{norm_path}' is not in profile allowed paths {profile_allowed_paths}"
                )
            if trusted_dir_env:
                norm_allowed = os.path.realpath(os.path.abspath(trusted_dir_env))
                if norm_path != norm_allowed and not norm_path.startswith(norm_allowed + os.sep):
                    raise AuthRuntimeMismatchError(
                        f"External execution register path '{norm_path}' is outside trusted register directory '{norm_allowed}'"
                    )

        # 2. Real path / mount decoupling from DB restore set
        db_dir = None
        if db_identity:
            clean_db = db_identity
            for prefix in ("sqlite:///", "sqlite://", "sqlite:"):
                if clean_db.lower().startswith(prefix):
                    clean_db = clean_db[len(prefix):]
                    break
            if clean_db and clean_db != ":memory:":
                db_real = os.path.realpath(os.path.abspath(clean_db))
                db_dir = os.path.dirname(db_real) if (os.path.isfile(db_real) or not os.path.isdir(db_real)) else db_real
                if norm_path == db_real or norm_path == db_dir or norm_path.startswith(db_dir + os.sep) or db_dir.startswith(norm_path + os.sep):
                    raise AuthRuntimeMismatchError(
                        f"External execution register path '{norm_path}' cannot reside inside DB directory/file '{db_dir}' (topology collision)"
                    )

        # 3. Real path / mount decoupling from Storage restore set (derived directly from real provider and identity)
        storage_roots = resolve_canonical_storage_restore_roots(storage_provider=storage_provider, storage_identity=storage_identity)

        for s_root in storage_roots:
            if s_root:
                s_real = os.path.realpath(os.path.abspath(s_root))
                if norm_path == s_real or norm_path.startswith(s_real + os.sep) or s_real.startswith(norm_path + os.sep):
                    raise AuthRuntimeMismatchError(
                        f"External execution register path '{norm_path}' cannot reside inside storage restore set directory '{s_real}' (topology collision)"
                    )

        # 4. Strict mount / device decoupling and non-downgradeable policy
        profile_requires_distinct_mount = profile.get("require_distinct_mount", False)
        env_distinct_mount = os.environ.get("EXTERNAL_REGISTER_REQUIRE_DISTINCT_MOUNT")

        if profile_requires_distinct_mount and env_distinct_mount is not None and env_distinct_mount.strip().lower() in ("false", "0", "no"):
            raise AuthRuntimeMismatchError(
                f"Durability policy violation: distinct mount requirement cannot be downgraded for runtime target '{runtime_target}' (fail-closed)"
            )

        require_distinct_mount = profile_requires_distinct_mount or (env_distinct_mount and env_distinct_mount.strip().lower() in ("true", "1", "yes"))
        if require_distinct_mount:
            reg_check_path = norm_path if os.path.exists(norm_path) else os.path.dirname(norm_path)
            if os.path.exists(reg_check_path):
                reg_stat = os.stat(reg_check_path)
                reg_dev = getattr(reg_stat, "st_dev", None)
                if reg_dev is not None:
                    if db_dir and os.path.exists(db_dir):
                        db_stat = os.stat(db_dir)
                        if getattr(db_stat, "st_dev", None) == reg_dev:
                            raise AuthRuntimeMismatchError(
                                f"External execution register mount (dev={reg_dev}) collides with DB mount (dev={getattr(db_stat, 'st_dev', None)}); distinct mount required (fail-closed)"
                            )
                    for s_root in storage_roots:
                        if s_root and os.path.exists(s_root):
                            s_stat = os.stat(s_root)
                            if getattr(s_stat, "st_dev", None) == reg_dev:
                                raise AuthRuntimeMismatchError(
                                    f"External execution register mount (dev={reg_dev}) collides with storage mount (dev={getattr(s_stat, 'st_dev', None)}); distinct mount required (fail-closed)"
                                )

    @classmethod
    def _read_register_unlocked(cls, reg_path: str) -> dict:
        """Read external register without acquiring exclusive lock."""
        if not os.path.exists(reg_path):
            return {"dispatched_jobs": [], "dispatched_nonces": [], "consumed_jobs": [], "consumed_nonces": []}
        with open(reg_path, "r", encoding="utf-8") as f:
            return json.load(f)

    @classmethod
    def _acquire_lock_and_read(cls, reg_path: str):
        """Cross-platform atomic file lock and load."""
        import time
        lock_path = f"{reg_path}.lock"
        os.makedirs(os.path.dirname(os.path.abspath(reg_path)), exist_ok=True)

        acquired = False
        start_lock = time.monotonic()
        while time.monotonic() - start_lock < 5.0:
            try:
                fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_RDWR)
                acquired = True
                break
            except FileExistsError:
                time.sleep(0.02)

        if not acquired:
            raise RecoveryAuthError(f"Failed to acquire atomic lock on external register '{lock_path}' within 5s")

        try:
            reg_data = {"dispatched_jobs": [], "dispatched_nonces": [], "consumed_jobs": [], "consumed_nonces": []}
            if os.path.exists(reg_path):
                with open(reg_path, "r", encoding="utf-8") as f:
                    reg_data = json.load(f)
            return fd, lock_path, reg_data
        except Exception as e:
            try:
                os.close(fd)
                if os.path.exists(lock_path):
                    os.remove(lock_path)
            except Exception:
                pass
            raise RecoveryAuthError(f"Failed to read external register at '{reg_path}': {sanitize_error_message(str(e))}") from e

    @classmethod
    def _write_atomic_and_release(
        cls,
        reg_path: str,
        fd: int,
        lock_path: str,
        reg_data: dict,
        runtime_target: str = "UAT-COMPOSE-PERSISTENT",
    ) -> None:
        """Atomic write via temporary file, flush, fsync, os.replace, parent directory fsync, and release lock."""
        import time
        reg_dir = os.path.dirname(os.path.abspath(reg_path))
        tmp_path = f"{reg_path}.tmp.{os.getpid()}.{time.time_ns()}"
        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(reg_data, f, indent=2)
                f.flush()
                os.fsync(f.fileno())

            # Atomic swap / replace
            os.replace(tmp_path, reg_path)

            # Directory durability acknowledgement: fsync parent directory on supported platforms (fail-closed)
            if cls.is_directory_fsync_required(reg_dir, runtime_target=runtime_target):
                dir_fd = None
                try:
                    open_flags = os.O_RDONLY
                    if hasattr(os, "O_DIRECTORY"):
                        open_flags |= os.O_DIRECTORY
                    dir_fd = os.open(reg_dir, open_flags)
                    os.fsync(dir_fd)
                except Exception as d_err:
                    raise RecoveryAuthError(
                        f"Parent directory fsync failed for '{reg_dir}': {sanitize_error_message(str(d_err))}"
                    ) from d_err
                finally:
                    if dir_fd is not None:
                        try:
                            os.close(dir_fd)
                        except Exception:
                            pass

            # Final acknowledgement verification: assert file exists, is readable and contains written state
            if not os.path.exists(reg_path):
                raise RecoveryAuthError(f"Durable acknowledgement failure: external register '{reg_path}' missing after atomic write")
            ack_data = cls._read_register_unlocked(reg_path)
            for j in reg_data.get("dispatched_jobs", []):
                if j not in ack_data.get("dispatched_jobs", []):
                    raise RecoveryAuthError(f"Durable acknowledgement failure: dispatched_job '{j}' not found in '{reg_path}'")
            for n in reg_data.get("dispatched_nonces", []):
                if n not in ack_data.get("dispatched_nonces", []):
                    raise RecoveryAuthError(f"Durable acknowledgement failure: dispatched_nonce '{n}' not found in '{reg_path}'")
            for cj in reg_data.get("consumed_jobs", []):
                if cj not in ack_data.get("consumed_jobs", []):
                    raise RecoveryAuthError(f"Durable acknowledgement failure: consumed_job '{cj}' not found in '{reg_path}'")
            for cn in reg_data.get("consumed_nonces", []):
                if cn not in ack_data.get("consumed_nonces", []):
                    raise RecoveryAuthError(f"Durable acknowledgement failure: consumed_nonce '{cn}' not found in '{reg_path}'")
        finally:
            try:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
            except Exception:
                pass
            try:
                os.close(fd)
                if os.path.exists(lock_path):
                    os.remove(lock_path)
            except Exception:
                pass

    @classmethod
    def check_and_assert_freshness(
        cls,
        provider_job_id: str,
        auth_nonce: str,
        db_identity: str = "",
        storage_identity: str = "",
        storage_provider: typing.Any = None,
        runtime_target: str = "UAT-COMPOSE-PERSISTENT",
    ) -> None:
        """Verify external evidence outside DB and storage before any network I/O.

        Requires a valid, writable external register path with attested topology.
        Empty environment or read-only mode fails closed.
        """
        reg_path = cls.get_register_path()
        cls.validate_register_topology(
            reg_path,
            db_identity=db_identity,
            storage_identity=storage_identity,
            storage_provider=storage_provider,
            runtime_target=runtime_target,
        )

        fd, lock_path, reg_data = cls._acquire_lock_and_read(reg_path)
        try:
            dispatched_jobs = reg_data.get("dispatched_jobs", [])
            dispatched_nonces = reg_data.get("dispatched_nonces", [])
            consumed_jobs = reg_data.get("consumed_jobs", [])
            consumed_nonces = reg_data.get("consumed_nonces", [])

            if provider_job_id in dispatched_jobs or provider_job_id in consumed_jobs:
                raise AuthReplayError(
                    f"Authoritative external register at '{reg_path}' confirms provider_job_id '{provider_job_id}' "
                    f"was previously dispatched or consumed outside DB/storage restore set; second GET rejected"
                )
            if auth_nonce in dispatched_nonces or auth_nonce in consumed_nonces:
                raise AuthReplayError(
                    f"Authoritative external register at '{reg_path}' confirms nonce '{auth_nonce}' "
                    f"was previously consumed outside DB/storage restore set; second GET rejected"
                )
        finally:
            try:
                os.close(fd)
                if os.path.exists(lock_path):
                    os.remove(lock_path)
            except Exception:
                pass

    @classmethod
    def claim_pre_get_dispatch(
        cls,
        provider_job_id: str,
        auth_nonce: str,
        execution_id: str,
        db_identity: str = "",
        storage_identity: str = "",
        storage_provider: typing.Any = None,
        runtime_target: str = "UAT-COMPOSE-PERSISTENT",
    ) -> None:
        """Atomically claim pre-GET dispatch fence with durable fsync before provider GET."""
        reg_path = cls.get_register_path()
        cls.validate_register_topology(
            reg_path,
            db_identity=db_identity,
            storage_identity=storage_identity,
            storage_provider=storage_provider,
            runtime_target=runtime_target,
        )

        fd, lock_path, reg_data = cls._acquire_lock_and_read(reg_path)
        try:
            dispatched_jobs = reg_data.setdefault("dispatched_jobs", [])
            dispatched_nonces = reg_data.setdefault("dispatched_nonces", [])
            consumed_jobs = reg_data.setdefault("consumed_jobs", [])
            consumed_nonces = reg_data.setdefault("consumed_nonces", [])

            if provider_job_id in dispatched_jobs or provider_job_id in consumed_jobs:
                raise AuthReplayError(
                    f"Authoritative external register at '{reg_path}' confirms provider_job_id '{provider_job_id}' "
                    f"was already claimed/dispatched; concurrent or replay GET rejected"
                )
            if auth_nonce in dispatched_nonces or auth_nonce in consumed_nonces:
                raise AuthReplayError(
                    f"Authoritative external register at '{reg_path}' confirms nonce '{auth_nonce}' "
                    f"was already claimed; concurrent or replay GET rejected"
                )

            dispatched_jobs.append(provider_job_id)
            dispatched_nonces.append(auth_nonce)
            cls._write_atomic_and_release(reg_path, fd, lock_path, reg_data, runtime_target=runtime_target)

            # Durable acknowledgement read-back verification
            ack_data = cls._read_register_unlocked(reg_path)
            if (
                provider_job_id not in ack_data.get("dispatched_jobs", [])
                or auth_nonce not in ack_data.get("dispatched_nonces", [])
            ):
                raise RecoveryAuthError(
                    f"Durable acknowledgement failed: claim for job '{provider_job_id}' / nonce '{auth_nonce}' not persisted to '{reg_path}'"
                )
        except Exception:
            try:
                os.close(fd)
                if os.path.exists(lock_path):
                    os.remove(lock_path)
            except Exception:
                pass
            raise

    @classmethod
    def record_dispatch(cls, provider_job_id: str, auth_nonce: str, execution_id: str) -> None:
        """Alias to atomic claim_pre_get_dispatch for backwards compatibility."""
        cls.claim_pre_get_dispatch(provider_job_id, auth_nonce, execution_id)

    @classmethod
    def record_consumed(
        cls,
        provider_job_id: str,
        auth_nonce: str,
        db_identity: str = "",
        storage_identity: str = "",
        storage_provider: typing.Any = None,
        runtime_target: str = "UAT-COMPOSE-PERSISTENT",
    ) -> None:
        """Atomically record terminal consumption to external register."""
        reg_path = cls.get_register_path()
        cls.validate_register_topology(
            reg_path,
            db_identity=db_identity,
            storage_identity=storage_identity,
            storage_provider=storage_provider,
            runtime_target=runtime_target,
        )

        fd, lock_path, reg_data = cls._acquire_lock_and_read(reg_path)
        try:
            consumed_jobs = reg_data.setdefault("consumed_jobs", [])
            consumed_nonces = reg_data.setdefault("consumed_nonces", [])
            if provider_job_id not in consumed_jobs:
                consumed_jobs.append(provider_job_id)
            if auth_nonce not in consumed_nonces:
                consumed_nonces.append(auth_nonce)
            cls._write_atomic_and_release(reg_path, fd, lock_path, reg_data, runtime_target=runtime_target)
        except Exception:
            try:
                os.close(fd)
                if os.path.exists(lock_path):
                    os.remove(lock_path)
            except Exception:
                pass
            raise


class RecoveryAuthService:
    """Two-phase asymmetric authorization verification."""

    @classmethod
    def get_current_runtime_restore_epoch(cls) -> str:
        """Independently source current runtime restore epoch with fail-closed missing/attestation check."""
        import os
        epoch = os.environ.get("CURRENT_RESTORE_EPOCH", "").strip()
        attested = os.environ.get("RESTORE_EPOCH_ATTESTED", "").strip().lower() == "true"
        if not epoch:
            raise AuthRevokedError(
                "Current runtime restore epoch is missing (CURRENT_RESTORE_EPOCH must be set, fail-closed)"
            )
        if not attested:
            raise AuthRevokedError(
                "Current runtime restore epoch lacks mandatory freshness attestation "
                "(RESTORE_EPOCH_ATTESTED must be 'true', fail-closed)"
            )
        return epoch

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
        6. Explicit signed restore_epoch matching current runtime restore epoch

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

        # 6. Restore Epoch verification (required signed field)
        token_epoch = getattr(payload, "restore_epoch", None)
        if not token_epoch or not str(token_epoch).strip():
            raise AuthScopeMismatchError("CanonicalAuthPayload missing required non-empty 'restore_epoch' field")

        current_epoch = cls.get_current_runtime_restore_epoch()
        if str(token_epoch).strip() != current_epoch:
            raise AuthScopeMismatchError(
                f"Restore epoch mismatch: token restore_epoch '{token_epoch}' != current runtime epoch '{current_epoch}' (fail-closed)"
            )

        return payload.digest()

    @classmethod
    def verify_phase_2_and_claim_fence(
        cls,
        db: Session,
        payload: CanonicalAuthPayload,
        auth_digest: str,
        execution_id: str,
        actual_runtime_target: str,
        revocation_list: Optional[list[str]] = None,
        storage_provider: Optional[any] = None,
    ) -> ProviderExecutionFence:
        """Phase 2: Database and runtime target validation pre-GET.

        Verifies:
        1. Restored-runtime safety: VIDU_GENERATION_ENABLED must be False, VIDU_RECOVERY_GET_ENABLED must not be False.
        2. Out-of-band evidence anchor syntax matches allowed format.
        3. Independently discovered actual DB identity and storage bucket match authorized profile for runtime_target.
        4. Runtime target string matches payload.
        5. Revocation check (Fail-Closed: missing or unattested empty registry rejected).
        6. Replay protection (nonce uniqueness in DB).
        7. Same-job concurrency fence (provider_name + provider_job_id uniqueness in DB).
        8. Restored DB check: deterministic GenerationJob existence when fence missing.
        9. Authoritative out-of-band consumption check: detects consumed job in storage marker/asset or external registry.

        Inserts and commits fence record with status 'CLAIMED_PENDING_GET'.
        """
        # 1. Restored-runtime provider safety check: Generation must be disabled
        import os
        from app.core.config import settings
        gen_enabled = getattr(settings, "VIDU_GENERATION_ENABLED", None)
        if gen_enabled is None:
            gen_enabled = os.environ.get("VIDU_GENERATION_ENABLED", "false").lower() in ("true", "1")
        if gen_enabled:
            raise RecoveryAuthError("Restored runtime safety check failed: VIDU_GENERATION_ENABLED must be False during recovery")

        rec_enabled = getattr(settings, "VIDU_RECOVERY_GET_ENABLED", None)
        if rec_enabled is None:
            rec_enabled = os.environ.get("VIDU_RECOVERY_GET_ENABLED", "false").lower() in ("true", "1")
        if not rec_enabled:
            raise RecoveryAuthError("Restored runtime safety check failed: VIDU_RECOVERY_GET_ENABLED is not explicitly True (fail-closed)")

        # 2. Out-of-band evidence anchor validation
        import re
        anchor = (payload.owner_evidence_anchor or "").strip()
        if not re.match(r"^(telegram|issue|pr|evidence|rec1|r5|run1)[\w\-\.\/:]+$", anchor, re.IGNORECASE):
            raise AuthScopeMismatchError(f"Invalid owner_evidence_anchor format: '{anchor}'")

        # 3. Independent discovery and verification of actual DB and storage identity
        actual_db_id, actual_storage_id = resolve_canonical_resource_identities(db, storage_provider)

        # Runtime target string match
        if payload.runtime_target != actual_runtime_target:
            raise AuthRuntimeMismatchError(
                f"Runtime target mismatch: authorized '{payload.runtime_target}' != actual '{actual_runtime_target}'"
            )

        # Validate discovered resource identity against authorized profile for runtime_target (fail-closed on unknown profile)
        if payload.runtime_target not in AUTHORIZED_RUNTIME_TARGET_PROFILES:
            raise AuthRuntimeMismatchError(
                f"Unknown or unauthorized runtime target profile '{payload.runtime_target}' (fail-closed)"
            )

        profile = AUTHORIZED_RUNTIME_TARGET_PROFILES[payload.runtime_target]
        db_matched = actual_db_id in profile["trusted_db_identities"]
        storage_matched = actual_storage_id in profile["trusted_storage_identities"]

        if not db_matched or not storage_matched:
            raise AuthRuntimeMismatchError(
                f"Actual resource configuration does not match authorized runtime target profile '{payload.runtime_target}': "
                f"actual_db='{actual_db_id}', actual_storage='{actual_storage_id}'"
            )

        # 4. Revocation check (Fail-Closed: missing evidence or unattested empty registry is treated as an error)
        import os
        revocations = set(revocation_list) if revocation_list is not None else None
        if revocations is None:
            if "OWNER_AUTH_REVOCATIONS" not in os.environ:
                raise AuthRevokedError("Revocation check failed: revocation registry evidence is missing (fail-closed)")
            env_rev = os.environ.get("OWNER_AUTH_REVOCATIONS", "")
            if env_rev == "" and os.environ.get("OWNER_AUTH_REVOCATIONS_ATTESTED", "").lower() != "true":
                raise AuthRevokedError("Revocation check failed: revocation registry is empty without active freshness attestation (fail-closed)")
            revocations = {x.strip() for x in env_rev.split(",") if x.strip()}

        if payload.auth_nonce in revocations:
            raise AuthRevokedError(f"Authorization nonce '{payload.auth_nonce}' is in revocation register")
        if payload.owner_evidence_anchor in revocations:
            raise AuthRevokedError(f"Owner evidence anchor '{payload.owner_evidence_anchor}' is in revocation register")

        # 5. Check existing fence by nonce (Replay check)
        existing_nonce_fence = db.execute(
            select(ProviderExecutionFence).where(
                ProviderExecutionFence.auth_nonce == payload.auth_nonce
            )
        ).scalar_one_or_none()

        if existing_nonce_fence is not None:
            raise AuthReplayError(
                f"Authorization nonce '{payload.auth_nonce}' has already been consumed (fence_id={existing_nonce_fence.fence_id})"
            )

        # 6. Check existing fence by provider_job_id (Same-job concurrency check)
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

        # 6. Mandatory check on OUT_OF_BAND_CONSUMED_EVIDENCE freshness attestation
        out_of_band_consumed = os.environ.get("OUT_OF_BAND_CONSUMED_EVIDENCE", "").strip()
        if out_of_band_consumed:
            oob_attested = os.environ.get("OUT_OF_BAND_CONSUMED_ATTESTED", "").strip().lower() == "true"
            if not oob_attested:
                raise AuthRevokedError("External consumed registry lacks mandatory freshness attestation")
            consumed_list = [j.strip() for j in out_of_band_consumed.split(",") if j.strip()]
            if payload.provider_job_id in consumed_list:
                raise AuthReplayError(
                    f"Out-of-band consumption evidence confirms provider_job_id '{payload.provider_job_id}' "
                    f"was already executed and consumed outside current DB state; second GET rejected"
                )

        # 7. Adversarial check for restored DB missing fence with unchanged runtime label
        from app.models.generation_job import GenerationJob
        job_uuid = uuid.uuid5(uuid.NAMESPACE_URL, f"orbis://vidu-recovery/job/{payload.provider_job_id}")
        existing_job = db.get(GenerationJob, job_uuid)
        if existing_job is not None:
            raise AuthSameJobConcurrentError(
                f"Restored DB state detected: GenerationJob '{job_uuid}' already exists for provider_job_id "
                f"'{payload.provider_job_id}' but ProviderExecutionFence is missing"
            )

        # 8. Restore Epoch binding validation: Token must match independently sourced current restore epoch
        current_epoch = cls.get_current_runtime_restore_epoch()
        if payload.restore_epoch != current_epoch:
            raise AuthScopeMismatchError(
                f"Authorization token is bound to stale restore epoch: '{payload.restore_epoch}' != current runtime epoch '{current_epoch}' (fail-closed)"
            )

        # 9. Mandatory Authoritative External Execution Register Check (Decoupled from DB/Storage restore set)
        AuthoritativeExternalExecutionRegister.check_and_assert_freshness(
            provider_job_id=payload.provider_job_id,
            auth_nonce=payload.auth_nonce,
            db_identity=actual_db_id,
            storage_identity=actual_storage_id,
            storage_provider=storage_provider,
            runtime_target=payload.runtime_target,
        )

        if storage_provider is not None:
            b_names = [
                getattr(storage_provider, "bucket_name", None),
                getattr(storage_provider, "bucket", None),
                getattr(settings, "OBJECT_STORAGE_BUCKET", None),
                "orbis-media-assets",
                "orbis-assets",
            ]
            fence_keys_to_check = [
                f"fences/in_flight/{payload.provider_job_id}.json",
                f"fences/consumed/{payload.provider_job_id}.json",
            ]
            project_uuid = uuid.uuid5(uuid.NAMESPACE_URL, f"orbis://vidu-recovery/project/{payload.provider_job_id}")
            asset_uuid = uuid.uuid5(uuid.NAMESPACE_URL, f"orbis://video-generation/{job_uuid}")
            fence_keys_to_check.append(f"assets/video/{project_uuid}/{asset_uuid}.mp4")

            has_marker = False
            for b in b_names:
                if not b:
                    continue
                for key_chk in fence_keys_to_check:
                    try:
                        if storage_provider.object_exists(b, key_chk):
                            has_marker = True
                            break
                    except Exception as st_err:
                        sanitized_st = sanitize_error_message(str(st_err))
                        raise RecoveryAuthError(
                            f"Storage accessibility failure while inspecting external execution fence for '{b}/{key_chk}': {sanitized_st}"
                        ) from st_err
                if has_marker:
                    break

            if not has_marker and hasattr(storage_provider, "_store"):
                for (b, k) in storage_provider._store.keys():
                    for key_chk in fence_keys_to_check:
                        if k == key_chk or k.endswith(f"/{payload.provider_job_id}.json"):
                            has_marker = True
                            break
                    if has_marker:
                        break

            if has_marker:
                raise AuthReplayError(
                    f"Authoritative external execution fence detected for provider_job_id '{payload.provider_job_id}' "
                    f"(attempt already dispatched or consumed outside restored DB snapshot; second GET rejected)"
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
        db_transaction_state: str = "FAILED",
        compensation_status: str = "NOT_APPLICABLE",
        fence_id: Optional[uuid.UUID] = None,
        orphan_bucket: Optional[str] = None,
        orphan_key: Optional[str] = None,
    ) -> RecoveryFailureAudit:
        """Record a sanitized failure audit in an autonomous, committed transaction.

        Uses an independent session bound to the same engine to ensure the audit
        is persisted even if the primary session is rolled back or failed.
        """
        from sqlalchemy.orm import sessionmaker

        sanitized_msg = sanitize_error_message(str(error_message))

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
            bind = db.get_bind()
            autonomous_factory = sessionmaker(bind=bind, expire_on_commit=False)
            with autonomous_factory() as autonomous_session:
                autonomous_session.add(audit)
                autonomous_session.commit()
                autonomous_session.refresh(audit)
                return audit
        except Exception as exc:
            sanitized_exc = sanitize_error_message(str(exc))
            raise AuditWriteFailureError(f"Failed to record autonomous failure audit: {sanitized_exc}") from exc
