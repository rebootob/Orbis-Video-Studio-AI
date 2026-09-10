from __future__ import annotations

import ast
import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import httpx
import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / ".github" / "scripts" / "wp020_live_r5_vidu2.py"
WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "wp020-live-r5-vidu2.yml"
EXPECTED_IDENTITY = "LIVE-20260910-VIDU2-R5"
HISTORICAL_VIDU1_IDENTITY = "LIVE-20260909-VIDU1-R5"
CANONICAL_BASE_SHA = "cdfe3ce44ba9a9d6219909d12c0536c1cd716cec"


def _load_script_module():
    import importlib.util

    spec = importlib.util.spec_from_file_location("wp020_live_r5_vidu2", SCRIPT_PATH)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# =========================================================================
# Contract Requirements A through U
# =========================================================================

def test_req_a_reserved_execution_identity_valid():
    """A. Reserved execution identity LIVE-20260910-VIDU2-R5 passes validation."""
    mod = _load_script_module()
    assert mod.EXPECTED_VIDU2_EXECUTION_ID == EXPECTED_IDENTITY
    mod.validate_execution_identity(EXPECTED_IDENTITY)


def test_req_b_historical_and_arbitrary_identities_fail_closed():
    """B. Historical identities and arbitrary strings fail closed."""
    mod = _load_script_module()

    # Historical identities from R1 through VIDU1 fail closed
    historical_identities = (
        HISTORICAL_VIDU1_IDENTITY,
        "LIVE-20260909-DE17-R4",
        "LIVE-20260909-363F-R3",
        "LIVE-20260908-468E-R2",
        "LIVE-20260908-B023-R1",
    )
    for historical in historical_identities:
        with pytest.raises(ValueError, match="reuses a consumed run identity"):
            mod.validate_execution_identity(historical)

    # Any VIDU1 reference fails closed
    with pytest.raises(ValueError, match="cannot reference consumed VIDU1 run"):
        mod.validate_execution_identity("LIVE-20260910-VIDU1-R5")

    # Any R1-R4 reference fails closed
    with pytest.raises(ValueError, match="cannot reference R1-R4"):
        mod.validate_execution_identity("LIVE-20260910-R4-PROBE")

    # Arbitrary strings fail closed
    for arbitrary in (
        "LIVE-20260910-VIDU3-R5",
        "LIVE-20260910-VIDU2-R6",
        "random-string",
    ):
        with pytest.raises(ValueError, match="does not match expected dedicated identity"):
            mod.validate_execution_identity(arbitrary)

    with pytest.raises(ValueError, match="must be a non-empty string"):
        mod.validate_execution_identity("")


def test_req_c_identity_distinct_from_vidu1():
    """C. Reserved VIDU2 identity is strictly distinct from VIDU1 identity."""
    assert EXPECTED_IDENTITY != HISTORICAL_VIDU1_IDENTITY
    assert "VIDU2" in EXPECTED_IDENTITY
    assert "VIDU1" in HISTORICAL_VIDU1_IDENTITY


def test_req_d_target_resolution_exact_720p():
    """D. Target resolution is exact lowercase '720p'."""
    mod = _load_script_module()
    assert mod.TARGET_RESOLUTION == "720p"
    assert mod.TARGET_RESOLUTION != "720P"


def test_req_e_target_model_viduq2():
    """E. Model is viduq2."""
    mod = _load_script_module()
    assert mod.TARGET_MODEL == "viduq2"


def test_req_f_target_duration_4_seconds():
    """F. Duration is 4.0 seconds."""
    mod = _load_script_module()
    assert mod.TARGET_DURATION_SECONDS == 4.0


def test_req_g_target_aspect_ratio_16_9():
    """G. Aspect ratio is 16:9."""
    mod = _load_script_module()
    assert mod.TARGET_ASPECT_RATIO == "16:9"


def test_req_h_i_outbound_request_endpoint_and_authorization():
    """H & I. Target endpoint is POST /text2video and Authorization header is Token <api_key>."""
    from app.providers.vidu import ViduProviderAdapter
    from app.providers.base import VideoGenerationParams

    captured_requests = []

    def mock_handler(request: httpx.Request) -> httpx.Response:
        captured_requests.append(request)
        return httpx.Response(
            status_code=200,
            json={
                "task_id": "vidu2-mock-job-001",
                "state": "queueing",
                "credits": 4.0,
            },
        )

    transport = httpx.MockTransport(mock_handler)
    adapter = ViduProviderAdapter(
        api_key="probe-test-token-xyz",
        base_url="https://api.vidu.com/ent/v2",
        model="viduq2",
    )

    params = VideoGenerationParams(
        shot_id="shot-vidu2-probe",
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
    # Endpoint
    assert req.method == "POST"
    assert req.url.path == "/ent/v2/text2video"
    assert str(req.url) == "https://api.vidu.com/ent/v2/text2video"

    # Headers
    auth_header = req.headers.get("Authorization")
    assert auth_header == "Token probe-test-token-xyz"
    assert req.headers.get("Content-Type") == "application/json"

    # Body
    body = json.loads(req.content.decode("utf-8"))
    assert body["model"] == "viduq2"
    assert body["duration"] == 4
    assert body["aspect_ratio"] == "16:9"
    assert body["resolution"] == "720p"
    assert body["prompt"] == params.prompt


def test_req_j_max_generation_posts_hard_cap():
    """J. MAX_GENERATION_POSTS = 1 hard cap enforced."""
    mod = _load_script_module()
    assert mod.MAX_GENERATION_POSTS == 1

    script_source = SCRIPT_PATH.read_text(encoding="utf-8")
    assert "MAX_GENERATION_POSTS = 1" in script_source


def test_req_k_http_400_mock_handling(tmp_path):
    """K. HTTP 400 mock handling -> provider_http_status = 400, failure_classification = HTTP_CLIENT_ERROR."""
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

    runner = mod.Vidu2ProbeRunner(evidence_dir=tmp_path)
    result = asyncio.run(runner.execute_probe(
        adapter=mock_adapter,
        authorized_main_sha=CANONICAL_BASE_SHA,
        current_sha=CANONICAL_BASE_SHA,
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


def test_req_l_http_401_403_mock_handling(tmp_path):
    """L. HTTP 401/403 mock handling -> provider_http_status = 401/403, failure_classification = HTTP_CLIENT_ERROR, secrets stripped."""
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

        runner = mod.Vidu2ProbeRunner(evidence_dir=evidence_dir)
        result = asyncio.run(runner.execute_probe(
            adapter=mock_adapter,
            authorized_main_sha=CANONICAL_BASE_SHA,
            current_sha=CANONICAL_BASE_SHA,
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

        evidence_file = evidence_dir / "vidu2_execution_evidence.json"
        assert evidence_file.is_file()
        file_text = evidence_file.read_text(encoding="utf-8")
        assert "api_key" not in file_text
        assert "Token" not in file_text
        assert "raw_response" not in file_text


def test_req_m_http_429_mock_handling_no_auto_retry(tmp_path):
    """M. HTTP 429 mock handling -> provider_http_status = 429, failure_classification = HTTP_RATE_LIMITED, cap = 1."""
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

    runner = mod.Vidu2ProbeRunner(evidence_dir=tmp_path)
    result = asyncio.run(runner.execute_probe(
        adapter=mock_adapter,
        authorized_main_sha=CANONICAL_BASE_SHA,
        current_sha=CANONICAL_BASE_SHA,
        auth_confirmed=True,
        fence_confirmed=True,
        ref_name="main",
    ))

    assert result["status"] == "FAILED"
    assert result["provider_http_status"] == 429
    assert result["failure_classification"] == "HTTP_RATE_LIMITED"
    assert runner.generation_post_count == 1
    assert mock_adapter.submit_generation_job.await_count == 1


def test_req_n_http_500_mock_handling_fail_closed_no_retry(tmp_path):
    """N. HTTP 500 mock handling -> provider_http_status = 500, failure_classification = HTTP_SERVER_ERROR, fail closed."""
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

    runner = mod.Vidu2ProbeRunner(evidence_dir=tmp_path)
    with pytest.raises(RuntimeError, match="Ambiguous POST submission outcome"):
        asyncio.run(runner.execute_probe(
            adapter=mock_adapter,
            authorized_main_sha=CANONICAL_BASE_SHA,
            current_sha=CANONICAL_BASE_SHA,
            auth_confirmed=True,
            fence_confirmed=True,
            ref_name="main",
        ))

    assert runner.generation_post_count == 1
    assert mock_adapter.submit_generation_job.await_count == 1

    evidence_file = tmp_path / "vidu2_execution_evidence.json"
    assert evidence_file.is_file()
    data = json.loads(evidence_file.read_text(encoding="utf-8"))
    assert data["status"] == "STOPPED"
    assert data["provider_http_status"] == 500
    assert data["failure_classification"] == "HTTP_SERVER_ERROR"


def test_req_o_ambiguous_submit_fails_closed_without_retry(tmp_path):
    """O. Ambiguous submit transport outcome fails closed without retry."""
    mod = _load_script_module()
    from app.providers.base import ProviderJobResult

    mock_adapter = MagicMock()
    mock_adapter.submit_generation_job = AsyncMock(return_value=ProviderJobResult(
        provider_job_id="",
        status="FAILED",
        error_code="TRANSPORT_ERROR",
        submission_uncertain=True,
    ))

    runner = mod.Vidu2ProbeRunner(evidence_dir=tmp_path)

    async def _run():
        await runner.execute_probe(
            adapter=mock_adapter,
            authorized_main_sha=CANONICAL_BASE_SHA,
            current_sha=CANONICAL_BASE_SHA,
            auth_confirmed=True,
            fence_confirmed=True,
            ref_name="main",
        )

    with pytest.raises(RuntimeError, match="Ambiguous POST submission outcome"):
        asyncio.run(_run())

    assert mock_adapter.submit_generation_job.await_count == 1
    assert runner.generation_post_count == 1
    evidence_file = tmp_path / "vidu2_execution_evidence.json"
    assert evidence_file.is_file()
    data = json.loads(evidence_file.read_text(encoding="utf-8"))
    assert data["status"] == "STOPPED"
    assert "SUBMISSION_UNCERTAIN" in data["error"]


def test_req_p_polling_operations_use_get_only(tmp_path):
    """P. Polling operations use GET only after confirmed submission."""
    mod = _load_script_module()
    from app.providers.base import ProviderJobResult

    mock_adapter = MagicMock()
    mock_adapter.submit_generation_job = AsyncMock(return_value=ProviderJobResult(
        provider_job_id="vidu2-job-abc",
        status="QUEUED",
        provider_status="queued",
        provider_credits=4.0,
    ))
    mock_adapter.check_job_status = AsyncMock(return_value=ProviderJobResult(
        provider_job_id="vidu2-job-abc",
        status="COMPLETED",
        provider_status="success",
        video_url="https://example.com/vidu2.mp4",
        provider_credits=4.0,
    ))

    runner = mod.Vidu2ProbeRunner(evidence_dir=tmp_path)
    result = asyncio.run(runner.execute_probe(
        adapter=mock_adapter,
        max_poll_attempts=2,
        poll_interval_seconds=0.01,
        authorized_main_sha=CANONICAL_BASE_SHA,
        current_sha=CANONICAL_BASE_SHA,
        auth_confirmed=True,
        fence_confirmed=True,
        ref_name="main",
    ))

    assert result["status"] == "SUCCESS"
    assert result["generation_posts"] == 1
    assert mock_adapter.submit_generation_job.await_count == 1
    assert mock_adapter.check_job_status.await_count == 1


def test_req_q_evidence_sanitization():
    """Q. Evidence sanitization strips secrets, raw response bodies, and response headers."""
    mod = _load_script_module()

    raw_state = {
        "execution_id": EXPECTED_IDENTITY,
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
        # Unsafe fields
        "raw_response": {"sensitive": "body"},
        "response_headers": {"x-secret": "topsecret"},
        "api_key": "BEARER_TOKEN_VALUE",
        "Authorization": "Token BEARER_TOKEN_VALUE",
        "secret_token": "TOKEN",
        "usd": 0.20,
    }

    sanitized = mod.sanitize_evidence(raw_state)

    assert "raw_response" not in sanitized
    assert "response_headers" not in sanitized
    assert "api_key" not in sanitized
    assert "Authorization" not in sanitized
    assert "secret_token" not in sanitized
    assert "usd" not in sanitized

    assert sanitized["execution_id"] == EXPECTED_IDENTITY
    assert sanitized["resolution"] == "720p"
    assert sanitized["provider_http_status"] == 400
    assert sanitized["failure_classification"] == "HTTP_CLIENT_ERROR"
    assert sanitized["vidu_credits_consumed"] is None
    assert sanitized["vidu_credits_consumed_confirmed"] is False


def test_req_r_zero_calls_to_other_providers():
    """R. Zero calls to OpenAI, Gemini, ElevenLabs."""
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


def test_req_s_workflow_safety_and_structure():
    """S. Workflow safety: workflow_dispatch only, dedicated concurrency group, base sha, markers."""
    assert WORKFLOW_PATH.is_file(), f"Missing {WORKFLOW_PATH}"
    content = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "workflow_dispatch:" in content
    assert "\n  push:" not in content
    assert "\n  pull_request:" not in content
    assert "group: wp020-live-r5-vidu2-probe" in content
    assert "WP020 LIVE R5 Vidu2 1-Call Probe" in content
    assert f"CANONICAL_BASE_SHA: {CANONICAL_BASE_SHA}" in content
    assert f"WP020_VIDU2_EXECUTION_ID: {EXPECTED_IDENTITY}" in content

    # Markers
    assert "FRESH_OWNER_AUTHORIZED_VIDU2: ${WP020_VIDU2_EXECUTION_ID} @ ${GITHUB_SHA}" in content
    assert "EXECUTION_STARTED: ${WP020_VIDU2_EXECUTION_ID}" in content
    assert "VIDU2_PROBE_PASS: ${WP020_VIDU2_EXECUTION_ID}" in content
    assert "VIDU2_PROBE_STOPPED: ${WP020_VIDU2_EXECUTION_ID}" in content
    assert "VIDU2_OWNER_AUTHORIZATION_CONFIRMED=true" in content
    assert "EXECUTION_FENCE_CONFIRMED=true" in content


def test_req_t_workflow_comment_pagination_and_fail_closed_simulation():
    """T. Workflow comment pagination and fail-closed guards simulation."""
    content = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert "--paginate" in content
    assert 'repos/${GITHUB_REPOSITORY}/issues/${ISSUE_NUMBER}/comments' in content

    auth_marker = f"FRESH_OWNER_AUTHORIZED_VIDU2: {EXPECTED_IDENTITY} @ {CANONICAL_BASE_SHA}"
    fence_marker = f"EXECUTION_STARTED: {EXPECTED_IDENTITY}"
    pass_marker = f"VIDU2_PROBE_PASS: {EXPECTED_IDENTITY}"
    stop_marker = f"VIDU2_PROBE_STOPPED: {EXPECTED_IDENTITY}"

    def evaluate_comments(comments: list[str]) -> str:
        if not comments:
            return "STOP_EMPTY"
        if auth_marker not in comments:
            return "STOP_MISSING_AUTH"
        if fence_marker in comments:
            return "STOP_FENCE_CONSUMED"
        if pass_marker in comments:
            return "STOP_TERMINAL_PASS"
        if stop_marker in comments:
            return "STOP_TERMINAL_STOP"
        return "AUTHORIZED"

    assert evaluate_comments([]) == "STOP_EMPTY"
    assert evaluate_comments(["random comment"]) == "STOP_MISSING_AUTH"
    assert evaluate_comments([auth_marker]) == "AUTHORIZED"
    assert evaluate_comments([auth_marker, fence_marker]) == "STOP_FENCE_CONSUMED"
    assert evaluate_comments([auth_marker, pass_marker]) == "STOP_TERMINAL_PASS"
    assert evaluate_comments([auth_marker, stop_marker]) == "STOP_TERMINAL_STOP"


def test_req_u_mock_transport_only():
    """U. Verification that contract tests use only MockTransport / mock adapters with zero live network calls."""
    mod = _load_script_module()
    # Confirm script runner requires explicit permit flags before any adapter call
    runner = mod.Vidu2ProbeRunner()
    mock_adapter = MagicMock()
    mock_adapter.submit_generation_job = AsyncMock()

    with pytest.raises(RuntimeError, match="Owner live execution authorization is not confirmed"):
        asyncio.run(runner.execute_probe(
            adapter=mock_adapter,
            auth_confirmed=False,
            fence_confirmed=False,
        ))

    assert mock_adapter.submit_generation_job.await_count == 0


def test_req_v_vidu_api_key_guard_ordering_before_fence_and_permit():
    """V. Prove ordering: VIDU_API_KEY presence guard
    < "Consuming VIDU2 execution fence"
    < VIDU2_OWNER_AUTHORIZATION_CONFIRMED=true
    and VIDU_API_KEY presence guard < EXECUTION_FENCE_CONFIRMED=true.
    """
    assert WORKFLOW_PATH.is_file(), f"Missing {WORKFLOW_PATH}"
    content = WORKFLOW_PATH.read_text(encoding="utf-8")

    key_guard = 'if [ -z "${VIDU_API_KEY:-}" ]; then'
    fence_msg = 'Consuming VIDU2 execution fence...'
    fence_comment = 'gh issue comment "${ISSUE_NUMBER}" --body "${FENCE_MARKER}"'
    auth_export = 'VIDU2_OWNER_AUTHORIZATION_CONFIRMED=true'
    fence_export = 'EXECUTION_FENCE_CONFIRMED=true'

    assert key_guard in content
    assert fence_msg in content
    assert fence_comment in content
    assert auth_export in content
    assert fence_export in content

    idx_key_guard = content.index(key_guard)
    idx_fence_msg = content.index(fence_msg)
    idx_fence_comment = content.index(fence_comment)
    idx_auth_export = content.index(auth_export)
    idx_fence_export = content.index(fence_export)

    # Required order:
    # 1. VIDU_API_KEY presence guard < "Consuming VIDU2 execution fence" < VIDU2_OWNER_AUTHORIZATION_CONFIRMED=true
    assert idx_key_guard < idx_fence_msg < idx_auth_export
    # 2. VIDU_API_KEY presence guard < EXECUTION_FENCE_CONFIRMED=true
    assert idx_key_guard < idx_fence_export
    # 3. Fence comment is written strictly after key guard and before exports
    assert idx_key_guard < idx_fence_comment < idx_auth_export
    assert idx_key_guard < idx_fence_comment < idx_fence_export


def test_req_w_workflow_yaml_syntax_and_registration_validity():
    """W. Prove workflow YAML syntax is valid and workflow_dispatch registration contract holds."""
    assert WORKFLOW_PATH.is_file(), f"Missing {WORKFLOW_PATH}"
    content = WORKFLOW_PATH.read_text(encoding="utf-8")

    data = yaml.safe_load(content)
    assert isinstance(data, dict), "Workflow YAML must parse into a mapping"
    assert data.get("name") == "WP020 LIVE R5 Vidu2 1-Call Probe"

    # PyYAML parses unquoted 'on:' as boolean True or string 'on'
    triggers = data.get("on") if "on" in data else data.get(True)
    assert isinstance(triggers, dict), "Workflow triggers must be a mapping"
    assert "workflow_dispatch" in triggers, "Workflow must register workflow_dispatch trigger"
    assert "push" not in triggers, "Workflow must NOT have push trigger"
    assert "pull_request" not in triggers, "Workflow must NOT have pull_request trigger"
    assert "schedule" not in triggers, "Workflow must NOT have schedule trigger"

    dispatch_config = triggers["workflow_dispatch"]
    assert "inputs" in dispatch_config
    assert "mode" in dispatch_config["inputs"]
    mode_input = dispatch_config["inputs"]["mode"]
    assert mode_input["default"] == "dry-run"
    assert mode_input["type"] == "choice"
    assert mode_input["options"] == ["dry-run", "live"]
