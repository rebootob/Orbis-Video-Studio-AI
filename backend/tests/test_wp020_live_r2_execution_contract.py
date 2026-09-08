from __future__ import annotations

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github/workflows/wp020-live-execution-r2.yml"
LAUNCHER = ROOT / ".github/scripts/wp020_live_uat_r2.py"
SNAPSHOT = ROOT / ".github/scripts/wp020_live_uat_r1_snapshot.py"

R2_EXECUTION_ID = "LIVE-20260909-BB75-R2"
R1_EXECUTION_ID = "LIVE-20260908-B023-R1"
R1_AUTHORIZED_MAIN_SHA = "b0233729e1882267123c863d98df861c50a66a3b"
R1_SNAPSHOT_GIT_BLOB_SHA = "7a34b21b8e72c4d8ef49efc56a23feef4476d82c"


def _git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(f"blob {len(data)}\0".encode("utf-8") + data).hexdigest()


def test_r2_workflow_is_manual_only_and_owner_fenced() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    trigger_section = text.split("permissions:", 1)[0]

    assert "workflow_dispatch:" in trigger_section
    assert "push:" not in trigger_section
    assert "pull_request:" not in trigger_section
    assert "contents: read" in text
    assert "issues: write" in text
    assert "cancel-in-progress: false" in text
    assert "GITHUB_EVENT_NAME" in text
    assert "GITHUB_REF_NAME" in text and '!= "main"' in text
    assert R2_EXECUTION_ID in text
    assert "bb75c8087428cb14a57a3557b9013f5472f976bf" in text
    assert "FRESH_OWNER_AUTHORIZED_R2:" in text
    assert "wp020_live_r2_preflight.py" in text
    assert "wp020_live_uat_r2.py" in text
    assert "wp020_live_uat_r1_snapshot.py" not in text

    fence_write = 'gh issue comment "$ISSUE_NUMBER" --body "EXECUTION_STARTED: $WP020_LIVE_EXECUTION_ID"'
    assert fence_write in text
    assert text.index("wp020_live_r2_preflight.py") < text.index(fence_write)
    assert text.index(fence_write) < text.index("wp020_live_uat_r2.py")


def test_r2_launcher_binds_identity_and_exact_runtime_main() -> None:
    text = LAUNCHER.read_text(encoding="utf-8")

    assert f'R2_EXECUTION_ID = "{R2_EXECUTION_ID}"' in text
    assert f'R1_EXECUTION_ID = "{R1_EXECUTION_ID}"' in text
    assert f'R1_AUTHORIZED_MAIN_SHA = "{R1_AUTHORIZED_MAIN_SHA}"' in text
    assert f'EXPECTED_R1_SNAPSHOT_GIT_BLOB_SHA = "{R1_SNAPSHOT_GIT_BLOB_SHA}"' in text
    assert 'authorized_main_sha != github_sha' in text
    assert 'fence_confirmed != "true"' in text
    assert "source.count(old_id_literal) != 1" in text
    assert "source.count(old_sha_literal) != 1" in text


def test_r1_runner_snapshot_is_immutable_and_contract_bounded() -> None:
    assert _git_blob_sha(SNAPSHOT) == R1_SNAPSHOT_GIT_BLOB_SHA

    text = SNAPSHOT.read_text(encoding="utf-8")
    assert text.count(f'"{R1_EXECUTION_ID}"') == 1
    assert text.count(f'"{R1_AUTHORIZED_MAIN_SHA}"') == 1
    assert R2_EXECUTION_ID not in text
    assert "HARD_CAP_USD = 1.00" in text
    assert "MAX_PAID_CALLS = 6" in text
    assert '_consume_paid_call("OPENAI_CREATIVE_STORY:gpt-4o")' in text
    assert '_consume_paid_call("GEMINI_IMAGE:gemini-3.1-flash-image:1K")' in text
    assert '_consume_paid_call("VIDU_VIDEO:viduq2:text2video:4s:720p")' in text
    assert "ELEVENLABS_TTS:Thai:<=150chars" in text
    assert "ELEVENLABS_MUSIC:<=10s" in text
    assert "ELEVENLABS_AMBIENCE:<=3s" in text
