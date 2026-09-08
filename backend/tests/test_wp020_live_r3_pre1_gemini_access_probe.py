import importlib.util
import io
import json
from pathlib import Path
from urllib.error import HTTPError

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / ".github/scripts/wp020_live_r3_gemini_access_probe.py"
WORKFLOW_PATH = REPO_ROOT / ".github/workflows/wp020-live-r3-pre1-gemini-access.yml"


def _load_probe_module():
    spec = importlib.util.spec_from_file_location("wp020_live_r3_gemini_access_probe", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class _Response:
    def __init__(self, status, payload):
        self.status = status
        self._payload = payload

    def read(self, _limit):
        return self._payload


@pytest.fixture
def probe_module():
    return _load_probe_module()


def test_probe_uses_exact_metadata_get_and_never_leaks_key(monkeypatch, capsys, probe_module):
    key = "unit-test-gemini-secret"
    captured = {}

    def opener(request, timeout):
        captured["method"] = request.get_method()
        captured["url"] = request.full_url
        captured["headers"] = dict(request.header_items())
        captured["timeout"] = timeout
        return _Response(200, b'{"name":"models/gemini-3.1-flash-image"}')

    monkeypatch.setenv("GEMINI_API_KEY", key)
    monkeypatch.setenv("GEMINI_IMAGE_MODEL", "gemini-3.1-flash-image")

    assert probe_module.run_probe(opener=opener) == 0
    output = capsys.readouterr().out
    result = json.loads(output)

    assert captured["method"] == "GET"
    assert captured["url"] == "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-image"
    assert key not in captured["url"]
    assert captured["headers"]["X-goog-api-key"] == key
    assert captured["timeout"] == 15
    assert result["status"] == "ACCESS_PROBE_PASS"
    assert result["http_status"] == 200
    assert result["generation_request_sent"] is False
    assert result["paid_generation_calls"] == 0
    assert key not in output


@pytest.mark.parametrize(
    ("status_code", "expected_error"),
    [
        (400, "BAD_REQUEST"),
        (401, "AUTHENTICATION_FAILED"),
        (403, "AUTHORIZATION_FAILED"),
        (404, "MODEL_NOT_VISIBLE"),
        (429, "RATE_LIMITED"),
        (503, "PROVIDER_UNAVAILABLE"),
    ],
)
def test_probe_classifies_http_failure_without_reading_or_printing_body(
    monkeypatch, capsys, probe_module, status_code, expected_error
):
    key = "unit-test-gemini-secret"
    provider_body = b"provider-secret-body-must-not-appear"

    def opener(request, timeout):
        raise HTTPError(request.full_url, status_code, "failure", {}, io.BytesIO(provider_body))

    monkeypatch.setenv("GEMINI_API_KEY", key)
    monkeypatch.setenv("GEMINI_IMAGE_MODEL", "gemini-3.1-flash-image")

    assert probe_module.run_probe(opener=opener) == 3
    output = capsys.readouterr().out
    result = json.loads(output)

    assert result["status"] == "ACCESS_PROBE_STOP"
    assert result["http_status"] == status_code
    assert result["error_code"] == expected_error
    assert result["generation_request_sent"] is False
    assert result["paid_generation_calls"] == 0
    assert key not in output
    assert provider_body.decode() not in output


def test_invalid_model_stops_before_network(monkeypatch, capsys, probe_module):
    called = False

    def opener(request, timeout):
        nonlocal called
        called = True
        raise AssertionError("network must not be reached")

    monkeypatch.setenv("GEMINI_API_KEY", "unit-test-gemini-secret")
    monkeypatch.setenv("GEMINI_IMAGE_MODEL", "models/gemini-3.1-flash-image")

    assert probe_module.run_probe(opener=opener) == 2
    result = json.loads(capsys.readouterr().out)
    assert called is False
    assert result["error_code"] == "INVALID_MODEL"
    assert result["paid_generation_calls"] == 0


def test_workflow_is_manual_main_only_and_probe_is_generation_incapable():
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
    source = SCRIPT_PATH.read_text(encoding="utf-8")

    assert "workflow_dispatch:" in workflow
    assert "\n  push:" not in workflow
    assert "\n  pull_request:" not in workflow
    assert "permissions:\n  contents: read" in workflow
    assert "issues: write" not in workflow
    assert 'GITHUB_REF_NAME" != "main"' in workflow
    assert "d706acacd1f51224c955fb9c8d0d9eab3deda186" in workflow
    assert "GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}" in workflow

    assert 'method="GET"' in source
    assert "/models/{model}" in source
    assert "/interactions" not in source
    assert "generateContent" not in source
    assert ".post(" not in source
    assert '"generation_request_sent": False' in source
    assert '"paid_generation_calls": 0' in source
