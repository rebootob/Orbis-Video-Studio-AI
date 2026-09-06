"""Vidu v2 HTTP adapter; all provider failures leave this boundary as safe metadata.

Contract: https://platform.vidu.com/docs/text-to-video
          https://platform.vidu.com/docs/reference-to-video
Transport failures after a possible POST are ambiguous, never blind-retried.
"""
import math
import re
from urllib.parse import urlsplit, quote

import httpx
from app.core.config import settings
from app.providers.base import IVideoGenerationProviderAdapter, ProviderJobResult
from app.providers.safety import contains_secret, safe_url


class ViduProviderAdapter(IVideoGenerationProviderAdapter):
    def __init__(self, api_key=None, base_url=None, model=None, timeout_seconds=None):
        self._api_key = settings.VIDU_API_KEY if api_key is None else api_key
        self._base_url = (base_url or settings.VIDU_BASE_URL).rstrip("/")
        self._model = model or settings.VIDU_DEFAULT_MODEL
        self._timeout_seconds = settings.VIDU_TIMEOUT_SECONDS if timeout_seconds is None else timeout_seconds

    @property
    def provider_id(self):
        return "vidu"

    @property
    def model(self):
        return self._model

    def validate_config(self, config):
        try:
            url = urlsplit(self._base_url)
            key = config.get("api_key", self._api_key)
            return bool(isinstance(key, str) and key.strip() and "\n" not in key and "\r" not in key
                        and url.scheme == "https" and url.hostname and not url.username
                        and not url.password and not url.query and not url.fragment
                        and isinstance(self._model, str) and self._model
                        and math.isfinite(self._timeout_seconds) and 0 < self._timeout_seconds <= 60)
        except (ValueError, TypeError):
            return False

    def _get_headers(self):
        return {"Authorization": f"Token {self._api_key}", "Content-Type": "application/json"}

    def _failure(self, code, *, status_code=None, retryable=False, uncertain=False, job_id=""):
        return ProviderJobResult(provider_job_id=job_id, status="FAILED", error_code=code,
                                 error_message=code, status_code=status_code,
                                 retryable=retryable, submission_uncertain=uncertain)

    def _output_url(self, value):
        if isinstance(value, str) and self._api_key and self._api_key in value:
            return None
        return safe_url(value)

    def _result(self, data, job_id="", submitting=False):
        if not isinstance(data, dict):
            return self._failure("INVALID_RESPONSE", uncertain=submitting, job_id=job_id)
        state = str(data.get("state") or data.get("status") or "").lower()
        if state == "failed":
            return self._failure("PROVIDER_REJECTED", job_id=job_id)
        identity = data.get("task_id") or data.get("id") or job_id
        if not isinstance(identity, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,255}", identity):
            return self._failure("INVALID_RESPONSE", uncertain=submitting, job_id=job_id)
        if self._api_key and self._api_key in identity:
            return self._failure("INVALID_RESPONSE", uncertain=submitting, job_id=job_id)
        state = str(data.get("state") or data.get("status") or "").lower()
        states = {"created": "QUEUED", "queueing": "QUEUED", "queued": "QUEUED", "pending": "QUEUED",
                  "processing": "PROCESSING", "running": "PROCESSING", "success": "COMPLETED",
                  "completed": "COMPLETED", "failed": "FAILED", "cancelled": "CANCELLED", "canceled": "CANCELLED"}
        if state not in states:
            return self._failure("INVALID_RESPONSE", uncertain=submitting, job_id=identity)
        creations = data.get("creations")
        creation = creations[0] if isinstance(creations, list) and creations and isinstance(creations[0], dict) else {}
        # Never copy error text, nested data, or raw bodies into results/logs.
        return ProviderJobResult(provider_job_id=identity, status=states[state],
            video_url=self._output_url(creation.get("url")), thumbnail_url=self._output_url(creation.get("cover_url")),
            error_code="PROVIDER_REJECTED" if state == "failed" else None,
            error_message="PROVIDER_REJECTED" if state == "failed" else None)

    async def _request(self, method, path, *, payload=None, job_id="", submitting=False):
        if not self.validate_config({}):
            return self._failure("INVALID_CONFIG", job_id=job_id)
        try:
            async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
                response = await client.request(method, self._base_url + path,
                                                json=payload, headers=self._get_headers())
            if response.status_code not in (200, 201, 202):
                retryable = response.status_code == 429 or response.status_code in (500, 502, 503, 504)
                return self._failure("HTTP_ERROR", status_code=response.status_code, retryable=retryable,
                    uncertain=submitting and response.status_code >= 500, job_id=job_id)
            return self._result(response.json(), job_id=job_id, submitting=submitting)
        except (httpx.ConnectError, httpx.ConnectTimeout, httpx.PoolTimeout):
            return self._failure("CONNECTION_ERROR", retryable=True, job_id=job_id)
        except (httpx.TimeoutException, httpx.NetworkError):
            return self._failure("TRANSPORT_ERROR", retryable=True, uncertain=submitting, job_id=job_id)
        except Exception:
            return self._failure("INVALID_RESPONSE", uncertain=submitting, job_id=job_id)

    async def submit_generation_job(self, params):
        if not self.validate_config({}):
            return self._failure("INVALID_CONFIG")
        references = bool(params.reference_images)
        allowed_models = {"viduq2", "viduq1", "viduq3-turbo", "viduq3" if references else "viduq3-pro"}
        duration = params.duration_seconds
        extras = params.provider_specific_params or {}
        allowed_extras = {"resolution", "style", "movement_amplitude", "off_peak"}
        if (self._model not in allowed_models or not math.isfinite(duration) or not duration.is_integer()
                or not 1 <= duration <= (16 if "q3" in self._model else 10)
                or (self._model == "viduq1" and duration != 5)
                or not params.prompt.strip() or len(params.prompt) > 5000
                or contains_secret(params.model_dump()) or set(extras) - allowed_extras
                or any(not isinstance(v, (str, bool)) for v in extras.values())):
            return self._failure("INVALID_PARAMETERS")
        if references and (len(params.reference_images) > 7 or any(not safe_url(i.url) for i in params.reference_images)):
            return self._failure("INVALID_PARAMETERS")
        payload = {"model": self._model, "prompt": params.prompt, "duration": int(duration),
                   "aspect_ratio": params.aspect_ratio, **extras}
        if references:
            payload["images"] = [image.url for image in params.reference_images]
        if params.seed is not None:
            payload["seed"] = params.seed
        if params.camera_motion:
            if params.camera_motion.type not in ("auto", "small", "medium", "large"):
                return self._failure("INVALID_PARAMETERS")
            payload["movement_amplitude"] = params.camera_motion.type
        return await self._request("POST", "/reference2video" if references else "/text2video",
                                   payload=payload, submitting=True)

    async def check_job_status(self, provider_job_id):
        return await self._request("GET", f"/tasks/{quote(provider_job_id, safe='')}/creations", job_id=provider_job_id)

    async def cancel_job(self, provider_job_id):
        if not self.validate_config({}):
            return False
        try:
            async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
                response = await client.post(self._base_url + f"/tasks/{quote(provider_job_id, safe='')}/cancel",
                                             headers=self._get_headers(), json={"id": provider_job_id})
            return response.status_code in (200, 202, 204)
        except Exception:
            # Bool contract deliberately drops provider exceptions and response bodies.
            return False
