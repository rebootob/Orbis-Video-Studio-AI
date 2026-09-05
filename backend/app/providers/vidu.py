import logging
import httpx
from typing import Dict, Any, Optional
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
        timeout_seconds: Optional[float] = None,
    ):
        self._api_key = api_key or settings.VIDU_API_KEY
        self._base_url = (base_url or settings.VIDU_BASE_URL).rstrip("/")
        self._timeout_seconds = timeout_seconds or settings.VIDU_TIMEOUT_SECONDS

    @property
    def provider_id(self) -> str:
        return "vidu"

    def validate_config(self, config: Dict[str, Any]) -> bool:
        api_key = config.get("api_key") or self._api_key
        return bool(api_key and isinstance(api_key, str) and len(api_key.strip()) > 0)

    def _get_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    async def submit_generation_job(self, params: VideoGenerationParams) -> ProviderJobResult:
        if not self.validate_config({}):
            return ProviderJobResult(
                provider_job_id="",
                status="FAILED",
                error_message="Vidu API key missing or invalid configuration",
            )

        payload: Dict[str, Any] = {
            "prompt": params.prompt,
            "aspect_ratio": params.aspect_ratio,
            "duration": params.duration_seconds,
        }

        if params.negative_prompt:
            payload["negative_prompt"] = params.negative_prompt
        if params.seed is not None:
            payload["seed"] = params.seed
        if params.reference_images:
            payload["images"] = [
                {"type": img.type, "url": img.url, "weight": img.weight}
                for img in params.reference_images
            ]
        if params.camera_motion:
            payload["camera_motion"] = {
                "type": params.camera_motion.type,
                "intensity": params.camera_motion.intensity,
            }
        if params.provider_specific_params:
            payload.update(params.provider_specific_params)

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
                response = await client.post(
                    f"{self._base_url}/tasks",
                    json=payload,
                    headers=headers,
                )

                if response.status_code not in (200, 201, 202):
                    return ProviderJobResult(
                        provider_job_id="",
                        status="FAILED",
                        error_message=f"Vidu API HTTP {response.status_code}: {response.text}",
                        raw_response={"status_code": response.status_code, "body": response.text},
                    )

                data = response.json()
                job_id = str(data.get("id") or data.get("task_id") or "")
                raw_status = str(data.get("state") or data.get("status") or "QUEUED").upper()

                status_map = {
                    "CREATED": "QUEUED",
                    "QUEUED": "QUEUED",
                    "PENDING": "QUEUED",
                    "PROCESSING": "PROCESSING",
                    "RUNNING": "PROCESSING",
                    "SUCCESS": "COMPLETED",
                    "COMPLETED": "COMPLETED",
                    "FAILED": "FAILED",
                }
                mapped_status = status_map.get(raw_status, "QUEUED")

                return ProviderJobResult(
                    provider_job_id=job_id,
                    status=mapped_status,
                    progress_percentage=float(data.get("progress", 0.0)),
                    video_url=data.get("video_url") or data.get("url"),
                    thumbnail_url=data.get("thumbnail_url"),
                    cost_usd=data.get("cost_usd"),
                    raw_response=data,
                )
        except Exception as exc:
            logger.exception("Vidu submit_generation_job exception")
            return ProviderJobResult(
                provider_job_id="",
                status="FAILED",
                error_message=f"Vidu client request failed: {str(exc)}",
            )

    async def check_job_status(self, provider_job_id: str) -> ProviderJobResult:
        if not self.validate_config({}):
            return ProviderJobResult(
                provider_job_id=provider_job_id,
                status="FAILED",
                error_message="Vidu API key missing or invalid configuration",
            )

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
                response = await client.get(
                    f"{self._base_url}/tasks/{provider_job_id}",
                    headers=headers,
                )

                if response.status_code != 200:
                    return ProviderJobResult(
                        provider_job_id=provider_job_id,
                        status="FAILED",
                        error_message=f"Vidu API HTTP {response.status_code}: {response.text}",
                        raw_response={"status_code": response.status_code, "body": response.text},
                    )

                data = response.json()
                raw_status = str(data.get("state") or data.get("status") or "PROCESSING").upper()

                status_map = {
                    "CREATED": "QUEUED",
                    "QUEUED": "QUEUED",
                    "PENDING": "QUEUED",
                    "PROCESSING": "PROCESSING",
                    "RUNNING": "PROCESSING",
                    "SUCCESS": "COMPLETED",
                    "COMPLETED": "COMPLETED",
                    "FAILED": "FAILED",
                }
                mapped_status = status_map.get(raw_status, "PROCESSING")

                return ProviderJobResult(
                    provider_job_id=provider_job_id,
                    status=mapped_status,
                    progress_percentage=float(data.get("progress", 0.0)),
                    video_url=data.get("video_url") or data.get("url"),
                    thumbnail_url=data.get("thumbnail_url"),
                    cost_usd=data.get("cost_usd"),
                    error_message=data.get("error_message") or data.get("err"),
                    raw_response=data,
                )
        except Exception as exc:
            logger.exception("Vidu check_job_status exception")
            return ProviderJobResult(
                provider_job_id=provider_job_id,
                status="FAILED",
                error_message=f"Vidu client check status failed: {str(exc)}",
            )

    async def cancel_job(self, provider_job_id: str) -> bool:
        if not self.validate_config({}):
            return False

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
                response = await client.post(
                    f"{self._base_url}/tasks/{provider_job_id}/cancel",
                    headers=headers,
                )
                return response.status_code in (200, 202, 204)
        except Exception as exc:
            logger.exception("Vidu cancel_job exception")
            return False
