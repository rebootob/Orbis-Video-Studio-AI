"""Provider-neutral persistence boundary. Never retain raw provider bodies."""
import re
import math
from urllib.parse import urlsplit, parse_qsl
from app.core.config import settings

SECRET_KEY = re.compile(r"api.?key|authorization|token|secret|password|credential", re.I)


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


def safe_result(result):
    if result is None:
        return None
    # Deliberately omit raw_response, error_message and arbitrary nested data.
    # Allowlist safe provider fields
    data = {
        "status": result.status,
        "video_url": safe_url(getattr(result, "video_url", None)),
        "thumbnail_url": safe_url(getattr(result, "thumbnail_url", None)),
    }
    progress = result.progress_percentage
    if isinstance(progress, (int, float)) and math.isfinite(progress) and 0 <= progress <= 100:
        data["progress_percentage"] = progress
    return data
