from __future__ import annotations

import ast
import hashlib
import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / ".github" / "scripts"
WORKFLOWS = ROOT / ".github" / "workflows"
EXPECTED_R3_RUNNER_GIT_BLOB_SHA = "24150cdece623004443e03ceecea10490955822b"


def _load_contract():
    path = SCRIPTS / "wp020_live_r4_contract.py"
    spec = importlib.util.spec_from_file_location("wp020_live_r4_contract_test", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _git_blob_sha(path: Path) -> str:
    content = path.read_bytes()
    return hashlib.sha1(f"blob {len(content)}\0".encode("utf-8") + content).hexdigest()


def test_r4_python_tooling_parses():
    for name in (
        "wp020_live_r4_contract.py",
        "wp020_live_r4_preflight.py",
        "wp020_live_uat_r4.py",
        "wp020_live_r4_failure_export.py",
    ):
        source = (SCRIPTS / name).read_text(encoding="utf-8")
        ast.parse(source, filename=name)


def test_r4_identity_markers_and_tooling_base_are_exact():
    c = _load_contract()
    assert c.R4_EXECUTION_ID == "LIVE-20260909-DE17-R4"
    assert c.R4_TOOLING_BASE_SHA == "de17a125dcd3b8066a546369d03aba813a7b5641"
    assert c.HARD_CAP_USD == 1.00
    assert c.MAX_PAID_CALLS == 6
    sha = "a" * 40
    assert c.authorization_marker(sha) == f"FRESH_OWNER_AUTHORIZED_R4: {c.R4_EXECUTION_ID} @ {sha}"
    assert c.execution_fence_marker() == f"EXECUTION_STARTED: {c.R4_EXECUTION_ID}"
    with pytest.raises(ValueError):
        c.authorization_marker("not-a-sha")


def test_runtime_binding_fails_closed_on_wrong_sha_or_missing_fence():
    c = _load_contract()
    sha = "b" * 40
    c.validate_runtime_binding(github_sha=sha, authorized_main_sha=sha, fence_confirmed=True)
    with pytest.raises(RuntimeError):
        c.validate_runtime_binding(github_sha=sha, authorized_main_sha="c" * 40, fence_confirmed=True)
    with pytest.raises(RuntimeError):
        c.validate_runtime_binding(github_sha=sha, authorized_main_sha=sha, fence_confirmed=False)


def test_paid_call_sequence_is_exact_and_capped_at_six():
    c = _load_contract()
    assert c.PAID_CALL_SEQUENCE == (
        "OPENAI_CREATIVE_STORY:gpt-4o",
        "GEMINI_IMAGE:gemini-3.1-flash-image:1K",
        "VIDU_VIDEO:viduq2:text2video:4s:720p",
        "ELEVENLABS_TTS:Thai:<=150chars",
        "ELEVENLABS_MUSIC:<=10s",
        "ELEVENLABS_AMBIENCE:<=3s",
    )
    consumed: list[str] = []
    for expected_index, label in enumerate(c.PAID_CALL_SEQUENCE, start=1):
        assert c.next_paid_call(consumed, label) == expected_index
        consumed.append(label)
    assert len(consumed) == c.MAX_PAID_CALLS == 6
    with pytest.raises(RuntimeError):
        c.next_paid_call(consumed, "EXTRA_CALL")
    with pytest.raises(RuntimeError):
        c.next_paid_call([], c.PAID_CALL_SEQUENCE[1])


def test_budget_guard_rejects_unknown_invalid_or_over_cap_cost():
    c = _load_contract()
    c.enforce_budget(committed_usd=0.999999, unknown_cost_count=0)
    with pytest.raises(RuntimeError):
        c.enforce_budget(committed_usd=0.1, unknown_cost_count=1)
    with pytest.raises(RuntimeError):
        c.enforce_budget(committed_usd=1.0001, unknown_cost_count=0)
    with pytest.raises(RuntimeError):
        c.enforce_budget(committed_usd=float("nan"), unknown_cost_count=0)


@pytest.mark.parametrize("provider", ["openai", "gemini_image", "vidu", "elevenlabs_audio"])
@pytest.mark.parametrize("status", ["FAILED", "REJECTED", "RECONCILIATION_REQUIRED"])
def test_every_provider_non_success_status_stops(provider: str, status: str):
    c = _load_contract()
    with pytest.raises(RuntimeError):
        c.require_provider_success(
            provider,
            status,
            submission_uncertain=status == "RECONCILIATION_REQUIRED",
        )


def test_r4_sanitizers_exclude_raw_sensitive_content():
    c = _load_contract()
    audit = SimpleNamespace(
        id="audit-1",
        provider="unknown",
        model="unknown",
        request_type="STORY_GENERATE",
        status="FAILED",
        duration_ms=12.0,
        error_message="SECRET provider detail",
        prompt="private prompt",
    )
    job = SimpleNamespace(
        id="job-1",
        provider_name="gemini_image",
        provider_job_id="provider-job-1",
        status="FAILED",
        job_type="IMAGE",
        cost_usd=0.0,
        payload={"api_key": "SECRET", "prompt": "private"},
        result={
            "provider": "gemini_image",
            "model": "gemini-3.1-flash-image",
            "http_status": 429,
            "error_code": "RESOURCE_EXHAUSTED",
            "retryable": True,
            "submission_uncertain": False,
            "quota_class": "rate_limit",
            "raw_body": "SECRET BODY",
            "headers": {"authorization": "SECRET"},
            "api_key": "SECRET",
        },
    )
    clip = SimpleNamespace(
        id="clip-1",
        audio_type="VO",
        status="FAILED",
        provenance={
            "provider_job_id": "audio-job-1",
            "error_code": "PROVIDER_REJECTED",
            "stage": "submission",
            "raw_body": "SECRET BODY",
        },
    )
    serialized = repr(
        {
            "creative": c.sanitize_creative_audit(audit),
            "generation": c.sanitize_generation_job(job),
            "audio": c.sanitize_audio_clip(clip),
        }
    )
    assert "SECRET" not in serialized
    assert "raw_body" not in serialized
    assert "headers" not in serialized
    assert "prompt" not in serialized


def test_r4_runner_reuses_only_exact_frozen_r3_implementation_without_source_rewrite():
    source = (SCRIPTS / "wp020_live_uat_r4.py").read_text(encoding="utf-8")
    r3_path = SCRIPTS / "wp020_live_uat_r3.py"
    assert _git_blob_sha(r3_path) == EXPECTED_R3_RUNNER_GIT_BLOB_SHA
    assert EXPECTED_R3_RUNNER_GIT_BLOB_SHA in source
    assert "import wp020_live_uat_r3 as base" in source
    assert "_bind_r4_contract(base)" in source
    assert "base._capture_durable_failure_evidence()" in source
    assert "base._write_evidence()" in source
    for forbidden in ("exec(compile(", "runpy", ".replace(\"R3\"", "source.replace"):
        assert forbidden not in source


def test_r4_preflight_is_manual_main_only_and_has_no_generation_invocation():
    workflow = (WORKFLOWS / "wp020-live-r4-preflight.yml").read_text(encoding="utf-8")
    script = (SCRIPTS / "wp020_live_r4_preflight.py").read_text(encoding="utf-8")
    assert "workflow_dispatch:" in workflow
    assert 'if [ "$GITHUB_REF_NAME" != "main" ]; then' in workflow
    assert "R4 preflight must be dispatched on canonical main" in workflow
    assert "LIVE-20260909-DE17-R4" in workflow
    assert "generation_request_sent=false" in workflow
    assert "paid_provider_calls=0" in workflow
    for forbidden in (
        ".generate_image(",
        ".generate_audio(",
        ".generate_video(",
        '"GENERATE_STORY"',
        "execute_action(",
        "EXECUTION_STARTED:",
    ):
        assert forbidden not in script


def test_r4_paid_workflow_requires_marker_preflight_fence_and_exact_runner_order():
    workflow = (WORKFLOWS / "wp020-live-execution-r4.yml").read_text(encoding="utf-8")
    helper = (SCRIPTS / "wp020_live_r4_fence.sh").read_text(encoding="utf-8")
    assert "workflow_dispatch:" in workflow
    assert 'test "$GITHUB_REF_NAME" = "main"' in workflow
    assert "LIVE-20260909-DE17-R4" in workflow
    assert "de17a125dcd3b8066a546369d03aba813a7b5641" in workflow
    assert "FRESH_OWNER_AUTHORIZED_R4:" in helper
    assert "EXECUTION_STARTED:" in helper
    assert "LIVE_EXECUTION_PASS:" in helper
    assert "LIVE_EXECUTION_STOPPED:" in helper
    assert "wp020_live_r4_preflight.py" in workflow
    assert "wp020_live_r4_fence.sh consume" in workflow
    assert "wp020_live_uat_r4.py" in workflow
    assert "wp020_live_r4_failure_export.py" in workflow
    assert workflow.index("wp020_live_r4_preflight.py") < workflow.index("wp020_live_r4_fence.sh consume")
    assert workflow.index("wp020_live_r4_fence.sh consume") < workflow.index("wp020_live_uat_r4.py")
    assert workflow.index("wp020_live_uat_r4.py") < workflow.index("wp020_live_r4_failure_export.py")
    assert workflow.index("wp020_live_r4_failure_export.py") < workflow.index("Upload sanitized LIVE R4 evidence artifact")


def test_r4_failure_export_has_no_provider_api_calls():
    source = (SCRIPTS / "wp020_live_r4_failure_export.py").read_text(encoding="utf-8")
    assert "GenerationAuditLog" in source
    assert "sanitize_creative_audit" in source
    assert 'failure_evidence["creative_audit"]' in source
    for forbidden in (
        "httpx.",
        "requests.",
        ".generate_story(",
        ".generate_image(",
        ".generate_audio(",
        ".generate_video(",
        "error_message",
    ):
        assert forbidden not in source
