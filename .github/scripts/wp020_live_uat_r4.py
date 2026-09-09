"""P4-WP020-LIVE R4 bounded one-shot provider UAT runner.

R4 deliberately reuses the exact independently-reviewed R3 runner implementation
without source rewriting. This adapter fails closed unless the frozen R3 runner
still has the expected Git blob SHA, then rebinds only its contract globals to
the immutable R4 contract before invoking it.

No provider I/O occurs at import/bind time. Actual provider calls are possible
only when this file is invoked by the separately Owner-authorized paid workflow
after the R4 fence has been consumed.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path

import wp020_live_r4_contract as r4_contract

EXPECTED_R3_RUNNER_GIT_BLOB_SHA = "24150cdece623004443e03ceecea10490955822b"


def _git_blob_sha(path: Path) -> str:
    content = path.read_bytes()
    header = f"blob {len(content)}\0".encode("utf-8")
    return hashlib.sha1(header + content).hexdigest()


def _require_frozen_r3_runner() -> Path:
    path = Path(__file__).with_name("wp020_live_uat_r3.py")
    actual = _git_blob_sha(path)
    if actual != EXPECTED_R3_RUNNER_GIT_BLOB_SHA:
        raise RuntimeError(
            "R4 STOP: inherited R3 runner blob drifted; independent review is required before paid execution"
        )
    return path


def _bind_r4_contract(base) -> None:
    """Rebind the frozen implementation to R4 identity and fail-closed guards."""
    base.R3_EXECUTION_ID = r4_contract.R4_EXECUTION_ID
    base.HARD_CAP_USD = r4_contract.HARD_CAP_USD
    base.MAX_PAID_CALLS = r4_contract.MAX_PAID_CALLS
    base.PAID_CALL_SEQUENCE = r4_contract.PAID_CALL_SEQUENCE
    base.enforce_budget = r4_contract.enforce_budget
    base.next_paid_call = r4_contract.next_paid_call
    base.require_provider_success = r4_contract.require_provider_success
    base.sanitize_audio_clip = r4_contract.sanitize_audio_clip
    base.sanitize_generation_job = r4_contract.sanitize_generation_job
    base.validate_runtime_binding = r4_contract.validate_runtime_binding


def main() -> None:
    if os.environ.get("WP020_LIVE_EXECUTION_ID") != r4_contract.R4_EXECUTION_ID:
        raise RuntimeError("R4 STOP: unexpected LIVE execution identity")

    _require_frozen_r3_runner()

    # Import only after the immutable source guard has passed. The base module has
    # no provider side effect at import time; provider calls occur only inside run().
    import wp020_live_uat_r3 as base

    _bind_r4_contract(base)
    try:
        base.run()
    except Exception as exc:
        # Imported modules do not execute the R3 __main__ exception block. Preserve
        # the same sanitized/durable STOP semantics explicitly for R4.
        base.state["status"] = "STOPPED"
        base.state["error"] = base._redact(str(exc))
        base.state["error_type"] = type(exc).__name__
        base._capture_durable_failure_evidence()
        base._write_evidence()
        raise


if __name__ == "__main__":
    main()
