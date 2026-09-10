#!/usr/bin/env python3
"""WP020 LIVE R5 Vidu2 1-Call Probe Tooling.

Bounded single-generation probe runner dedicated to VIDU2 diagnostic execution.
Strictly enforced invariants:
- Zero live provider or network calls when run locally or during test execution.
- Exactly 1 POST generation call maximum (MAX_GENERATION_POSTS = 1).
- Non-retryable on POST failure or ambiguous submission transport outcome.
- GET-only polling after confirmed generation job submission.
- Zero calls to OpenAI, Gemini, or ElevenLabs.
- Reserved execution identity: LIVE-20260910-VIDU2-R5 (reserved in tooling; NOT authorized for live execution).
- Evidence sanitization excludes secrets, tokens, raw response bodies, and response headers.
- Typed provider_http_status and failure_classification preserved for HTTP diagnostics.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, Optional

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_VIDU2_EXECUTION_ID = "LIVE-20260910-VIDU2-R5"
EXPECTED_VIDU2_EXECUTION_ID = "LIVE-20260910-VIDU2-R5"
ISSUE_NUMBER = 63
MAX_GENERATION_POSTS = 1

TARGET_PROVIDER = "vidu"
TARGET_MODEL = "viduq2"
TARGET_MODE = "text-to-video"
TARGET_DURATION_SECONDS = 4.0
TARGET_RESOLUTION = "720p"
TARGET_ASPECT_RATIO = "16:9"
TARGET_PROMPT = (
    "Cinematic slow aerial shot of calm turquoise ocean waves breaking on a golden sand beach at dawn, "
    "soft warm morning lighting, photorealistic, 4k"
)

FORBIDDEN_REUSED_EXECUTION_IDS = frozenset({
    "LIVE-20260909-VIDU1-R5",
    "LIVE-20260909-DE17-R4",
    "LIVE-20260909-363F-R3",
    "LIVE-20260908-468E-R2",
    "LIVE-20260908-B023-R1",
})

_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
_SAFE_JOB_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,255}$")
_SAFE_ERROR_CODE_RE = re.compile(r"^[A-Za-z0-9_.:-]{1,128}$")


def validate_execution_identity(execution_id: str) -> None:
    """Ensure execution identity matches the dedicated VIDU2 identity exactly."""
    if not execution_id or not isinstance(execution_id, str):
        raise ValueError("VIDU2 STOP: Execution identity must be a non-empty string")
    if execution_id in FORBIDDEN_REUSED_EXECUTION_IDS:
        raise ValueError(
            f"VIDU2 STOP: Execution identity {execution_id!r} reuses a consumed run identity; "
            "a distinct VIDU2 identity is strictly required"
        )
    if "VIDU1" in execution_id:
        raise ValueError(
            f"VIDU2 STOP: Execution identity {execution_id!r} cannot reference consumed VIDU1 run"
        )
    if any(r in execution_id for r in ("R1", "R2", "R3", "R4")):
        raise ValueError(
            f"VIDU2 STOP: Execution identity {execution_id!r} cannot reference R1-R4 historical runs"
        )
    if execution_id != EXPECTED_VIDU2_EXECUTION_ID:
        raise ValueError(
            f"VIDU2 STOP: Execution identity {execution_id!r} does not match expected dedicated identity {EXPECTED_VIDU2_EXECUTION_ID!r}"
        )


def authorization_marker(execution_id: str, git_sha: str) -> str:
    """Generate expected fresh Owner authorization marker."""
    validate_execution_identity(execution_id)
    if not isinstance(git_sha, str) or not _SHA_RE.fullmatch(git_sha):
        raise ValueError(f"VIDU2 STOP: git_sha must be a 40-character lowercase hex string, got {git_sha!r}")
    return f"FRESH_OWNER_AUTHORIZED_VIDU2: {execution_id} @ {git_sha}"


def execution_fence_marker(execution_id: str) -> str:
    """Generate expected one-shot execution fence marker."""
    validate_execution_identity(execution_id)
    return f"EXECUTION_STARTED: {execution_id}"


def terminal_pass_marker(execution_id: str) -> str:
    """Generate terminal pass marker."""
    validate_execution_identity(execution_id)
    return f"VIDU2_PROBE_PASS: {execution_id}"


def terminal_stop_marker(execution_id: str) -> str:
    """Generate terminal stop marker."""
    validate_execution_identity(execution_id)
    return f"VIDU2_PROBE_STOPPED: {execution_id}"


def classify_http_status(status_code: Optional[int]) -> Optional[str]:
    """Map integer HTTP status code to coarse safe classification enum."""
    if not isinstance(status_code, int) or isinstance(status_code, bool):
        return None
    if status_code == 429:
        return "HTTP_RATE_LIMITED"
    if 400 <= status_code <= 499:
        return "HTTP_CLIENT_ERROR"
    if 500 <= status_code <= 599:
        return "HTTP_SERVER_ERROR"
    return None


def sanitize_evidence(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Sanitize raw probe execution state into structured safe evidence."""
    sanitized: Dict[str, Any] = {
        "execution_id": raw.get("execution_id"),
        "provider": TARGET_PROVIDER,
        "model": raw.get("model", TARGET_MODEL),
        "mode": TARGET_MODE,
        "duration_seconds": TARGET_DURATION_SECONDS,
        "resolution": TARGET_RESOLUTION,
        "status": raw.get("status", "UNKNOWN"),
        "generation_posts": raw.get("generation_posts", 0),
        "poll_attempts": raw.get("poll_attempts", 0),
        "provider_job_id": None,
        "provider_status": None,
        "provider_error_code": None,
        "provider_http_status": None,
        "failure_classification": None,
        "provider_credits_reported": raw.get("provider_credits_reported"),
        "vidu_credits_consumed": raw.get("vidu_credits_consumed"),
        "vidu_credits_consumed_confirmed": bool(raw.get("vidu_credits_consumed_confirmed", False)),
        "video_url_present": bool(raw.get("video_url_present", False)),
        "error": None,
        "error_type": None,
        "openai_calls": 0,
        "gemini_calls": 0,
        "elevenlabs_calls": 0,
    }

    job_id = raw.get("provider_job_id")
    if isinstance(job_id, str) and _SAFE_JOB_ID_RE.fullmatch(job_id):
        sanitized["provider_job_id"] = job_id

    p_status = raw.get("provider_status")
    if isinstance(p_status, str) and _SAFE_ERROR_CODE_RE.fullmatch(p_status):
        sanitized["provider_status"] = p_status

    err_code = raw.get("provider_error_code")
    if isinstance(err_code, str) and _SAFE_ERROR_CODE_RE.fullmatch(err_code):
        sanitized["provider_error_code"] = err_code

    http_status = raw.get("provider_http_status")
    if isinstance(http_status, int) and not isinstance(http_status, bool) and 100 <= http_status <= 599:
        sanitized["provider_http_status"] = http_status
        classification = raw.get("failure_classification")
        if classification in ("HTTP_CLIENT_ERROR", "HTTP_RATE_LIMITED", "HTTP_SERVER_ERROR"):
            sanitized["failure_classification"] = classification
        else:
            sanitized["failure_classification"] = classify_http_status(http_status)

    err = raw.get("error")
    if isinstance(err, str):
        sanitized["error"] = err[:255]

    err_t = raw.get("error_type")
    if isinstance(err_t, str):
        sanitized["error_type"] = err_t[:128]

    return sanitized


class Vidu2ProbeRunner:
    """Safe bounded runner for dedicated VIDU2 1-call diagnostic probe."""

    def __init__(
        self,
        execution_id: str = DEFAULT_VIDU2_EXECUTION_ID,
        evidence_dir: Optional[Path] = None,
    ) -> None:
        validate_execution_identity(execution_id)
        self.execution_id = execution_id
        self.evidence_dir = evidence_dir or (REPO_ROOT / "vidu2_evidence")
        self.evidence_file = self.evidence_dir / "vidu2_execution_evidence.json"
        self.generation_post_count = 0

        self.state: Dict[str, Any] = {
            "execution_id": self.execution_id,
            "provider": TARGET_PROVIDER,
            "model": TARGET_MODEL,
            "mode": TARGET_MODE,
            "duration_seconds": TARGET_DURATION_SECONDS,
            "resolution": TARGET_RESOLUTION,
            "status": "INITIALIZED",
            "generation_posts": 0,
            "poll_attempts": 0,
            "provider_job_id": None,
            "provider_status": None,
            "provider_error_code": None,
            "provider_http_status": None,
            "failure_classification": None,
            "provider_credits_reported": None,
            "vidu_credits_consumed": None,
            "vidu_credits_consumed_confirmed": False,
            "video_url_present": False,
            "error": None,
            "error_type": None,
            "openai_calls": 0,
            "gemini_calls": 0,
            "elevenlabs_calls": 0,
        }

    def write_evidence(self) -> None:
        """Persist sanitized evidence atomically to disk."""
        self.evidence_dir.mkdir(parents=True, exist_ok=True)
        sanitized = sanitize_evidence(self.state)
        tmp_path = self.evidence_file.with_suffix(".tmp")
        tmp_path.write_text(json.dumps(sanitized, indent=2), encoding="utf-8")
        tmp_path.replace(self.evidence_file)

    async def execute_probe(
        self,
        adapter: Any,
        max_poll_attempts: int = 15,
        poll_interval_seconds: float = 5.0,
        authorized_main_sha: Optional[str] = None,
        current_sha: Optional[str] = None,
        auth_confirmed: bool = False,
        fence_confirmed: bool = False,
        ref_name: str = "main",
    ) -> Dict[str, Any]:
        """Execute single-call probe under strict fail-closed safety guards."""
        validate_execution_identity(self.execution_id)

        if ref_name != "main":
            self.state["status"] = "STOPPED"
            self.state["error"] = f"INVALID_REF: {ref_name} is not canonical 'main'"
            self.state["error_type"] = "InvalidBranch"
            self.write_evidence()
            raise RuntimeError(f"VIDU2 STOP: Execution must run on canonical 'main' branch, got {ref_name!r}")

        if not auth_confirmed:
            self.state["status"] = "STOPPED"
            self.state["error"] = "MISSING_OWNER_AUTHORIZATION: auth_confirmed is False"
            self.state["error_type"] = "AuthorizationMissing"
            self.write_evidence()
            raise RuntimeError("VIDU2 STOP: Owner live execution authorization is not confirmed")

        if not fence_confirmed:
            self.state["status"] = "STOPPED"
            self.state["error"] = "FENCE_NOT_CONSUMED: fence_confirmed is False"
            self.state["error_type"] = "FenceNotConfirmed"
            self.write_evidence()
            raise RuntimeError("VIDU2 STOP: One-shot execution fence is not confirmed")

        if not authorized_main_sha or not current_sha or authorized_main_sha != current_sha:
            self.state["status"] = "STOPPED"
            self.state["error"] = f"SHA_MISMATCH: authorized={authorized_main_sha} current={current_sha}"
            self.state["error_type"] = "ShaMismatch"
            self.write_evidence()
            raise RuntimeError(
                f"VIDU2 STOP: Execution SHA mismatch: authorized {authorized_main_sha!r} vs current {current_sha!r}"
            )

        if self.generation_post_count >= MAX_GENERATION_POSTS:
            self.state["status"] = "STOPPED"
            self.state["error"] = "GENERATION_POST_CAP_REACHED: strictly 1 POST permitted"
            self.state["error_type"] = "CapExceeded"
            self.write_evidence()
            raise RuntimeError("VIDU2 STOP: Generation POST cap reached; cannot submit additional generation jobs")

        from app.providers.base import VideoGenerationParams

        params = VideoGenerationParams(
            shot_id="shot-vidu2-probe-001",
            prompt=TARGET_PROMPT,
            duration_seconds=TARGET_DURATION_SECONDS,
            aspect_ratio=TARGET_ASPECT_RATIO,
            provider_specific_params={"resolution": TARGET_RESOLUTION},
        )

        self.generation_post_count += 1
        self.state["generation_posts"] = self.generation_post_count
        self.state["status"] = "SUBMITTING"
        self.write_evidence()

        try:
            submission_result = await adapter.submit_generation_job(params)
        except Exception as exc:
            self.state["status"] = "STOPPED"
            self.state["error"] = f"POST_EXCEPTION: {type(exc).__name__}"
            self.state["error_type"] = type(exc).__name__
            self.write_evidence()
            raise RuntimeError(
                f"VIDU2 STOP: Generation POST raised exception {type(exc).__name__}; retry strictly forbidden"
            ) from exc

        uncertain = getattr(submission_result, "submission_uncertain", False)
        if uncertain:
            self.state["status"] = "STOPPED"
            self.state["error"] = "SUBMISSION_UNCERTAIN: transport error after possible POST dispatch"
            self.state["error_type"] = "SubmissionUncertain"
            self.state["provider_status"] = getattr(submission_result, "provider_status", None)
            self.state["provider_error_code"] = (
                getattr(submission_result, "provider_error_code", None)
                or getattr(submission_result, "error_code", None)
            )
            status_code = getattr(submission_result, "status_code", None)
            if isinstance(status_code, int) and not isinstance(status_code, bool) and 100 <= status_code <= 599:
                self.state["provider_http_status"] = status_code
                self.state["failure_classification"] = classify_http_status(status_code)
            self.write_evidence()
            raise RuntimeError(
                "VIDU2 STOP: Ambiguous POST submission outcome; retry strictly forbidden"
            )

        if submission_result.status == "FAILED":
            self.state["status"] = "FAILED"
            self.state["error"] = submission_result.error_code or "PROVIDER_FAILED"
            self.state["provider_status"] = submission_result.provider_status or "failed"
            self.state["provider_error_code"] = submission_result.provider_error_code or submission_result.error_code
            status_code = getattr(submission_result, "status_code", None)
            if isinstance(status_code, int) and not isinstance(status_code, bool) and 100 <= status_code <= 599:
                self.state["provider_http_status"] = status_code
                self.state["failure_classification"] = classify_http_status(status_code)
            if getattr(submission_result, "provider_credits", None) is not None:
                self.state["provider_credits_reported"] = submission_result.provider_credits
            self.write_evidence()
            return sanitize_evidence(self.state)

        # Successful submission: record job ID and start GET polling
        job_id = submission_result.provider_job_id
        if not job_id:
            self.state["status"] = "STOPPED"
            self.state["error"] = "MISSING_JOB_ID: Provider submission succeeded without job_id"
            self.state["error_type"] = "MissingJobId"
            self.write_evidence()
            raise RuntimeError("VIDU2 STOP: No job_id returned after successful submission; cannot poll")

        self.state["provider_job_id"] = job_id
        self.state["provider_status"] = submission_result.provider_status or submission_result.status
        if getattr(submission_result, "provider_credits", None) is not None:
            self.state["provider_credits_reported"] = submission_result.provider_credits

        if submission_result.status == "COMPLETED":
            self.state["status"] = "SUCCESS"
            self.state["video_url_present"] = bool(submission_result.video_url)
            self.write_evidence()
            return sanitize_evidence(self.state)

        # Poll status via GET only
        for attempt in range(1, max_poll_attempts + 1):
            self.state["poll_attempts"] = attempt
            try:
                poll_result = await adapter.check_job_status(job_id)
            except Exception as exc:
                self.state["error"] = f"POLL_EXCEPTION: {type(exc).__name__}"
                await asyncio.sleep(poll_interval_seconds)
                continue

            self.state["provider_status"] = poll_result.provider_status or poll_result.status
            if getattr(poll_result, "provider_credits", None) is not None:
                self.state["provider_credits_reported"] = poll_result.provider_credits

            if poll_result.status == "COMPLETED":
                self.state["status"] = "SUCCESS"
                self.state["video_url_present"] = bool(poll_result.video_url)
                self.state["error"] = None
                self.write_evidence()
                return sanitize_evidence(self.state)

            if poll_result.status in ("FAILED", "CANCELLED"):
                self.state["status"] = poll_result.status
                self.state["provider_error_code"] = poll_result.provider_error_code or poll_result.error_code
                self.state["error"] = poll_result.error_code or f"PROVIDER_{poll_result.status}"
                status_code = getattr(poll_result, "status_code", None)
                if isinstance(status_code, int) and not isinstance(status_code, bool) and 100 <= status_code <= 599:
                    self.state["provider_http_status"] = status_code
                    self.state["failure_classification"] = classify_http_status(status_code)
                self.write_evidence()
                return sanitize_evidence(self.state)

            await asyncio.sleep(poll_interval_seconds)

        # Reached max poll attempts
        self.state["status"] = "STOPPED"
        self.state["error"] = "POLL_TIMEOUT: maximum polling attempts reached without completion"
        self.write_evidence()
        return sanitize_evidence(self.state)


def main() -> int:
    parser = argparse.ArgumentParser(description="WP020 LIVE R5 Vidu2 1-Call Probe")
    parser.add_argument(
        "--mode",
        choices=["dry-run", "live"],
        default="dry-run",
        help="Execution mode (default: dry-run, zero POST calls)",
    )
    args = parser.parse_args()

    execution_id = os.getenv("WP020_VIDU2_EXECUTION_ID", DEFAULT_VIDU2_EXECUTION_ID)
    validate_execution_identity(execution_id)

    evidence_dir = Path("vidu2_evidence")
    runner = Vidu2ProbeRunner(execution_id=execution_id, evidence_dir=evidence_dir)

    if args.mode == "dry-run":
        print(f"VIDU2 DRY-RUN / PREFLIGHT PASS for execution ID {execution_id}")
        runner.state["status"] = "DRY_RUN_PASS"
        runner.write_evidence()
        return 0

    # Live mode checks
    auth_confirmed = os.getenv("VIDU2_OWNER_AUTHORIZATION_CONFIRMED", "").lower() == "true"
    fence_confirmed = os.getenv("EXECUTION_FENCE_CONFIRMED", "").lower() == "true"
    authorized_main_sha = os.getenv("AUTHORIZED_MAIN_SHA", "")
    current_sha = os.getenv("CURRENT_EXECUTION_SHA", "")
    ref_name = os.getenv("GITHUB_REF_NAME", "main")

    from app.providers.vidu import ViduProviderAdapter

    api_key = os.getenv("VIDU_API_KEY")
    if not api_key:
        print("STOP: VIDU_API_KEY environment variable is missing in live mode", file=sys.stderr)
        return 1

    adapter = ViduProviderAdapter(api_key=api_key)

    try:
        asyncio.run(
            runner.execute_probe(
                adapter=adapter,
                authorized_main_sha=authorized_main_sha,
                current_sha=current_sha,
                auth_confirmed=auth_confirmed,
                fence_confirmed=fence_confirmed,
                ref_name=ref_name,
            )
        )
    except Exception as exc:
        print(f"VIDU2 live execution halted: {exc}", file=sys.stderr)
        return 1

    final_status = runner.state.get("status")
    return 0 if final_status == "SUCCESS" else 1


if __name__ == "__main__":
    sys.exit(main())
