"""P4-WP020-LIVE-R5-VIDU1 Dedicated 1-Call Vidu Probe Runner.

Strictly bounded tooling for a single-call Vidu generation probe.
NO provider generation calls or credit consumption occur during PREP.
Future execution requires separate explicit Owner authorization and dedicated fence.

Safety invariants:
- Provider: Vidu only (viduq2, text2video, 4s, 720p)
- Max generation POST: exactly 1 (hard capped; ambiguous transport fails closed without retry)
- GET polling only after confirmed submission
- OpenAI / Gemini / ElevenLabs calls = 0
- Never reuses consumed R4 / R3 / R2 / R1 execution identities
- Sanitized evidence only; no raw response bodies, secrets, or credits-to-USD conversion
"""
from __future__ import annotations

import argparse
import asyncio
import json
import math
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, Optional

# Root and configuration constants
REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_VIDU1_EXECUTION_ID = "LIVE-20260909-VIDU1-R5"
ISSUE_NUMBER = 63
MAX_GENERATION_POSTS = 1

TARGET_PROVIDER = "vidu"
TARGET_MODEL = "viduq2"
TARGET_MODE = "text-to-video"
TARGET_DURATION_SECONDS = 4.0
TARGET_RESOLUTION = "720p"
TARGET_PROMPT = "Cinematic slow aerial shot of calm turquoise ocean waves breaking on a golden sand beach at dawn, soft warm morning lighting, photorealistic, 4k"

FORBIDDEN_REUSED_EXECUTION_IDS = frozenset({
    "LIVE-20260909-DE17-R4",
    "LIVE-20260909-363F-R3",
    "LIVE-20260908-468E-R2",
    "LIVE-20260908-B023-R1",
})

_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
_SAFE_JOB_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,255}$")
_SAFE_ERROR_CODE_RE = re.compile(r"^[A-Za-z0-9_.:-]{1,128}$")


def validate_execution_identity(execution_id: str) -> None:
    """Ensure execution identity is valid and not reusing consumed live runs."""
    if not execution_id or not isinstance(execution_id, str):
        raise ValueError("VIDU1 STOP: Execution identity must be a non-empty string")
    if execution_id in FORBIDDEN_REUSED_EXECUTION_IDS:
        raise ValueError(
            f"VIDU1 STOP: Execution identity {execution_id!r} reuses a consumed run identity; "
            "a distinct VIDU1 identity is strictly required"
        )
    if "R4" in execution_id or "R3" in execution_id or "R2" in execution_id or "R1" in execution_id:
        raise ValueError(
            f"VIDU1 STOP: Execution identity {execution_id!r} cannot reference R1-R4 historical runs"
        )


def authorization_marker(execution_id: str, main_sha: str) -> str:
    """Format exact Owner authorization marker required before paid execution."""
    if not _SHA_RE.fullmatch(main_sha or ""):
        raise ValueError("VIDU1 authorization requires an exact 40-character lowercase main SHA")
    return f"FRESH_OWNER_AUTHORIZED_VIDU1: {execution_id} @ {main_sha}"


def execution_fence_marker(execution_id: str) -> str:
    return f"EXECUTION_STARTED: {execution_id}"


def terminal_pass_marker(execution_id: str) -> str:
    return f"VIDU1_PROBE_PASS: {execution_id}"


def terminal_stop_marker(execution_id: str) -> str:
    return f"VIDU1_PROBE_STOPPED: {execution_id}"


def sanitize_evidence(state: Dict[str, Any]) -> Dict[str, Any]:
    """Return only safe, non-sensitive metadata for public evidence."""
    safe_fields = [
        "execution_id",
        "provider",
        "model",
        "mode",
        "duration_seconds",
        "resolution",
        "status",
        "generation_posts",
        "poll_attempts",
        "provider_job_id",
        "provider_status",
        "provider_error_code",
        "provider_credits",
        "credits_consumed",
        "video_url_present",
        "error",
        "error_type",
        "openai_calls",
        "gemini_calls",
        "elevenlabs_calls",
    ]
    sanitized: Dict[str, Any] = {}
    for key in safe_fields:
        val = state.get(key)
        if key == "provider_credits" or key == "credits_consumed":
            if val is not None and isinstance(val, (int, float)) and math.isfinite(val):
                sanitized[key] = float(val)
            else:
                sanitized[key] = None
        elif key == "provider_error_code":
            if val is not None and _SAFE_ERROR_CODE_RE.fullmatch(str(val)):
                sanitized[key] = str(val)
            else:
                sanitized[key] = None if val is None else "REDACTED_ERROR_CODE"
        elif key == "provider_job_id":
            if val is not None and _SAFE_JOB_ID_RE.fullmatch(str(val)):
                sanitized[key] = str(val)
            else:
                sanitized[key] = None if val is None else "REDACTED_JOB_ID"
        elif key in ("error", "error_type"):
            sanitized[key] = str(val)[:200] if val is not None else None
        else:
            sanitized[key] = val
    return sanitized


class Vidu1ProbeRunner:
    """Manages the bounded single-call Vidu probe execution lifecycle."""

    def __init__(
        self,
        execution_id: str = DEFAULT_VIDU1_EXECUTION_ID,
        evidence_dir: Optional[Path] = None,
    ) -> None:
        validate_execution_identity(execution_id)
        self.execution_id = execution_id
        self.evidence_dir = evidence_dir or (REPO_ROOT / "vidu1_evidence")
        self.generation_post_count = 0
        self.state: Dict[str, Any] = {
            "execution_id": execution_id,
            "provider": TARGET_PROVIDER,
            "model": TARGET_MODEL,
            "mode": TARGET_MODE,
            "duration_seconds": TARGET_DURATION_SECONDS,
            "resolution": TARGET_RESOLUTION,
            "status": "NOT_STARTED",
            "generation_posts": 0,
            "poll_attempts": 0,
            "provider_job_id": None,
            "provider_status": None,
            "provider_error_code": None,
            "provider_credits": None,
            "credits_consumed": None,
            "video_url_present": False,
            "error": None,
            "error_type": None,
            "openai_calls": 0,
            "gemini_calls": 0,
            "elevenlabs_calls": 0,
        }

    def write_evidence(self) -> Path:
        self.evidence_dir.mkdir(parents=True, exist_ok=True)
        evidence_file = self.evidence_dir / "vidu1_execution_evidence.json"
        sanitized = sanitize_evidence(self.state)
        evidence_file.write_text(json.dumps(sanitized, indent=2), encoding="utf-8")
        return evidence_file

    def run_preflight_check(self) -> Dict[str, Any]:
        """Validate config and environment without making any provider calls."""
        # Ensure backend is in path
        backend_dir = REPO_ROOT / "backend"
        if str(backend_dir) not in sys.path:
            sys.path.insert(0, str(backend_dir))

        from app.providers.vidu import ViduProviderAdapter
        from app.core.config import settings

        api_key = settings.VIDU_API_KEY
        if not api_key:
            raise RuntimeError("VIDU1 PREFLIGHT: VIDU_API_KEY secret is not configured")

        adapter = ViduProviderAdapter(model=TARGET_MODEL)
        if not adapter.validate_config({}):
            raise RuntimeError("VIDU1 PREFLIGHT: ViduProviderAdapter configuration validation failed")

        self.state["status"] = "PREFLIGHT_PASS"
        self.state["generation_posts"] = 0
        self.write_evidence()
        return sanitize_evidence(self.state)

    async def execute_probe(
        self,
        *,
        adapter: Any = None,
        max_poll_attempts: int = 30,
        poll_interval_seconds: float = 10.0,
    ) -> Dict[str, Any]:
        """Execute exactly one generation POST, followed by GET polling only."""
        if self.generation_post_count >= MAX_GENERATION_POSTS:
            raise RuntimeError(
                f"VIDU1 STOP: Generation POST cap reached ({self.generation_post_count}/{MAX_GENERATION_POSTS})"
            )

        # Import backend if adapter not injected
        if adapter is None:
            backend_dir = REPO_ROOT / "backend"
            if str(backend_dir) not in sys.path:
                sys.path.insert(0, str(backend_dir))
            from app.providers.vidu import ViduProviderAdapter
            adapter = ViduProviderAdapter(model=TARGET_MODEL)

        from app.providers.base import VideoGenerationParams

        params = VideoGenerationParams(
            shot_id="shot-vidu1-probe",
            prompt=TARGET_PROMPT,
            aspect_ratio="16:9",
            duration_seconds=TARGET_DURATION_SECONDS,
            provider_specific_params={"resolution": TARGET_RESOLUTION},
        )

        # HARD FENCE: Exactly one POST
        self.generation_post_count += 1
        self.state["generation_posts"] = self.generation_post_count

        try:
            submission_result = await adapter.submit_generation_job(params)
        except Exception as exc:
            self.state["status"] = "STOPPED"
            self.state["error"] = f"UNEXPECTED_POST_EXCEPTION: {type(exc).__name__}"
            self.state["error_type"] = type(exc).__name__
            self.write_evidence()
            raise RuntimeError(
                "VIDU1 STOP: POST exception raised; blind retry forbidden"
            ) from exc

        # Ambiguous transport outcome MUST STOP immediately and must never blind retry
        if submission_result.submission_uncertain:
            self.state["status"] = "STOPPED"
            self.state["error"] = "SUBMISSION_UNCERTAIN: transport error after POST; retry strictly forbidden"
            self.state["error_type"] = "SubmissionUncertain"
            self.state["provider_status"] = submission_result.provider_status
            self.state["provider_error_code"] = submission_result.provider_error_code or submission_result.error_code
            self.write_evidence()
            raise RuntimeError(
                "VIDU1 STOP: Ambiguous POST submission outcome; retry strictly forbidden"
            )

        if submission_result.status == "FAILED":
            self.state["status"] = "FAILED"
            self.state["error"] = submission_result.error_code or "PROVIDER_FAILED"
            self.state["provider_status"] = submission_result.provider_status or "failed"
            self.state["provider_error_code"] = submission_result.provider_error_code or submission_result.error_code
            self.state["provider_credits"] = submission_result.provider_credits
            self.state["credits_consumed"] = submission_result.provider_credits
            self.write_evidence()
            return sanitize_evidence(self.state)

        # Successful submission: record job ID and start GET polling
        job_id = submission_result.provider_job_id
        self.state["provider_job_id"] = job_id
        self.state["provider_status"] = submission_result.provider_status or submission_result.status
        if submission_result.provider_credits is not None:
            self.state["provider_credits"] = submission_result.provider_credits
            self.state["credits_consumed"] = submission_result.provider_credits

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
                # Transient GET poll error: record and continue unless terminal
                self.state["error"] = f"POLL_EXCEPTION: {type(exc).__name__}"
                await asyncio.sleep(poll_interval_seconds)
                continue

            self.state["provider_status"] = poll_result.provider_status or poll_result.status
            if poll_result.provider_credits is not None:
                self.state["provider_credits"] = poll_result.provider_credits
                self.state["credits_consumed"] = poll_result.provider_credits

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
                self.write_evidence()
                return sanitize_evidence(self.state)

            await asyncio.sleep(poll_interval_seconds)

        # Reached max poll attempts
        self.state["status"] = "STOPPED"
        self.state["error"] = "POLL_TIMEOUT: maximum polling attempts reached without completion"
        self.write_evidence()
        return sanitize_evidence(self.state)


def main() -> None:
    parser = argparse.ArgumentParser(description="P4-WP020-LIVE-R5-VIDU1 Probe Runner")
    parser.add_argument(
        "--mode",
        choices=["preflight", "dry-run", "live"],
        default="dry-run",
        help="Execution mode (default: dry-run)",
    )
    parser.add_argument(
        "--execution-id",
        default=os.environ.get("WP020_VIDU1_EXECUTION_ID", DEFAULT_VIDU1_EXECUTION_ID),
        help="One-time execution identity for VIDU1",
    )
    args = parser.parse_args()

    runner = Vidu1ProbeRunner(execution_id=args.execution_id)

    if args.mode in ("preflight", "dry-run"):
        print(f"=== VIDU1 NO-PAID PREFLIGHT / DRY-RUN: {args.execution_id} ===")
        evidence = runner.run_preflight_check()
        print(json.dumps(evidence, indent=2))
        print("PREFLIGHT SUCCESS: Zero provider generation calls made.")
        return

    # Live execution: strictly gated
    print(f"=== VIDU1 PAID PROBE EXECUTION: {args.execution_id} ===")
    evidence = asyncio.run(runner.execute_probe())
    print(json.dumps(evidence, indent=2))
    if evidence.get("status") == "SUCCESS":
        print("VIDU1 PROBE SUCCESS")
    else:
        print(f"VIDU1 PROBE TERMINAL STATE: {evidence.get('status')}")
        sys.exit(1)


if __name__ == "__main__":
    main()
