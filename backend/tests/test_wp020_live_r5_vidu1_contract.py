from __future__ import annotations

import ast
import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / ".github" / "scripts" / "wp020_live_r5_vidu1.py"
WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "wp020-live-r5-vidu1.yml"
VALID_SHA = "5107e3e9ef7702c8403fe74146062ab68e8e50b9"


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
