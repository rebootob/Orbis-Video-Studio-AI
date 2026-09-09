"""Provider-neutral persistence boundary. Never retain raw provider bodies."""
import re
import math
from urllib.parse import urlsplit, parse_qsl
from app.core.config import settings

SECRET_KEY = re.compile(r"api.?key|authorization|token|secret|password|credential", re.I)
SAFE_METADATA_CODE = re.compile(r"^[A-Za-z0-9_.:-]{1,128}$")
SAFE_PROVIDER_JOB_ID = re.compile(r"^[A-Za-z0-9_-]{1,255}$")


def sanitize_secret_text(text):
    if not text:
        return text
    return re.sub(
        r'''(?i)(?:authorization|api[_-]?key|token|bearer|secret|password|credential)[\\"' \t:=]*[^\s,;}]+''',
        "[REDACTED]", str(text),
    )


def is_secret_key(k: str) -> bool:
    k_lower = str(k).lower()
    if k_lower in ("prompt_tokens", "completion_tokens", "total_tokens", "tokens") or k_lower.endswith("_tokens"):
        return False
    return bool(SECRET_KEY.search(k_lower))


def contains_secret(value):
    if isinstance(value, dict):
        return any(is_secret_key(k) or contains_secret(v) for k, v in value.items())
    if isinstance(value, list):
        return any(contains_secret(v) for v in value)
    if isinstance(value, str):
        configured_secrets = (v for k, v in settings.model_dump().items()
                              if SECRET_KEY.search(k) and isinstance(v, str) and v)
        return sanitize_secret_text(value) != value or any(secret in value for secret in configured_secrets)
    return False


def safe_url(value):
    if not isinstance(value, str) or len(value) > 4096:
        return None
    try:
        parsed = urlsplit(value)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
            return None
        if any(SECRET_KEY.search(k) for k, _ in parse_qsl(parsed.query)) or contains_secret(value):
            return None
        return value
    except ValueError:
        return None


def _safe_code(value):
    if not isinstance(value, str):
        return None
    value = value.strip()
    if not SAFE_METADATA_CODE.fullmatch(value) or contains_secret(value):
        return None
    return value


def _safe_provider_job_id(value):
    if not isinstance(value, str):
        return None
    if not SAFE_PROVIDER_JOB_ID.fullmatch(value) or contains_secret(value):
        return None
    return value


def _safe_nonnegative_number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    value = float(value)
    if not math.isfinite(value) or value < 0:
        return None
    return value


def safe_result(result):
    if result is None:
        return None
    # Deliberately omit raw_response, error_message and arbitrary nested data.
    # Allowlist only typed, non-content provider metadata required for durable
    # reconciliation after an ephemeral runtime is torn down.
    data = {
        "status": result.status,
        "video_url": safe_url(getattr(result, "video_url", None)),
        "thumbnail_url": safe_url(getattr(result, "thumbnail_url", None)),
    }
    progress = getattr(result, "progress_percentage", None)
    if isinstance(progress, (int, float)) and not isinstance(progress, bool) and math.isfinite(progress) and 0 <= progress <= 100:
        data["progress_percentage"] = progress

    provider_job_id = _safe_provider_job_id(getattr(result, "provider_job_id", None))
    if provider_job_id:
        data["provider_job_id"] = provider_job_id

    error_code = _safe_code(getattr(result, "error_code", None))
    if error_code:
        data["error_code"] = error_code

    status_code = getattr(result, "status_code", None)
    if isinstance(status_code, int) and not isinstance(status_code, bool) and 100 <= status_code <= 599:
        data["status_code"] = status_code

    data["retryable"] = bool(getattr(result, "retryable", False))
    data["submission_uncertain"] = bool(getattr(result, "submission_uncertain", False))

    provider_status = _safe_code(getattr(result, "provider_status", None))
    if provider_status:
        data["provider_status"] = provider_status

    provider_error_code = _safe_code(getattr(result, "provider_error_code", None))
    if provider_error_code:
        data["provider_error_code"] = provider_error_code

    provider_credits = _safe_nonnegative_number(getattr(result, "provider_credits", None))
    if provider_credits is not None:
        data["provider_credits"] = provider_credits

    return data
