from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = ROOT / ".github" / "scripts" / "wp020_live_r3_contract.py"


def _load_contract():
    spec = importlib.util.spec_from_file_location("wp020_live_r3_contract_quota_test", CONTRACT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_generation_job_artifact_retains_only_sanitized_gemini_429_quota_fields():
    contract = _load_contract()
    job = SimpleNamespace(
        id="job-429",
        provider_name="gemini_image",
        provider_job_id=None,
        status="FAILED",
        job_type="IMAGE",
        cost_usd=0.0,
        result={
            "provider": "gemini_image",
            "model": "gemini-3.1-flash-image",
            "http_status": 429,
            "error_code": "HTTP_ERROR",
            "retryable": True,
            "submission_uncertain": False,
            "provider_status": "RESOURCE_EXHAUSTED",
            "quota_class": "QUOTA_ZERO",
            "retry_delay": "60s",
            "quota_failures": [
                {
                    "quota_metric": "generativelanguage.googleapis.com/generate_requests_per_model_per_day",
                    "quota_id": "GenerateRequestsPerDayPerProjectPerModel-FreeTier",
                    "quota_value": "0",
                    "quota_dimensions": {
                        "model": "gemini-3.1-flash-image",
                        "location": "global",
                        "project": "SECRET_PROJECT",
                    },
                    "description": "SECRET provider body text",
                }
            ],
            "raw_body": "SECRET BODY",
            "headers": {"authorization": "SECRET"},
            "api_key": "SECRET",
            "prompt": "SECRET PROMPT",
        },
    )

    evidence = contract.sanitize_generation_job(job)
    result = evidence["result"]

    assert result["http_status"] == 429
    assert result["provider_status"] == "RESOURCE_EXHAUSTED"
    assert result["quota_class"] == "QUOTA_ZERO"
    assert result["retry_delay"] == "60s"
    assert result["quota_failures"] == [
        {
            "quota_metric": "generativelanguage.googleapis.com/generate_requests_per_model_per_day",
            "quota_id": "GenerateRequestsPerDayPerProjectPerModel-FreeTier",
            "quota_value": "0",
            "quota_dimensions": {
                "model": "gemini-3.1-flash-image",
                "location": "global",
            },
        }
    ]

    serialized = repr(evidence)
    for forbidden in (
        "SECRET_PROJECT",
        "SECRET provider body text",
        "SECRET BODY",
        "authorization",
        "api_key",
        "SECRET PROMPT",
        "description",
    ):
        assert forbidden not in serialized


def test_generation_job_artifact_ignores_malformed_quota_failure_container():
    contract = _load_contract()
    job = SimpleNamespace(
        id="job-429-malformed",
        provider_name="gemini_image",
        provider_job_id=None,
        status="FAILED",
        job_type="IMAGE",
        cost_usd=0.0,
        result={
            "provider": "gemini_image",
            "http_status": 429,
            "quota_failures": "not-a-list",
            "raw_body": "SECRET BODY",
        },
    )

    evidence = contract.sanitize_generation_job(job)
    assert evidence["result"]["http_status"] == 429
    assert "quota_failures" not in evidence["result"]
    assert "SECRET BODY" not in repr(evidence)
