"""P4-WP020-LIVE R2 launcher for the reviewed bounded provider UAT runner.

The underlying R1 runner logic is retained byte-for-byte as an immutable snapshot.
This launcher changes only the one-shot execution identity and authorized runtime
main SHA after verifying the snapshot Git blob SHA and the runtime fence inputs.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path

R2_EXECUTION_ID = "LIVE-20260909-BB75-R2"
R1_EXECUTION_ID = "LIVE-20260908-B023-R1"
R1_AUTHORIZED_MAIN_SHA = "b0233729e1882267123c863d98df861c50a66a3b"
EXPECTED_R1_SNAPSHOT_GIT_BLOB_SHA = "7a34b21b8e72c4d8ef49efc56a23feef4476d82c"
SNAPSHOT = Path(__file__).with_name("wp020_live_uat_r1_snapshot.py")


def _git_blob_sha(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode("utf-8")
    return hashlib.sha1(header + data).hexdigest()  # nosec B324 - Git object identity only


def main() -> None:
    execution_id = os.environ.get("WP020_LIVE_EXECUTION_ID", "")
    authorized_main_sha = os.environ.get("AUTHORIZED_MAIN_SHA", "")
    github_sha = os.environ.get("GITHUB_SHA", "")
    fence_confirmed = os.environ.get("EXECUTION_FENCE_CONFIRMED", "")

    if execution_id != R2_EXECUTION_ID:
        raise RuntimeError("Unexpected R2 LIVE execution id")
    if not github_sha or authorized_main_sha != github_sha:
        raise RuntimeError("R2 authorized main SHA must exactly equal workflow GITHUB_SHA")
    if fence_confirmed != "true":
        raise RuntimeError("R2 execution fence not confirmed")

    snapshot_bytes = SNAPSHOT.read_bytes()
    if _git_blob_sha(snapshot_bytes) != EXPECTED_R1_SNAPSHOT_GIT_BLOB_SHA:
        raise RuntimeError("R1 runner snapshot integrity mismatch")

    source = snapshot_bytes.decode("utf-8")
    old_id_literal = f'"{R1_EXECUTION_ID}"'
    old_sha_literal = f'"{R1_AUTHORIZED_MAIN_SHA}"'
    if source.count(old_id_literal) != 1:
        raise RuntimeError("R1 execution-id guard occurrence drift")
    if source.count(old_sha_literal) != 1:
        raise RuntimeError("R1 authorized-main guard occurrence drift")

    source = source.replace(old_id_literal, f'"{R2_EXECUTION_ID}"', 1)
    source = source.replace(old_sha_literal, f'"{authorized_main_sha}"', 1)

    namespace = {
        "__name__": "__main__",
        "__file__": str(SNAPSHOT),
        "__package__": None,
    }
    exec(compile(source, str(SNAPSHOT), "exec"), namespace, namespace)


if __name__ == "__main__":
    main()
