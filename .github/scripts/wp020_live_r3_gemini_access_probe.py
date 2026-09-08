"""WP020 LIVE R3 PRE1 metadata-only Gemini access probe.

This probe performs exactly one authenticated GET to Gemini models.get. It does
not call image generation, does not submit content, and never prints the API key
or provider response body on failure.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any, Callable, Dict, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
DEFAULT_MODEL = "gemini-3.1-flash-image"
TIMEOUT_SECONDS = 15


def _result(
    status: str,
    *,
    model: str,
    http_status: Optional[int] = None,
    error_code: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "status": status,
        "provider": "gemini_image",
        "model": model,
        "http_status": http_status,
        "error_code": error_code,
        "generation_request_sent": False,
        "paid_generation_calls": 0,
    }


def _classify_http(status_code: int) -> str:
    if status_code == 400:
        return "BAD_REQUEST"
    if status_code == 401:
        return "AUTHENTICATION_FAILED"
    if status_code == 403:
        return "AUTHORIZATION_FAILED"
    if status_code == 404:
        return "MODEL_NOT_VISIBLE"
    if status_code == 429:
        return "RATE_LIMITED"
    if status_code >= 500:
        return "PROVIDER_UNAVAILABLE"
    return "HTTP_ERROR"


def _endpoint(model: str) -> str:
    if not model or "/" in model or "?" in model or "#" in model:
        raise ValueError("INVALID_MODEL")
    return f"{BASE_URL}/models/{model}"


def run_probe(opener: Callable[..., Any] = urlopen) -> int:
    model = (os.environ.get("GEMINI_IMAGE_MODEL") or DEFAULT_MODEL).strip()
    api_key = os.environ.get("GEMINI_API_KEY") or ""

    try:
        endpoint = _endpoint(model)
    except ValueError:
        print(json.dumps(_result("PREFLIGHT_STOP", model=model, error_code="INVALID_MODEL"), sort_keys=True))
        return 2

    if not api_key.strip() or "\n" in api_key or "\r" in api_key:
        print(json.dumps(_result("PREFLIGHT_STOP", model=model, error_code="GEMINI_API_KEY_MISSING_OR_INVALID"), sort_keys=True))
        return 2

    request = Request(
        endpoint,
        headers={"x-goog-api-key": api_key, "Accept": "application/json"},
        method="GET",
    )

    try:
        response = opener(request, timeout=TIMEOUT_SECONDS)
        status_code = int(getattr(response, "status", response.getcode()))
        payload = response.read(65536)
    except HTTPError as exc:
        status_code = int(exc.code)
        print(
            json.dumps(
                _result(
                    "ACCESS_PROBE_STOP",
                    model=model,
                    http_status=status_code,
                    error_code=_classify_http(status_code),
                ),
                sort_keys=True,
            )
        )
        return 3
    except (URLError, TimeoutError, OSError):
        print(json.dumps(_result("ACCESS_PROBE_STOP", model=model, error_code="TRANSPORT_ERROR"), sort_keys=True))
        return 3

    if status_code != 200:
        print(
            json.dumps(
                _result(
                    "ACCESS_PROBE_STOP",
                    model=model,
                    http_status=status_code,
                    error_code=_classify_http(status_code),
                ),
                sort_keys=True,
            )
        )
        return 3

    try:
        data = json.loads(payload.decode("utf-8"))
    except Exception:
        print(
            json.dumps(
                _result(
                    "ACCESS_PROBE_STOP",
                    model=model,
                    http_status=status_code,
                    error_code="INVALID_METADATA_RESPONSE",
                ),
                sort_keys=True,
            )
        )
        return 3

    expected_name = f"models/{model}"
    if not isinstance(data, dict) or data.get("name") != expected_name:
        print(
            json.dumps(
                _result(
                    "ACCESS_PROBE_STOP",
                    model=model,
                    http_status=status_code,
                    error_code="MODEL_METADATA_MISMATCH",
                ),
                sort_keys=True,
            )
        )
        return 3

    print(json.dumps(_result("ACCESS_PROBE_PASS", model=model, http_status=200), sort_keys=True))
    return 0


def main() -> None:
    raise SystemExit(run_probe())


if __name__ == "__main__":
    main()
