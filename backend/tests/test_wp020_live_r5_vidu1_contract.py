from __future__ import annotations

import ast
import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / ".github" / "scripts" / "wp020_live_r5_vidu1.py"
WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "wp020-live-r5-vidu1.yml"
VALID_SHA = "5a818b9dbf642b1e456dba51c9a80745d966919e"


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
    assert 'TARGET_RESOLUTION = "720p"' in source


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
    """E. only fully valid mocked live permit can reach exactly one mocked POST with 720p."""
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

    # Corrective 3: exact resolution 720p
    assert result["resolution"] == "720p"

    # Verify adapter submission params: exact 720p resolution
    assert mock_adapter.submit_generation_job.await_count == 1
    called_params = mock_adapter.submit_generation_job.call_args[0][0]
    assert called_params.provider_specific_params == {"resolution": "720p"}
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
        "resolution": "720p",
        "status": "SUCCESS",
        "generation_posts": 1,
        "poll_attempts": 2,
        "provider_job_id": "vidu-task-999",
        "provider_status": "success",
        "provider_error_code": None,
        "provider_http_status": 200,
        "failure_classification": None,
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
    assert sanitized["resolution"] == "720p"
    assert sanitized["provider_http_status"] == 200
    assert sanitized["failure_classification"] is None
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


# =========================================================================
# Static Provenance Regression Tests (COR1 authorization identity)
# =========================================================================

# These constants are static truth — must NOT be interchangeable.
COR1_AUTH_COMMENT = "5604486823"
PRIOR_PAID_VIDU1_AUTH_COMMENT = "5603798466"
PRIOR_PAID_VIDU1_MARKER_SHA = "42d789efdb49725b1dd45b312ce39cb71ac02d1e"


def test_cor1_provenance_comment_ids_are_distinct():
    """COR1 NO-PAID authorization comment and prior paid VIDU1 authorization comment
    are distinct issue comments and MUST NOT be interchangeable."""
    assert COR1_AUTH_COMMENT != PRIOR_PAID_VIDU1_AUTH_COMMENT, (
        "COR1 NO-PAID auth (5604486823) and prior paid VIDU1 auth (5603798466) "
        "must be distinct — they are different Issue #63 comments."
    )


def test_cor1_auth_comment_authorizes_no_paid_work_only():
    """5604486823 authorizes only the NO-PAID COR1 corrective.
    It is NOT the paid VIDU1 authorization marker."""
    # The COR1 auth comment ID must match the expected constant
    assert COR1_AUTH_COMMENT == "5604486823"
    # The prior paid VIDU1 marker comment ID must be different
    assert COR1_AUTH_COMMENT != PRIOR_PAID_VIDU1_AUTH_COMMENT


def test_prior_paid_vidu1_marker_comment_is_distinct():
    """5603798466 is the prior paid VIDU1 marker comment.
    It contains FRESH_OWNER_AUTHORIZED_VIDU1: LIVE-20260909-VIDU1-R5 @ 42d789ef...
    This marker is bound to SHA 42d789efdb49725b1dd45b312ce39cb71ac02d1e and
    MUST NOT be reused after COR1 (PR #93) merges to main."""
    assert PRIOR_PAID_VIDU1_AUTH_COMMENT == "5603798466"
    assert PRIOR_PAID_VIDU1_MARKER_SHA == "42d789efdb49725b1dd45b312ce39cb71ac02d1e"
    # The paid marker comment must differ from the COR1 auth comment
    assert PRIOR_PAID_VIDU1_AUTH_COMMENT != COR1_AUTH_COMMENT


def test_cor1_delivery_doc_does_not_attribute_paid_marker_to_cor1_auth_comment():
    """Delivery doc P4_WP020_LIVE_R5_VIDU1_COR1.md must not attribute
    FRESH_OWNER_AUTHORIZED_VIDU1 paid marker text to COR1 auth comment 5604486823.
    That is: the FRESH_OWNER_AUTHORIZED_VIDU1 marker text and 5604486823 must not
    appear on the SAME LINE, because they have different meanings."""
    cor1_doc_path = REPO_ROOT / "project-docs" / "40_DELIVERY" / "P4_WP020_LIVE_R5_VIDU1_COR1.md"
    assert cor1_doc_path.is_file(), f"Missing {cor1_doc_path}"
    content = cor1_doc_path.read_text(encoding="utf-8")

    # Verify correct provenance: 5604486823 is used only as COR1 NO-PAID auth
    assert COR1_AUTH_COMMENT in content, "COR1 auth comment must be present in delivery doc"

    # Verify prior paid marker comment is correctly referenced
    assert PRIOR_PAID_VIDU1_AUTH_COMMENT in content, (
        "Prior paid VIDU1 auth comment 5603798466 must be present in delivery doc"
    )

    # Critical: FRESH_OWNER_AUTHORIZED_VIDU1 paid marker text must NOT appear on the
    # SAME line as COR1 auth comment 5604486823. They may appear in the same document
    # section (as a two-bullet clarification list), but the marker text itself must
    # only be attributed to comment 5603798466.
    lines = content.splitlines()
    for i, line in enumerate(lines):
        if "FRESH_OWNER_AUTHORIZED_VIDU1" in line and COR1_AUTH_COMMENT in line:
            raise AssertionError(
                f"FRESH_OWNER_AUTHORIZED_VIDU1 paid marker must NOT be on the same line "
                f"as COR1 auth comment {COR1_AUTH_COMMENT}. "
                f"Line {i+1}: {line}"
            )


# =========================================================================
# Diagnostic & Contract Tests for P4-WP020-LIVE-R5-VIDU1-C1 (Items 1 to 10)
# =========================================================================

def test_c1_classify_http_status_logic():
    """Unit test for classify_http_status mapping."""
    mod = _load_script_module()
    classify = mod.classify_http_status

    assert classify(400) == "HTTP_CLIENT_ERROR"
    assert classify(401) == "HTTP_CLIENT_ERROR"
    assert classify(403) == "HTTP_CLIENT_ERROR"
    assert classify(404) == "HTTP_CLIENT_ERROR"
    assert classify(422) == "HTTP_CLIENT_ERROR"
    assert classify(429) == "HTTP_RATE_LIMITED"
    assert classify(500) == "HTTP_SERVER_ERROR"
    assert classify(502) == "HTTP_SERVER_ERROR"
    assert classify(503) == "HTTP_SERVER_ERROR"
    assert classify(504) == "HTTP_SERVER_ERROR"

    # Non-error or invalid status codes return None
    assert classify(200) is None
    assert classify(201) is None
    assert classify(None) is None
    assert classify("400") is None
    assert classify(True) is None
    assert classify(99) is None
    assert classify(600) is None


def test_c1_http_400_mocked_response(tmp_path):
    """1. HTTP 400 mocked response:
    - status = FAILED
    - error_code = HTTP_ERROR
    - provider HTTP status preserved as 400
    - failure_classification = HTTP_CLIENT_ERROR
    - submission_uncertain = false
    """
    mod = _load_script_module()
    from app.providers.base import ProviderJobResult

    mock_adapter = MagicMock()
    mock_adapter.submit_generation_job = AsyncMock(return_value=ProviderJobResult(
        provider_job_id="",
        status="FAILED",
        error_code="HTTP_ERROR",
        status_code=400,
        submission_uncertain=False,
    ))

    runner = mod.Vidu1ProbeRunner(evidence_dir=tmp_path)
    result = asyncio.run(runner.execute_probe(
        adapter=mock_adapter,
        authorized_main_sha=VALID_SHA,
        current_sha=VALID_SHA,
        auth_confirmed=True,
        fence_confirmed=True,
        ref_name="main",
    ))

    assert result["status"] == "FAILED"
    assert result["error"] == "HTTP_ERROR"
    assert result["provider_http_status"] == 400
    assert result["failure_classification"] == "HTTP_CLIENT_ERROR"
    assert runner.generation_post_count == 1
    assert mock_adapter.submit_generation_job.await_count == 1


def test_c1_http_401_403_mocked_response(tmp_path):
    """2. HTTP 401/403 mocked response:
    - status code preserved
    - failure_classification = HTTP_CLIENT_ERROR
    - no secret/raw body exposed
    """
    mod = _load_script_module()
    from app.providers.base import ProviderJobResult

    for code in (401, 403):
        evidence_dir = tmp_path / f"evidence_{code}"
        mock_adapter = MagicMock()
        mock_adapter.submit_generation_job = AsyncMock(return_value=ProviderJobResult(
            provider_job_id="",
            status="FAILED",
            error_code="HTTP_ERROR",
            status_code=code,
            submission_uncertain=False,
        ))

        runner = mod.Vidu1ProbeRunner(evidence_dir=evidence_dir)
        result = asyncio.run(runner.execute_probe(
            adapter=mock_adapter,
            authorized_main_sha=VALID_SHA,
            current_sha=VALID_SHA,
            auth_confirmed=True,
            fence_confirmed=True,
            ref_name="main",
        ))

        assert result["status"] == "FAILED"
        assert result["provider_http_status"] == code
        assert result["failure_classification"] == "HTTP_CLIENT_ERROR"
        assert "secret" not in result
        assert "api_key" not in result
        assert "Authorization" not in result

        evidence_file = evidence_dir / "vidu1_execution_evidence.json"
        assert evidence_file.is_file()
        file_text = evidence_file.read_text(encoding="utf-8")
        assert "api_key" not in file_text
        assert "Token" not in file_text
        assert "raw_response" not in file_text


def test_c1_http_429_mocked_response_no_auto_retry(tmp_path):
    """3. HTTP 429 mocked response:
    - status code preserved as 429
    - failure_classification = HTTP_RATE_LIMITED
    - retryable metadata may remain true
    - VIDU1 probe MUST NOT automatically retry generation POST (cap = 1)
    """
    mod = _load_script_module()
    from app.providers.base import ProviderJobResult

    mock_adapter = MagicMock()
    mock_adapter.submit_generation_job = AsyncMock(return_value=ProviderJobResult(
        provider_job_id="",
        status="FAILED",
        error_code="HTTP_ERROR",
        status_code=429,
        retryable=True,
        submission_uncertain=False,
    ))

    runner = mod.Vidu1ProbeRunner(evidence_dir=tmp_path)
    result = asyncio.run(runner.execute_probe(
        adapter=mock_adapter,
        authorized_main_sha=VALID_SHA,
        current_sha=VALID_SHA,
        auth_confirmed=True,
        fence_confirmed=True,
        ref_name="main",
    ))

    assert result["status"] == "FAILED"
    assert result["provider_http_status"] == 429
    assert result["failure_classification"] == "HTTP_RATE_LIMITED"
    assert runner.generation_post_count == 1
    assert mock_adapter.submit_generation_job.await_count == 1


def test_c1_http_500_mocked_response_fail_closed_without_retry(tmp_path):
    """4. HTTP 500 mocked response:
    - status preserved as 500 in evidence
    - failure_classification = HTTP_SERVER_ERROR
    - submission uncertainty / fail-closed behavior preserved
    - absolutely no blind POST retry
    """
    mod = _load_script_module()
    from app.providers.base import ProviderJobResult

    mock_adapter = MagicMock()
    mock_adapter.submit_generation_job = AsyncMock(return_value=ProviderJobResult(
        provider_job_id="",
        status="FAILED",
        error_code="HTTP_ERROR",
        status_code=500,
        retryable=True,
        submission_uncertain=True,
    ))

    runner = mod.Vidu1ProbeRunner(evidence_dir=tmp_path)
    with pytest.raises(RuntimeError, match="Ambiguous POST submission outcome"):
        asyncio.run(runner.execute_probe(
            adapter=mock_adapter,
            authorized_main_sha=VALID_SHA,
            current_sha=VALID_SHA,
            auth_confirmed=True,
            fence_confirmed=True,
            ref_name="main",
        ))

    assert runner.generation_post_count == 1
    assert mock_adapter.submit_generation_job.await_count == 1

    evidence_file = tmp_path / "vidu1_execution_evidence.json"
    assert evidence_file.is_file()
    data = json.loads(evidence_file.read_text(encoding="utf-8"))
    assert data["status"] == "STOPPED"
    assert data["provider_http_status"] == 500
    assert data["failure_classification"] == "HTTP_SERVER_ERROR"


def test_c1_request_contract_payload_headers_and_path():
    """5, 6, 7. Request contract verification using mock HTTP transport:
    - Exactly one mocked POST target: /text2video
    - Payload contains model=viduq2, duration=4, aspect_ratio=16:9, resolution=720p
    - Authorization scheme is Token <api_key> (Token prefix verified, real secret never exposed)
    - Content-Type is application/json
    """
    import httpx
    from unittest.mock import patch
    from app.providers.vidu import ViduProviderAdapter
    from app.providers.base import VideoGenerationParams

    captured_requests = []

    def mock_handler(request: httpx.Request) -> httpx.Response:
        captured_requests.append(request)
        return httpx.Response(
            status_code=200,
            json={
                "task_id": "vidu-task-mock-123",
                "state": "queueing",
                "credits": 4.0,
            },
        )

    transport = httpx.MockTransport(mock_handler)
    adapter = ViduProviderAdapter(
        api_key="test-mock-api-key",
        base_url="https://api.vidu.com/ent/v2",
        model="viduq2",
    )

    params = VideoGenerationParams(
        shot_id="shot-vidu1-probe",
        prompt="Cinematic slow aerial shot of calm turquoise ocean waves breaking on a golden sand beach at dawn, soft warm morning lighting, photorealistic, 4k",
        aspect_ratio="16:9",
        duration_seconds=4.0,
        provider_specific_params={"resolution": "720p"},
    )

    original_init = httpx.AsyncClient.__init__

    def patched_init(client_self, *args, **kwargs):
        kwargs["transport"] = transport
        original_init(client_self, *args, **kwargs)

    with patch.object(httpx.AsyncClient, "__init__", patched_init):
        result = asyncio.run(adapter.submit_generation_job(params))

    assert result.status == "QUEUED"
    assert len(captured_requests) == 1

    req = captured_requests[0]
    # 5. Method and Path
    assert req.method == "POST"
    assert req.url.path == "/ent/v2/text2video"
    assert str(req.url) == "https://api.vidu.com/ent/v2/text2video"

    # 6. Payload field names and values
    body = json.loads(req.content.decode("utf-8"))
    assert body["model"] == "viduq2"
    assert body["duration"] == 4
    assert body["aspect_ratio"] == "16:9"
    assert body["resolution"] == "720p"
    assert body["prompt"] == params.prompt

    # 7. Authorization scheme: Token
    auth_header = req.headers.get("Authorization")
    assert auth_header is not None
    assert auth_header.startswith("Token ")
    assert auth_header == "Token test-mock-api-key"
    assert req.headers.get("Content-Type") == "application/json"


def test_c1_vidu_adapter_resolution_normalization_and_validation():
    """Verify ViduProviderAdapter normalizes resolution casing to lowercase
    and validates supported values without broad refactoring."""
    import httpx
    from unittest.mock import patch
    from app.providers.vidu import ViduProviderAdapter
    from app.providers.base import VideoGenerationParams

    for input_res, expected_res in [
        ("720p", "720p"),
        ("720P", "720p"),
        ("1080P", "1080p"),
        ("540P", "540p"),
    ]:
        captured = []

        def mock_handler(request: httpx.Request) -> httpx.Response:
            captured.append(request)
            return httpx.Response(status_code=200, json={"task_id": "t1", "state": "queueing"})

        transport = httpx.MockTransport(mock_handler)
        adapter = ViduProviderAdapter(api_key="key", base_url="https://api.vidu.com/ent/v2", model="viduq2")
        params = VideoGenerationParams(
            shot_id="s1",
            prompt="valid prompt",
            duration_seconds=4.0,
            provider_specific_params={"resolution": input_res},
        )

        original_init = httpx.AsyncClient.__init__

        def patched_init(client_self, *args, **kwargs):
            kwargs["transport"] = transport
            original_init(client_self, *args, **kwargs)

        with patch.object(httpx.AsyncClient, "__init__", patched_init):
            result = asyncio.run(adapter.submit_generation_job(params))

        assert result.status == "QUEUED"
        body = json.loads(captured[0].content.decode("utf-8"))
        assert body["resolution"] == expected_res

    # Unsupported resolutions fail closed with INVALID_PARAMETERS
    adapter = ViduProviderAdapter(api_key="key", base_url="https://api.vidu.com/ent/v2", model="viduq2")
    for bad_res in ["4K", "unsupported", 720]:
        bad_params = VideoGenerationParams(
            shot_id="s1",
            prompt="valid prompt",
            duration_seconds=4.0,
            provider_specific_params={"resolution": bad_res},
        )
        result = asyncio.run(adapter.submit_generation_job(bad_params))
        assert result.status == "FAILED"
        assert result.error_code == "INVALID_PARAMETERS"


def test_c1_sanitized_evidence_safety_exclusions():
    """8. Sanitized evidence excludes raw response body, response headers,
    API key, Authorization value, and unsafe provider messages."""
    mod = _load_script_module()

    raw_state = {
        "execution_id": "LIVE-20260909-VIDU1-R5",
        "provider": "vidu",
        "model": "viduq2",
        "mode": "text-to-video",
        "duration_seconds": 4.0,
        "resolution": "720p",
        "status": "FAILED",
        "generation_posts": 1,
        "poll_attempts": 0,
        "provider_job_id": None,
        "provider_status": "failed",
        "provider_error_code": "HTTP_ERROR",
        "provider_http_status": 400,
        "failure_classification": "HTTP_CLIENT_ERROR",
        "provider_credits_reported": None,
        "vidu_credits_consumed": None,
        "vidu_credits_consumed_confirmed": False,
        "video_url_present": False,
        "error": "HTTP_ERROR",
        "error_type": None,
        "openai_calls": 0,
        "gemini_calls": 0,
        "elevenlabs_calls": 0,
        # Unsafe fields that must be stripped
        "raw_response": {"message": "Invalid prompt formatting", "error_details": "sensitive"},
        "response_headers": {"x-request-id": "req-123", "set-cookie": "secret-cookie"},
        "api_key": "PRIVATE_KEY_VALUE",
        "Authorization": "Token PRIVATE_KEY_VALUE",
        "secret_token": "BEARER_SECRET",
        "usd": 0.15,
    }

    sanitized = mod.sanitize_evidence(raw_state)

    # Exclusions
    assert "raw_response" not in sanitized
    assert "response_headers" not in sanitized
    assert "api_key" not in sanitized
    assert "Authorization" not in sanitized
    assert "secret_token" not in sanitized
    assert "usd" not in sanitized

    # Preserved safe fields
    assert sanitized["provider_http_status"] == 400
    assert sanitized["failure_classification"] == "HTTP_CLIENT_ERROR"
    assert sanitized["vidu_credits_consumed"] is None
    assert sanitized["vidu_credits_consumed_confirmed"] is False

    # Out of range or invalid types sanitize to None
    bad_status_state = {"provider_http_status": 999, "failure_classification": "INVALID_CLASS"}
    sanitized_bad = mod.sanitize_evidence(bad_status_state)
    assert sanitized_bad["provider_http_status"] is None
    assert sanitized_bad["failure_classification"] is None

    bool_status_state = {"provider_http_status": True, "failure_classification": True}
    sanitized_bool = mod.sanitize_evidence(bool_status_state)
    assert sanitized_bool["provider_http_status"] is None
    assert sanitized_bool["failure_classification"] is None


def test_c1_generation_post_cap_and_no_other_providers():
    """9 & 10. Generation POST cap remains MAX_GENERATION_POSTS = 1,
    and OpenAI/Gemini/ElevenLabs are not invoked."""
    source = SCRIPT_PATH.read_text(encoding="utf-8")
    assert "MAX_GENERATION_POSTS = 1" in source

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
