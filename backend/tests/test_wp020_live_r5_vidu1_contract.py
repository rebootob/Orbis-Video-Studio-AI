from __future__ import annotations

import ast
import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / ".github" / "scripts" / "wp020_live_r5_vidu1.py"
WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "wp020-live-r5-vidu1.yml"


def test_vidu1_script_ast_and_syntax():
    assert SCRIPT_PATH.is_file(), f"Missing {SCRIPT_PATH}"
    source = SCRIPT_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    assert tree is not None


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
    import importlib.util

    spec = importlib.util.spec_from_file_location("wp020_live_r5_vidu1", SCRIPT_PATH)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    # Valid VIDU1 identity passes
    mod.validate_execution_identity("LIVE-20260909-VIDU1-R5")

    # Historical identities fail closed
    for historical in ("LIVE-20260909-DE17-R4", "LIVE-20260909-363F-R3", "LIVE-20260908-468E-R2", "LIVE-20260908-B023-R1"):
        with pytest.raises(ValueError, match="reuses a consumed run identity"):
            mod.validate_execution_identity(historical)

    # Any R1-R4 reference fails closed
    with pytest.raises(ValueError, match="cannot reference R1-R4"):
        mod.validate_execution_identity("LIVE-20260909-R4-PROBE")


def test_authorization_and_markers():
    import importlib.util

    spec = importlib.util.spec_from_file_location("wp020_live_r5_vidu1", SCRIPT_PATH)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    sha = "5107e3e9ef7702c8403fe74146062ab68e8e50b9"
    auth = mod.authorization_marker("LIVE-20260909-VIDU1-R5", sha)
    assert auth == f"FRESH_OWNER_AUTHORIZED_VIDU1: LIVE-20260909-VIDU1-R5 @ {sha}"

    fence = mod.execution_fence_marker("LIVE-20260909-VIDU1-R5")
    assert fence == "EXECUTION_STARTED: LIVE-20260909-VIDU1-R5"

    with pytest.raises(ValueError, match="40-character"):
        mod.authorization_marker("LIVE-20260909-VIDU1-R5", "invalid-sha")


def test_vidu1_mocked_success_single_post_and_polling(tmp_path):
    import importlib.util
    from app.providers.base import ProviderJobResult

    spec = importlib.util.spec_from_file_location("wp020_live_r5_vidu1", SCRIPT_PATH)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    mock_adapter = MagicMock()
    # 1. submit returns QUEUED
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
        )

    result = asyncio.run(_run())

    assert result["status"] == "SUCCESS"
    assert result["generation_posts"] == 1
    assert result["provider_job_id"] == "vidu-task-123"
    assert result["provider_credits"] == 4.0
    assert result["credits_consumed"] == 4.0
    assert result["video_url_present"] is True
    assert result["openai_calls"] == 0
    assert result["gemini_calls"] == 0
    assert result["elevenlabs_calls"] == 0

    # Ensure exactly 1 POST was made
    assert mock_adapter.submit_generation_job.await_count == 1
    # Check status GET was called
    assert mock_adapter.check_job_status.await_count >= 1

    # Attempting second POST must fail closed
    with pytest.raises(RuntimeError, match="Generation POST cap reached"):
        asyncio.run(runner.execute_probe(adapter=mock_adapter))


def test_vidu1_ambiguous_post_fails_closed_without_retry(tmp_path):
    import importlib.util
    from app.providers.base import ProviderJobResult

    spec = importlib.util.spec_from_file_location("wp020_live_r5_vidu1", SCRIPT_PATH)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    mock_adapter = MagicMock()
    # Uncertain transport failure on POST
    mock_adapter.submit_generation_job = AsyncMock(return_value=ProviderJobResult(
        provider_job_id="",
        status="FAILED",
        error_code="TRANSPORT_ERROR",
        submission_uncertain=True,
    ))

    runner = mod.Vidu1ProbeRunner(evidence_dir=tmp_path)
    with pytest.raises(RuntimeError, match="Ambiguous POST submission outcome"):
        asyncio.run(runner.execute_probe(adapter=mock_adapter))

    # Exactly 1 POST made; no blind retry
    assert mock_adapter.submit_generation_job.await_count == 1
    evidence_file = tmp_path / "vidu1_execution_evidence.json"
    assert evidence_file.is_file()
    data = mod.json.loads(evidence_file.read_text(encoding="utf-8"))
    assert data["status"] == "STOPPED"
    assert "SUBMISSION_UNCERTAIN" in data["error"]
    assert data["generation_posts"] == 1


def test_evidence_sanitization():
    import importlib.util

    spec = importlib.util.spec_from_file_location("wp020_live_r5_vidu1", SCRIPT_PATH)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

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
        "provider_credits": 4.0,
        "credits_consumed": 4.0,
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
    assert sanitized["provider_credits"] == 4.0
    assert sanitized["credits_consumed"] == 4.0
    assert "usd" not in sanitized  # No credits-to-USD conversion
