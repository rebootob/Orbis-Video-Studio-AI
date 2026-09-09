"""Pure fail-closed guards for P4-WP020-LIVE R4 tooling.

This module performs no provider I/O. It centralizes the immutable R4 execution
identity, exact paid-call order, budget ceiling, authorization/fence markers,
and sanitized durable failure evidence rules used by the manual R4 workflows.
"""
from __future__ import annotations

import math
import re
from typing import Any, Mapping, Sequence

R4_EXECUTION_ID = "LIVE-20260909-DE17-R4"
R4_TOOLING_BASE_SHA = "de17a125dcd3b8066a546369d03aba813a7b5641"
ISSUE_NUMBER = 63
HARD_CAP_USD = 1.00
MAX_PAID_CALLS = 6

PAID_CALL_SEQUENCE: tuple[str, ...] = (
    "OPENAI_CREATIVE_STORY:gpt-4o",
    "GEMINI_IMAGE:gemini-3.1-flash-image:1K",
    "VIDU_VIDEO:viduq2:text2video:4s:720p",
    "ELEVENLABS_TTS:Thai:<=150chars",
    "ELEVENLABS_MUSIC:<=10s",
    "ELEVENLABS_AMBIENCE:<=3s",
)

_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
_SAFE_RESULT_KEYS = (
    "provider",
    "model",
    "http_status",
    "status_code",
    "error_code",
    "retryable",
    "submission_uncertain",
    "provider_status",
    "quota_class",
    "retry_delay",
)
_SAFE_QUOTA_FAILURE_KEYS = (
    "quota_metric",
    "quota_id",
    "quota_value",
)
_SAFE_QUOTA_DIMENSION_KEYS = (
    "model",
    "location",
)
_SAFE_PROVENANCE_KEYS = (
    "provider_job_id",
    "error_code",
    "stage",
)


def authorization_marker(main_sha: str) -> str:
    """Return the exact Owner marker accepted by the paid R4 workflow."""
    if not _SHA_RE.fullmatch(main_sha or ""):
        raise ValueError("R4 authorization requires an exact 40-character lowercase main SHA")
    return f"FRESH_OWNER_AUTHORIZED_R4: {R4_EXECUTION_ID} @ {main_sha}"


def execution_fence_marker() -> str:
    return f"EXECUTION_STARTED: {R4_EXECUTION_ID}"


def validate_runtime_binding(*, github_sha: str, authorized_main_sha: str, fence_confirmed: bool) -> None:
    """Fail closed unless runtime execution is bound to the exact authorized main."""
    if not _SHA_RE.fullmatch(github_sha or ""):
        raise RuntimeError("R4 runtime GITHUB_SHA is missing or invalid")
    if authorized_main_sha != github_sha:
        raise RuntimeError("R4 authorized main SHA must exactly equal workflow GITHUB_SHA")
    if not fence_confirmed:
        raise RuntimeError("R4 execution fence is not confirmed")


def next_paid_call(consumed: Sequence[str], label: str) -> int:
    """Enforce exact sequential call order and return the new call count."""
    count = len(consumed)
    if count >= MAX_PAID_CALLS:
        raise RuntimeError("R4 paid-call ceiling reached")
    expected = PAID_CALL_SEQUENCE[count]
    if label != expected:
        raise RuntimeError(f"R4 paid-call order violation: expected {expected!r}, got {label!r}")
    return count + 1


def enforce_budget(*, committed_usd: float, unknown_cost_count: int = 0) -> None:
    """Fail closed on unknown/invalid cost truth or a value above the hard cap."""
    if unknown_cost_count:
        raise RuntimeError("R4 usage ledger contains UNKNOWN cost evidence")
    if not isinstance(committed_usd, (int, float)) or not math.isfinite(float(committed_usd)):
        raise RuntimeError("R4 committed cost is not finite")
    if float(committed_usd) < 0:
        raise RuntimeError("R4 committed cost is negative")
    if float(committed_usd) > HARD_CAP_USD + 1e-9:
        raise RuntimeError(f"R4 hard UAT budget exceeded: USD {float(committed_usd):.4f}")


def require_provider_success(
    provider: str,
    status: str,
    *,
    submission_uncertain: bool = False,
) -> None:
    """Reject every ambiguous or non-success provider terminal status."""
    if submission_uncertain or status == "RECONCILIATION_REQUIRED":
        raise RuntimeError(f"{provider} provider outcome requires reconciliation")
    if status not in {"SUCCESS", "COMPLETED", "READY"}:
        raise RuntimeError(f"{provider} provider returned non-success status: {status}")


def _copy_allowlist(source: Mapping[str, Any] | None, keys: Sequence[str]) -> dict[str, Any]:
    if not isinstance(source, Mapping):
        return {}
    return {key: source[key] for key in keys if key in source and source[key] is not None}


def _sanitize_quota_failures(source: Mapping[str, Any] | None) -> list[dict[str, Any]]:
    """Copy only the structured quota fields already sanitized by the provider adapter."""
    if not isinstance(source, Mapping):
        return []
    failures = source.get("quota_failures")
    if not isinstance(failures, Sequence) or isinstance(failures, (str, bytes, bytearray)):
        return []

    safe_failures: list[dict[str, Any]] = []
    for row in failures[:4]:
        if not isinstance(row, Mapping):
            continue
        safe_row = _copy_allowlist(row, _SAFE_QUOTA_FAILURE_KEYS)
        dimensions = row.get("quota_dimensions")
        safe_dimensions = _copy_allowlist(
            dimensions if isinstance(dimensions, Mapping) else None,
            _SAFE_QUOTA_DIMENSION_KEYS,
        )
        if safe_dimensions:
            safe_row["quota_dimensions"] = safe_dimensions
        if safe_row:
            safe_failures.append(safe_row)
    return safe_failures


def sanitize_creative_audit(
    audit: Any,
    *,
    fallback_provider: str = "openai",
    fallback_model: str = "gpt-4o",
) -> dict[str, Any]:
    """Serialize only non-content creative generation audit metadata."""
    if audit is None:
        return {}
    provider = getattr(audit, "provider", None)
    model = getattr(audit, "model", None)
    if provider in (None, "", "unknown"):
        provider = fallback_provider
    if model in (None, "", "unknown"):
        model = fallback_model
    evidence: dict[str, Any] = {
        "kind": "creative_audit",
        "audit_id": str(getattr(audit, "id", "")),
        "provider": provider,
        "model": model,
        "request_type": getattr(audit, "request_type", None),
        "status": getattr(audit, "status", None),
        "duration_ms": getattr(audit, "duration_ms", None),
    }
    return {key: value for key, value in evidence.items() if value not in (None, "")}


def sanitize_generation_job(job: Any) -> dict[str, Any]:
    """Serialize only allowlisted GenerationJob failure metadata."""
    if job is None:
        return {}
    evidence: dict[str, Any] = {
        "kind": "generation_job",
        "job_id": str(getattr(job, "id", "")),
        "provider": getattr(job, "provider_name", None),
        "provider_job_id": getattr(job, "provider_job_id", None),
        "status": getattr(job, "status", None),
        "job_type": getattr(job, "job_type", None),
        "cost_usd": getattr(job, "cost_usd", None),
    }
    raw_result = getattr(job, "result", None)
    result = _copy_allowlist(raw_result, _SAFE_RESULT_KEYS)
    quota_failures = _sanitize_quota_failures(raw_result)
    if quota_failures:
        result["quota_failures"] = quota_failures
    if result:
        evidence["result"] = result
    return {key: value for key, value in evidence.items() if value not in (None, "")}


def sanitize_audio_clip(clip: Any) -> dict[str, Any]:
    """Serialize only allowlisted AudioClip failure metadata."""
    if clip is None:
        return {}
    evidence: dict[str, Any] = {
        "kind": "audio_clip",
        "clip_id": str(getattr(clip, "id", "")),
        "audio_type": getattr(clip, "audio_type", None),
        "status": getattr(clip, "status", None),
    }
    provenance = _copy_allowlist(getattr(clip, "provenance", None), _SAFE_PROVENANCE_KEYS)
    if provenance:
        evidence["provenance"] = provenance
    return {key: value for key, value in evidence.items() if value not in (None, "")}
