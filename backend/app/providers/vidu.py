import logging
import re
import httpx
from typing import Dict, Any, Optional, List
from app.providers.base import (
    IVideoGenerationProviderAdapter,
    VideoGenerationParams,
    ProviderJobResult,
)
from app.core.config import settings

logger = logging.getLogger(__name__)


class ViduProviderAdapter(IVideoGenerationProviderAdapter):
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
    ):
        self._api_key = api_key if api_key is not None else settings.VIDU_API_KEY
        self._base_url = (base_url or settings.VIDU_BASE_URL).rstrip("/")
        self._model = model or getattr(settings, "VIDU_DEFAULT_MODEL", "viduq2-pro")
        self._timeout_seconds = timeout_seconds or settings.VIDU_TIMEOUT_SECONDS

    @property
    def provider_id(self) -> str:
        return "vidu"

    @property
    def model(self) -> str:
        return self._model

    def validate_config(self, config: Dict[str, Any]) -> bool:
        api_key = config.get("api_key") or self._api_key
        return bool(api_key and isinstance(api_key, str) and len(api_key.strip()) > 0)

    def _get_headers(self) -> Dict[str, str]:
        # Official Vidu API uses Token {api_key}
        return {
            "Authorization": f"Token {self._api_key}",
            "Content-Type": "application/json",
        }

    def _sanitize_error(self, text: str) -> str:
        if not text:
            return ""
        # Redact any authorization tokens or API keys
        sanitized = re.sub(
            r'(Token|Bearer|key|api_key|secret|password)\s*[:=]?\s*[A-Za-z0-9_\-\.]+',
            r'\1 [REDACTED]',
            text,
            flags=re.IGNORECASE,
        )
        if self._api_key and len(self._api_key) > 4 and self._api_key in sanitized:
            sanitized = sanitized.replace(self._api_key, "[REDACTED]")
        return sanitized

    def _sanitize_response_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Safely extract provider response fields without persisting raw auth or unverified blobs."""
        safe_keys = ["id", "task_id", "state", "status", "progress", "err_code", "error_message"]
        out = {k: data[k] for k in safe_keys if k in data}
        if "creations" in data and isinstance(data["creations"], list):
            out["creations"] = [
                {
                    "id": c.get("id"),
                    "url": c.get("url"),
                    "cover_url": c.get("cover_url"),
                }
                for c in data["creations"]
                if isinstance(c, dict)
            ]
        if "video_url" in data:
            out["video_url"] = data["video_url"]
        if "thumbnail_url" in data:
            out["thumbnail_url"] = data["thumbnail_url"]
        return out

    async def submit_generation_job(self, params: VideoGenerationParams) -> ProviderJobResult:
        if not self.validate_config({}):
            return ProviderJobResult(
                provider_job_id="",
                status="FAILED",
                error_message="Vidu API key missing or invalid configuration",
            )

        has_references = bool(params.reference_images and len(params.reference_images) > 0)
        endpoint = f"{self._base_url}/reference2video" if has_references else f"{self._base_url}/text2video"

        # Explicit mapping according to Vidu API
        payload: Dict[str, Any] = {
            "model": self._model,
            "prompt": params.prompt,
            "duration": int(params.duration_seconds),
            "aspect_ratio": params.aspect_ratio,
        }

        if has_references and params.reference_images:
            payload["images"] = [img.url for img in params.reference_images]

        if params.seed is not None:
            payload["seed"] = params.seed

        if params.camera_motion:
            payload["movement_amplitude"] = params.camera_motion.type

        if params.provider_specific_params:
            for k, v in params.provider_specific_params.items():
                if k not in ("api_key", "authorization", "token", "headers"):
                    payload[k] = v

        headers = self._get_headers()

        try:
            async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
                response = await client.post(
                    endpoint,
                    json=payload,
                    headers=headers,
                )

                if response.status_code not in (200, 201, 202):
                    sanitized_err = self._sanitize_error(response.text)
                    return ProviderJobResult(
                        provider_job_id="",
                        status="FAILED",
                        error_message=f"Vidu API HTTP {response.status_code}: {sanitized_err}",
                        raw_response={"status_code": response.status_code, "error": sanitized_err[:500]},
                    )

                data = response.json()
                job_id = str(data.get("task_id") or data.get("id") or "")
                raw_status = str(data.get("state") or data.get("status") or "QUEUED").upper()

                status_map = {
                    "CREATED": "QUEUED",
                    "QUEUEING": "QUEUED",
                    "QUEUED": "QUEUED",
                    "PENDING": "QUEUED",
                    "PROCESSING": "PROCESSING",
                    "RUNNING": "PROCESSING",
                    "SUCCESS": "COMPLETED",
                    "COMPLETED": "COMPLETED",
                    "FAILED": "FAILED",
                }
                mapped_status = status_map.get(raw_status, "QUEUED")

                video_url = None
                thumbnail_url = None
                creations = data.get("creations")
                if creations and isinstance(creations, list) and len(creations) > 0:
                    video_url = creations[0].get("url")
                    thumbnail_url = creations[0].get("cover_url")
                if not video_url:
                    video_url = data.get("video_url") or data.get("url")
                if not thumbnail_url:
                    thumbnail_url = data.get("thumbnail_url")

                return ProviderJobResult(
                    provider_job_id=job_id,
                    status=mapped_status,
                    progress_percentage=float(data.get("progress", 0.0)),
                    video_url=video_url,
                    thumbnail_url=thumbnail_url,
                    cost_usd=data.get("cost_usd"),
                    raw_response=self._sanitize_response_data(data),
                )
        except Exception as exc:
            sanitized_exc = self._sanitize_error(str(exc))
            logger.error(f"Vidu submit_generation_job exception: {sanitized_exc}")
            return ProviderJobResult(
                provider_job_id="",
                status="FAILED",
                error_message=f"Vidu client request failed: {sanitized_exc}",
            )

    async def check_job_status(self, provider_job_id: str) -> ProviderJobResult:
        if not self.validate_config({}):
            return ProviderJobResult(
                provider_job_id=provider_job_id,
                status="FAILED",
                error_message="Vidu API key missing or invalid configuration",
            )

        headers = self._get_headers()
        endpoint = f"{self._base_url}/tasks/{provider_job_id}/creations"

        try:
            async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
                response = await client.get(
                    endpoint,
                    headers=headers,
                )

                if response.status_code != 200:
                    sanitized_err = self._sanitize_error(response.text)
                    return ProviderJobResult(
                        provider_job_id=provider_job_id,
                        status="FAILED",
                        error_message=f"Vidu API HTTP {response.status_code}: {sanitized_err}",
                        raw_response={"status_code": response.status_code, "error": sanitized_err[:500]},
                    )

                data = response.json()
                raw_status = str(data.get("state") or data.get("status") or "PROCESSING").upper()

                status_map = {
                    "CREATED": "QUEUED",
                    "QUEUEING": "QUEUED",
                    "QUEUED": "QUEUED",
                    "PENDING": "QUEUED",
                    "PROCESSING": "PROCESSING",
                    "RUNNING": "PROCESSING",
                    "SUCCESS": "COMPLETED",
                    "COMPLETED": "COMPLETED",
                    "FAILED": "FAILED",
                }
                mapped_status = status_map.get(raw_status, "PROCESSING")

                video_url = None
                thumbnail_url = None
                creations = data.get("creations")
                if creations and isinstance(creations, list) and len(creations) > 0:
                    video_url = creations[0].get("url")
                    thumbnail_url = creations[0].get("cover_url")
                if not video_url:
                    video_url = data.get("video_url") or data.get("url")
                if not thumbnail_url:
                    thumbnail_url = data.get("thumbnail_url")

                err_msg = (
                    data.get("error_message")
                    or data.get("err")
                    or (str(data.get("err_code")) if data.get("err_code") else None)
                )
                if err_msg:
                    err_msg = self._sanitize_error(str(err_msg))

                return ProviderJobResult(
                    provider_job_id=provider_job_id,
                    status=mapped_status,
                    progress_percentage=float(data.get("progress", 0.0)),
                    video_url=video_url,
                    thumbnail_url=thumbnail_url,
                    cost_usd=data.get("cost_usd"),
                    error_message=err_msg,
                    raw_response=self._sanitize_response_data(data),
                )
        except Exception as exc:
            sanitized_exc = self._sanitize_error(str(exc))
            logger.error(f"Vidu check_job_status exception: {sanitized_exc}")
            return ProviderJobResult(
                provider_job_id=provider_job_id,
                status="FAILED",
                error_message=f"Vidu client check status failed: {sanitized_exc}",
            )

    async def cancel_job(self, provider_job_id: str) -> bool:
        if not self.validate_config({}):
            return False

        headers = self._get_headers()
        endpoint = f"{self._base_url}/tasks/{provider_job_id}/cancel"

        try:
            async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
                response = await client.post(
                    endpoint,
                    headers=headers,
                )
                return response.status_code in (200, 202, 204)
        except Exception as exc:
            sanitized_exc = self._sanitize_error(str(exc))
            logger.error(f"Vidu cancel_job exception: {sanitized_exc}")
            return False
