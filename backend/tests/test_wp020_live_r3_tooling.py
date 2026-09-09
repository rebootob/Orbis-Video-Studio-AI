from __future__ import annotations

import ast
import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / ".github" / "scripts"
WORKFLOWS = ROOT / ".github" / "workflows"


def _load_contract():
    path = SCRIPTS / "wp020_live_r3_contract.py"
    spec = importlib.util.spec_from_file_location("wp020_live_r3_contract_test", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_r3_python_tooling_parses():
    for name in (
        "wp020_live_r3_contract.py",
        "wp020_live_r3_preflight.py",
        "wp020_live_uat_r3.py",
        "wp020_live_r3_failure_export.py",
    ):
        source = (SCRIPTS / name).read_text(encoding="utf-8")
        ast.parse(source, filename=name)


def test_r3_identity_and_markers_are_distinct_and_exact():
    c = _load_contract()
    assert c.R3_EXECUTION_ID == "LIVE-20260909-363F-R3"
    assert "R1" not in c.R3_EXECUTION_ID
    assert "R2" not in c.R3_EXECUTION_ID
    sha = "a" * 40
    assert c.authorization_marker(sha) == f"FRESH_OWNER_AUTHORIZED_R3: {c.R3_EXECUTION_ID} @ {sha}"
    assert c.execution_fence_marker() == f"EXECUTION_STARTED: {c.R3_EXECUTION_ID}"
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


def test_sanitized_creative_failure_excludes_error_text_and_content_fields():
    c = _load_contract()
    audit = SimpleNamespace(
        id="audit-1",
        provider="unknown",
        model="unknown",
        request_type="STORY_GENERATE",
        status="FAILED",
        duration_ms=123.4,
        error_message="SECRET provider detail",
        prompt="private prompt",
    )
    evidence = c.sanitize_creative_audit(audit)
    serialized = repr(evidence)
    assert evidence["provider"] == "openai"
    assert evidence["model"] == "gpt-4o"
    assert evidence["status"] == "FAILED"
    assert "error_message" not in serialized
    assert "prompt" not in serialized
    assert "SECRET" not in serialized


def test_sanitized_generation_failure_excludes_raw_body_headers_payload_and_secret_fields():
    c = _load_contract()
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
            "http_status": 403,
            "error_code": "HTTP_ERROR",
            "retryable": False,
            "submission_uncertain": False,
            "raw_body": "SECRET BODY",
            "headers": {"authorization": "SECRET"},
            "api_key": "SECRET",
        },
    )
    evidence = c.sanitize_generation_job(job)
    serialized = repr(evidence)
    assert evidence["result"]["http_status"] == 403
    assert evidence["result"]["error_code"] == "HTTP_ERROR"
    assert "raw_body" not in serialized
    assert "headers" not in serialized
    assert "api_key" not in serialized
    assert "SECRET" not in serialized
    assert "prompt" not in serialized


def test_sanitized_audio_failure_excludes_unapproved_provenance_fields():
    c = _load_contract()
    clip = SimpleNamespace(
        id="clip-1",
        audio_type="VO",
        status="FAILED",
        provenance={
            "provider_job_id": "audio-job-1",
            "error_code": "PROVIDER_REJECTED",
            "stage": "submission",
            "raw_body": "SECRET BODY",
            "authorization": "SECRET",
        },
    )
    evidence = c.sanitize_audio_clip(clip)
    serialized = repr(evidence)
    assert evidence["provenance"]["error_code"] == "PROVIDER_REJECTED"
    assert "raw_body" not in serialized
    assert "authorization" not in serialized
    assert "SECRET" not in serialized


def test_r3_preflight_is_manual_main_only_and_has_no_generation_invocation():
    workflow = (WORKFLOWS / "wp020-live-r3-preflight.yml").read_text(encoding="utf-8")
    script = (SCRIPTS / "wp020_live_r3_preflight.py").read_text(encoding="utf-8")
    assert "workflow_dispatch:" in workflow
    assert 'if [ "$GITHUB_REF_NAME" != "main" ]; then' in workflow
    assert "R3 preflight must be dispatched on canonical main" in workflow
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


def test_r3_runner_is_not_dynamic_r1_snapshot_patch_and_persists_sanitized_failure_before_exit():
    source = (SCRIPTS / "wp020_live_uat_r3.py").read_text(encoding="utf-8")
    assert "wp020_live_uat_r1_snapshot" not in source
    assert "exec(compile(" not in source
    assert "next_paid_call" in source
    assert "sanitize_generation_job" in source
    assert "sanitize_audio_clip" in source
    assert "_capture_durable_failure_evidence()" in source
    exception_block = source.rsplit('if __name__ == "__main__":', 1)[1]
    assert exception_block.index("_capture_durable_failure_evidence()") < exception_block.index("_write_evidence()")


def test_creative_failure_export_reads_only_durable_audit_metadata_and_no_provider_api():
    source = (SCRIPTS / "wp020_live_r3_failure_export.py").read_text(encoding="utf-8")
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


def test_paid_workflow_requires_owner_marker_fence_preflight_and_stop_enrichment_before_upload():
    workflow = (WORKFLOWS / "wp020-live-execution-r3.yml").read_text(encoding="utf-8")
    helper = (SCRIPTS / "wp020_live_r3_fence.sh").read_text(encoding="utf-8")
    assert "workflow_dispatch:" in workflow
    assert 'test "$GITHUB_REF_NAME" = "main"' in workflow
    assert "LIVE-20260909-363F-R3" in workflow
    assert "FRESH_OWNER_AUTHORIZED_R3:" in helper
    assert "EXECUTION_STARTED:" in helper
    assert "LIVE_EXECUTION_PASS:" in helper
    assert "LIVE_EXECUTION_STOPPED:" in helper
    assert "wp020_live_r3_preflight.py" in workflow
    assert "wp020_live_r3_fence.sh consume" in workflow
    assert "wp020_live_uat_r3.py" in workflow
    assert "wp020_live_r3_failure_export.py" in workflow
    assert workflow.index("wp020_live_r3_preflight.py") < workflow.index("wp020_live_r3_fence.sh consume")
    assert workflow.index("wp020_live_r3_fence.sh consume") < workflow.index("wp020_live_uat_r3.py")
    assert workflow.index("wp020_live_uat_r3.py") < workflow.index("wp020_live_r3_failure_export.py")
    assert workflow.index("wp020_live_r3_failure_export.py") < workflow.index("Upload sanitized LIVE R3 evidence artifact")
