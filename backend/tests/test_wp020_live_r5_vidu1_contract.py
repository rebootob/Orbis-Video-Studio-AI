from __future__ import annotations

import ast
import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / ".github" / "scripts" / "wp020_live_r5_vidu1.py"
WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "wp020-live-r5-vidu1.yml"
VALID_SHA = "42d789efdb49725b1dd45b312ce39cb71ac02d1e"


def _load_script_module():
    import importlib.util

    spec = importlib.util.spec_from_file_location("wp020_live_r5_vidu1", SCRIPT_PATH)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_vidu1_script_ast_and_syntax():
    assert SCRIPT_PATH.is_file(), f"Missing {SCRIPT_PATH}"
    source = SCRIPT_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    assert tree is not None
    assert 'TARGET_RESOLUTION = "720P"' in source


def test_vidu1_workflow_safety_and_structure():
    assert WORKFLOW_PATH.is_file(), f"Missing {WORKFLOW_PATH}"
    content = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert "workflow_dispatch:" in content
    assert "\n  push:" not in content
    assert "\n  pull_request:" not in content
    assert "wp020-live-r5-vidu1-probe" in content
    assert "WP020 LIVE R5 Vidu 1-Call Probe" in content
    assert "FRESH_OWNER_AUTHORIZED_VIDU1:" in content
    assert "EXECUTION_STARTED:" in content
    assert "VIDU1_PROBE_PASS:" in content
    assert "VIDU1_PROBE_STOPPED:" in content
    assert 'VIDU1_OWNER_AUTHORIZATION_CONFIRMED=true' in content
    assert 'EXECUTION_FENCE_CONFIRMED=true' in content


def test_forbidden_provider_calls_absent():
    source = SCRIPT_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    called_attrs = {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }
    forbidden = {
        "generate_story",
        "generate_image",
        "generate_audio",
        "call_openai",
        "call_gemini",
        "call_elevenlabs",
    }
    assert called_attrs.isdisjoint(forbidden)


def test_execution_identity_validation():
    mod = _load_script_module()

    # Valid VIDU1 identity passes
    mod.validate_execution_identity("LIVE-20260909-VIDU1-R5")

    # Historical identities fail closed
    for historical in (
        "LIVE-20260909-DE17-R4",
        "LIVE-20260909-363F-R3",
        "LIVE-20260908-468E-R2",
        "LIVE-20260908-B023-R1",
    ):
        with pytest.raises(ValueError, match="reuses a consumed run identity"):
            mod.validate_execution_identity(historical)

    # Any R1-R4 reference fails closed
    with pytest.raises(ValueError, match="cannot reference R1-R4"):
        mod.validate_execution_identity("LIVE-20260909-R4-PROBE")

    # Non-historical wrong identities must fail closed
    for non_historical in (
        "LIVE-20260909-VIDU2-R5",
        "LIVE-20260909-VIDU1-R6",
        "LIVE-20260909-OTHER-R5",
        "LIVE-20260910-VIDU1-R5",
        "arbitrary-identity",
    ):
        with pytest.raises(ValueError, match="does not match expected dedicated identity"):
            mod.validate_execution_identity(non_historical)


def test_authorization_and_markers():
    mod = _load_script_module()

    auth = mod.authorization_marker("LIVE-20260909-VIDU1-R5", VALID_SHA)
    assert auth == f"FRESH_OWNER_AUTHORIZED_VIDU1: LIVE-20260909-VIDU1-R5 @ {VALID_SHA}"

    fence = mod.execution_fence_marker("LIVE-20260909-VIDU1-R5")
    assert fence == "EXECUTION_STARTED: LIVE-20260909-VIDU1-R5"

    with pytest.raises(ValueError, match="40-character"):
        mod.authorization_marker("LIVE-20260909-VIDU1-R5", "invalid-sha")


# =========================================================================
# Behavioral Tests for Runner-Side Paid Safety Boundary (Corrective 1)
# =========================================================================

def test_live_guard_a_direct_live_invocation_without_authorization(tmp_path):
    """A. direct live invocation without authorization -> STOP, zero adapter submit calls."""
    mod = _load_script_module()
    mock_adapter = MagicMock()
    mock_adapter.submit_generation_job = AsyncMock()

    runner = mod.Vidu1ProbeRunner(evidence_dir=tmp_path)

    async def _run():
        await runner.execute_probe(
            adapter=mock_adapter,
            auth_confirmed=False,
            fence_confirmed=False,
        )

    with pytest.raises(RuntimeError, match="Owner live execution authorization is not confirmed"):
        asyncio.run(_run())

    assert mock_adapter.submit_generation_job.await_count == 0
    assert runner.generation_post_count == 0
    assert runner.state["status"] == "STOPPED"


def test_live_guard_b_auth_true_but_fence_false(tmp_path):
    """B. auth true but fence false -> STOP, zero POST."""
    mod = _load_script_module()
    mock_adapter = MagicMock()
    mock_adapter.submit_generation_job = AsyncMock()

    runner = mod.Vidu1ProbeRunner(evidence_dir=tmp_path)

    async def _run():
        await runner.execute_probe(
            adapter=mock_adapter,
            authorized_main_sha=VALID_SHA,
            current_sha=VALID_SHA,
            auth_confirmed=True,
            fence_confirmed=False,
        )

    with pytest.raises(RuntimeError, match="One-shot execution fence is not confirmed"):
        asyncio.run(_run())

    assert mock_adapter.submit_generation_job.await_count == 0
    assert runner.generation_post_count == 0
    assert runner.state["status"] == "STOPPED"


def test_live_guard_c_sha_mismatch(tmp_path):
    """C. SHA mismatch -> STOP, zero POST."""
    mod = _load_script_module()
    mock_adapter = MagicMock()
    mock_adapter.submit_generation_job = AsyncMock()

    runner = mod.Vidu1ProbeRunner(evidence_dir=tmp_path)

    async def _run():
        await runner.execute_probe(
            adapter=mock_adapter,
            authorized_main_sha=VALID_SHA,
            current_sha="a" * 40,
            auth_confirmed=True,
            fence_confirmed=True,
        )

    with pytest.raises(RuntimeError, match="Execution SHA mismatch"):
        asyncio.run(_run())

    assert mock_adapter.submit_generation_job.await_count == 0
    assert runner.generation_post_count == 0
    assert runner.state["status"] == "STOPPED"


def test_live_guard_d_wrong_execution_id(tmp_path):
    """D. wrong execution ID -> STOP, zero POST."""
    mod = _load_script_module()

    # Reused historical R4 identity rejected at runner instantiation
    with pytest.raises(ValueError, match="reuses a consumed run identity"):
        mod.Vidu1ProbeRunner(execution_id="LIVE-20260909-DE17-R4", evidence_dir=tmp_path)

    # Non-historical wrong identity rejected at runner instantiation
    with pytest.raises(ValueError, match="does not match expected dedicated identity"):
        mod.Vidu1ProbeRunner(execution_id="LIVE-20260909-VIDU2-R5", evidence_dir=tmp_path)


def test_live_guard_non_historical_wrong_identity_with_valid_permit_stopped(tmp_path):
    """Behavioral test: NON-HISTORICAL wrong identity (LIVE-20260909-VIDU2-R5)
    with otherwise valid auth/fence/SHA/main MUST STOP before adapter call with:
    - execution rejected
    - generation_post_count == 0
    - submit_generation_job.await_count == 0
    """
    mod = _load_script_module()
    mock_adapter = MagicMock()
    mock_adapter.submit_generation_job = AsyncMock()

    runner = mod.Vidu1ProbeRunner(evidence_dir=tmp_path)
    # Mutate execution ID on runner to simulate non-historical wrong identity
    runner.execution_id = "LIVE-20260909-VIDU2-R5"

    async def _run():
        await runner.execute_probe(
            adapter=mock_adapter,
            authorized_main_sha=VALID_SHA,
            current_sha=VALID_SHA,
            auth_confirmed=True,
            fence_confirmed=True,
            ref_name="main",
        )

    with pytest.raises(ValueError, match="does not match expected dedicated identity"):
        asyncio.run(_run())

    assert mock_adapter.submit_generation_job.await_count == 0
    assert runner.generation_post_count == 0
    assert runner.state["status"] == "STOPPED"


def test_live_guard_branch_mismatch(tmp_path):
    """Execution on non-main branch -> STOP, zero POST."""
    mod = _load_script_module()
    mock_adapter = MagicMock()
    mock_adapter.submit_generation_job = AsyncMock()

    runner = mod.Vidu1ProbeRunner(evidence_dir=tmp_path)

    async def _run():
        await runner.execute_probe(
            adapter=mock_adapter,
            authorized_main_sha=VALID_SHA,
            current_sha=VALID_SHA,
            auth_confirmed=True,
            fence_confirmed=True,
            ref_name="feature/unauthorized",
        )

    with pytest.raises(RuntimeError, match="Execution must run on canonical 'main' branch"):
        asyncio.run(_run())

    assert mock_adapter.submit_generation_job.await_count == 0
    assert runner.generation_post_count == 0
    assert runner.state["status"] == "STOPPED"


# =========================================================================
# Behavioral Tests for Single-Call Execution & Resolution Contract (E & 2 & 3)
# =========================================================================

def test_live_guard_e_mocked_success_with_valid_permit_and_exact_resolution(tmp_path):
    """E. only fully valid mocked live permit can reach exactly one mocked POST with 720P."""
    mod = _load_script_module()
    from app.providers.base import ProviderJobResult

    mock_adapter = MagicMock()
    # 1. submit returns QUEUED with provider_credits
    mock_adapter.submit_generation_job = AsyncMock(return_value=ProviderJobResult(
        provider_job_id="vidu-task-123",
        status="QUEUED",
        provider_status="queued",
        provider_credits=4.0,
    ))
    # 2. check_status returns COMPLETED
    mock_adapter.check_job_status = AsyncMock(return_value=ProviderJobResult(
        provider_job_id="vidu-task-123",
        status="COMPLETED",
        provider_status="success",
        video_url="https://example.com/video.mp4",
        provider_credits=4.0,
    ))

    runner = mod.Vidu1ProbeRunner(evidence_dir=tmp_path)

    async def _run():
        return await runner.execute_probe(
            adapter=mock_adapter,
            max_poll_attempts=3,
            poll_interval_seconds=0.01,
            authorized_main_sha=VALID_SHA,
            current_sha=VALID_SHA,
            auth_confirmed=True,
            fence_confirmed=True,
            ref_name="main",
        )

    result = asyncio.run(_run())

    # Verify execution outcome
    assert result["status"] == "SUCCESS"
    assert result["generation_posts"] == 1
    assert result["provider_job_id"] == "vidu-task-123"

    # Corrective 2: provider_credits_reported is preserved, but NOT equated to credits_consumed
    assert result["provider_credits_reported"] == 4.0
    assert result["vidu_credits_consumed"] is None
    assert result["vidu_credits_consumed_confirmed"] is False

    # Corrective 3: exact resolution 720P
    assert result["resolution"] == "720P"

    # Verify adapter submission params: exact 720P resolution
    assert mock_adapter.submit_generation_job.await_count == 1
    called_params = mock_adapter.submit_generation_job.call_args[0][0]
    assert called_params.provider_specific_params == {"resolution": "720P"}
    assert called_params.duration_seconds == 4.0
    assert called_params.aspect_ratio == "16:9"

    # Polling calls are GET only
    assert mock_adapter.check_job_status.await_count >= 1

    # Attempting second POST must fail closed
    with pytest.raises(RuntimeError, match="Generation POST cap reached"):
        asyncio.run(runner.execute_probe(
            adapter=mock_adapter,
            authorized_main_sha=VALID_SHA,
            current_sha=VALID_SHA,
            auth_confirmed=True,
            fence_confirmed=True,
            ref_name="main",
        ))


def test_vidu1_ambiguous_post_fails_closed_without_retry(tmp_path):
    mod = _load_script_module()
    from app.providers.base import ProviderJobResult

    mock_adapter = MagicMock()
    # Uncertain transport failure on POST
    mock_adapter.submit_generation_job = AsyncMock(return_value=ProviderJobResult(
        provider_job_id="",
        status="FAILED",
        error_code="TRANSPORT_ERROR",
        submission_uncertain=True,
    ))

    runner = mod.Vidu1ProbeRunner(evidence_dir=tmp_path)

    async def _run():
        await runner.execute_probe(
            adapter=mock_adapter,
            authorized_main_sha=VALID_SHA,
            current_sha=VALID_SHA,
            auth_confirmed=True,
            fence_confirmed=True,
            ref_name="main",
        )

    with pytest.raises(RuntimeError, match="Ambiguous POST submission outcome"):
        asyncio.run(_run())

    # Exactly 1 POST made; zero blind retry
    assert mock_adapter.submit_generation_job.await_count == 1
    evidence_file = tmp_path / "vidu1_execution_evidence.json"
    assert evidence_file.is_file()
    data = mod.json.loads(evidence_file.read_text(encoding="utf-8"))
    assert data["status"] == "STOPPED"
    assert "SUBMISSION_UNCERTAIN" in data["error"]
    assert data["generation_posts"] == 1


def test_evidence_sanitization():
    mod = _load_script_module()

    raw_state = {
        "execution_id": "LIVE-20260909-VIDU1-R5",
        "provider": "vidu",
        "model": "viduq2",
        "mode": "text-to-video",
        "duration_seconds": 4.0,
        "resolution": "720P",
        "status": "SUCCESS",
        "generation_posts": 1,
        "poll_attempts": 2,
        "provider_job_id": "vidu-task-999",
        "provider_status": "success",
        "provider_error_code": None,
        "provider_credits_reported": 4.0,
        "vidu_credits_consumed": None,
        "vidu_credits_consumed_confirmed": False,
        "video_url_present": True,
        "secret_token": "SUPER_SECRET_BEARER_TOKEN",
        "api_key": "PRIVATE_KEY_VALUE",
        "raw_response": {"secret": "data"},
        "openai_calls": 0,
        "gemini_calls": 0,
        "elevenlabs_calls": 0,
    }

    sanitized = mod.sanitize_evidence(raw_state)
    assert "secret_token" not in sanitized
    assert "api_key" not in sanitized
    assert "raw_response" not in sanitized
    assert sanitized["resolution"] == "720P"
    assert sanitized["provider_credits_reported"] == 4.0
    assert sanitized["vidu_credits_consumed"] is None
    assert sanitized["vidu_credits_consumed_confirmed"] is False
    assert "usd" not in sanitized  # No credits-to-USD conversion


# =========================================================================
# Behavioral & Contract Tests for P4-WP020-LIVE-R5-VIDU1-COR1 (Tests A through H)
# =========================================================================

def test_cor1_workflow_no_incompatible_gh_comments_flags():
    """A. Workflow no longer contains incompatible --comments + --json flags."""
    content = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert "--comments --json" not in content
    assert "--comments" not in content or "gh issue view" not in content
    assert "gh issue view" not in content


def test_cor1_workflow_uses_gh_api_paginate():
    """B. Comment retrieval uses gh api --paginate with exact repository issues comments endpoint."""
    content = WORKFLOW_PATH.read_text(encoding="utf-8")
    expected_api_cmd = 'COMMENTS="$(gh api --paginate "repos/${GITHUB_REPOSITORY}/issues/${ISSUE_NUMBER}/comments" --jq \'.[].body\')"'
    assert expected_api_cmd in content


def test_cor1_workflow_pagination_preserved():
    """C. Pagination is preserved explicitly via --paginate."""
    content = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert "--paginate" in content
    assert 'repos/${GITHUB_REPOSITORY}/issues/${ISSUE_NUMBER}/comments' in content


def test_cor1_workflow_exact_owner_authorization_marker_required():
    """D. Exact Owner authorization marker is required and checked with grep -Fx."""
    content = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert 'AUTH_MARKER="FRESH_OWNER_AUTHORIZED_VIDU1: ${WP020_VIDU1_EXECUTION_ID} @ ${GITHUB_SHA}"' in content
    assert 'grep -Fx "${AUTH_MARKER}"' in content
    assert 'echo "STOP: exact fresh Owner VIDU1 paid authorization marker missing for current main"' in content


def test_cor1_workflow_existing_fence_blocks_execution():
    """E. Existing fence marker blocks execution fail-closed."""
    content = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert 'FENCE_MARKER="EXECUTION_STARTED: ${WP020_VIDU1_EXECUTION_ID}"' in content
    assert 'if printf \'%s\\n\' "${COMMENTS}" | grep -Fx "${FENCE_MARKER}" >/dev/null; then' in content
    assert 'echo "STOP: VIDU1 one-shot execution fence already consumed"' in content


def test_cor1_workflow_terminal_markers_block_execution():
    """F. Existing terminal PASS/STOP markers block execution fail-closed."""
    content = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert 'TERMINAL_PASS="VIDU1_PROBE_PASS: ${WP020_VIDU1_EXECUTION_ID}"' in content
    assert 'TERMINAL_STOP="VIDU1_PROBE_STOPPED: ${WP020_VIDU1_EXECUTION_ID}"' in content
    assert 'grep -F "${TERMINAL_PASS}"' in content
    assert 'grep -F "${TERMINAL_STOP}"' in content


def test_cor1_workflow_empty_or_failed_comment_retrieval_fails_closed():
    """G. Missing or empty comment retrieval fails closed immediately."""
    content = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert 'if [ -z "${COMMENTS}" ]; then' in content
    assert 'echo "STOP: failed to retrieve Issue #${ISSUE_NUMBER} comments or comment list is empty" >&2' in content
    assert 'exit 1' in content


def test_cor1_workflow_preserves_safety_invariants():
    """H. Preserves max generation POST = 1, exact execution identity, SHA binding, branch guard, no automatic generation retry, ambiguous POST => STOP."""
    content = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert "WP020_VIDU1_EXECUTION_ID: LIVE-20260909-VIDU1-R5" in content
    assert f"CANONICAL_BASE_SHA: {VALID_SHA}" in content
    assert 'if [ "$GITHUB_REF_NAME" != "main" ]; then' in content
    assert "workflow_dispatch:" in content

    # Check script safety invariants
    script_content = SCRIPT_PATH.read_text(encoding="utf-8")
    assert "MAX_GENERATION_POSTS = 1" in script_content
    assert "EXPECTED_VIDU1_EXECUTION_ID = \"LIVE-20260909-VIDU1-R5\"" in script_content
    assert "submission_uncertain" in script_content
    assert "Ambiguous POST submission outcome" in script_content


def test_cor1_comment_parsing_simulation():
    """Simulation of the workflow shell guard comment parsing logic."""
    target_marker = f"FRESH_OWNER_AUTHORIZED_VIDU1: LIVE-20260909-VIDU1-R5 @ {VALID_SHA}"
    fence_marker = "EXECUTION_STARTED: LIVE-20260909-VIDU1-R5"
    pass_marker = "VIDU1_PROBE_PASS: LIVE-20260909-VIDU1-R5"
    stop_marker = "VIDU1_PROBE_STOPPED: LIVE-20260909-VIDU1-R5"

    def evaluate_comments(comments: list[str]) -> str:
        if not comments:
            return "STOP_EMPTY"
        if target_marker not in comments:
            return "STOP_MISSING_AUTH"
        if fence_marker in comments:
            return "STOP_FENCE_CONSUMED"
        if pass_marker in comments:
            return "STOP_TERMINAL_PASS"
        if stop_marker in comments:
            return "STOP_TERMINAL_STOP"
        return "AUTHORIZED"

    # Case 1: Empty comments -> STOP_EMPTY
    assert evaluate_comments([]) == "STOP_EMPTY"

    # Case 2: Missing auth -> STOP_MISSING_AUTH
    assert evaluate_comments(["Some comment", "Another comment"]) == "STOP_MISSING_AUTH"

    # Case 3: Valid fresh auth -> AUTHORIZED
    assert evaluate_comments(["Some comment", target_marker]) == "AUTHORIZED"

    # Case 4: Auth present but fence already consumed -> STOP_FENCE_CONSUMED
    assert evaluate_comments(["Some comment", target_marker, fence_marker]) == "STOP_FENCE_CONSUMED"

    # Case 5: Auth present but already passed -> STOP_TERMINAL_PASS
    assert evaluate_comments([target_marker, pass_marker]) == "STOP_TERMINAL_PASS"

    # Case 6: Auth present but already stopped -> STOP_TERMINAL_STOP
    assert evaluate_comments([target_marker, stop_marker]) == "STOP_TERMINAL_STOP"

