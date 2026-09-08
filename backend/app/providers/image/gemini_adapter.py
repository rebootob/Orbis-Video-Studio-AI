"""Gemini production ImageProvider adapter for Core V1 keyframes.

The adapter uses Google's synchronous Interactions image-generation API and
returns only canonical ImageJobResult fields. It never persists raw provider
bodies, API keys, or reference-image bytes.
"""
import base64
import math
import re
from typing import Any, Callable, Dict, Optional, Tuple
from urllib.parse import urlsplit

import httpx

from app.core.config import settings
from app.providers.image.base import (
    IImageGenerationProviderAdapter,
    ImageGenerationParams,
    ImageJobResult,
)
from app.providers.safety import contains_secret

ReferenceResolver = Callable[[str], Tuple[bytes, str]]

_SUPPORTED_ASPECT_RATIOS = {"16:9", "9:16", "1:1", "4:3", "3:4"}
_SUPPORTED_IMAGE_SIZES = {"512", "1K", "2K", "4K"}
_SUPPORTED_OUTPUT_MIME_TYPES = {"image/jpeg"}
_SUPPORTED_REFERENCE_MIME_TYPES = {"image/jpeg", "image/png", "image/webp"}
_MODEL_RE = re.compile(r"^gemini-[A-Za-z0-9.-]+-image(?:-preview)?$")


class GeminiImageProviderAdapter(IImageGenerationProviderAdapter):
    """Synchronous Gemini image adapter with fail-closed continuity handling."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
        image_size: Optional[str] = None,
        reference_resolver: Optional[ReferenceResolver] = None,
        **_: Any,
    ) -> None:
        self._api_key = settings.GEMINI_API_KEY if api_key is None else api_key
        self._base_url = (base_url or settings.GEMINI_IMAGE_BASE_URL).rstrip("/")
        self._model = model or settings.GEMINI_IMAGE_MODEL
        self._timeout_seconds = (
            settings.GEMINI_IMAGE_TIMEOUT_SECONDS if timeout_seconds is None else timeout_seconds
        )
        self._default_image_size = image_size or settings.GEMINI_IMAGE_SIZE
        self._reference_resolver = reference_resolver
        self._max_reference_count = int(settings.GEMINI_IMAGE_MAX_REFERENCE_COUNT)
        self._max_inline_reference_bytes = int(settings.GEMINI_IMAGE_MAX_INLINE_REFERENCE_BYTES)

    @property
    def provider_id(self) -> str:
        return "gemini_image"

    @property
    def model(self) -> str:
        return self._model

    def validate_config(self, config: Dict[str, Any]) -> bool:
        try:
            key = config.get("api_key", self._api_key)
            parsed = urlsplit(self._base_url)
            return bool(
                isinstance(key, str)
                and key.strip()
                and "\n" not in key
                and "\r" not in key
                and parsed.scheme == "https"
                and parsed.hostname
                and not parsed.username
                and not parsed.password
                and not parsed.query
                and not parsed.fragment
                and isinstance(self._model, str)
                and _MODEL_RE.fullmatch(self._model)
                and isinstance(self._timeout_seconds, (int, float))
                and math.isfinite(self._timeout_seconds)
                and 0 < float(self._timeout_seconds) <= 120
                and self._default_image_size in _SUPPORTED_IMAGE_SIZES
                and 1 <= self._max_reference_count <= 14
                and 0 < self._max_inline_reference_bytes <= 19 * 1024 * 1024
            )
        except (TypeError, ValueError):
            return False

    @staticmethod
    def _failure(
        code: str,
        *,
        status_code: Optional[int] = None,
        retryable: bool = False,
        uncertain: bool = False,
        job_id: str = "",
    ) -> ImageJobResult:
        return ImageJobResult(
            provider_job_id=job_id,
            status="FAILED",
            error_code=code,
            error_message=code,
            status_code=status_code,
            retryable=retryable,
            submission_uncertain=uncertain,
        )

    def _resolve_references(self, params: ImageGenerationParams):
        refs = params.reference_images or []
        if not refs:
            return []
        if len(refs) > self._max_reference_count or self._reference_resolver is None:
            raise ValueError("REFERENCE_INPUT_UNSUPPORTED")

        blocks = []
        total_bytes = 0
        for ref in refs:
            payload, mime_type = self._reference_resolver(ref.url)
            if not isinstance(payload, (bytes, bytearray)) or not payload:
                raise ValueError("REFERENCE_INPUT_INVALID")
            if mime_type not in _SUPPORTED_REFERENCE_MIME_TYPES:
                raise ValueError("REFERENCE_MIME_UNSUPPORTED")
            total_bytes += len(payload)
            if total_bytes > self._max_inline_reference_bytes:
                raise ValueError("REFERENCE_INPUT_TOO_LARGE")
            blocks.append(
                {
                    "type": "image",
                    "mime_type": mime_type,
                    "data": base64.b64encode(bytes(payload)).decode("ascii"),
                }
            )
        return blocks

    @staticmethod
    def _safe_prompt(params: ImageGenerationParams) -> Optional[str]:
        prompt = (params.prompt or "").strip()
        if not prompt or len(prompt) > 12000:
            return None
        if params.negative_prompt:
            negative = params.negative_prompt.strip()
            if len(negative) > 4000:
                return None
            if negative:
                prompt = f"{prompt}\n\nAvoid these visual elements or qualities: {negative}"
        return prompt

    @staticmethod
    def _extract_output(data: Any) -> Tuple[Optional[bytes], Optional[str], str]:
        if not isinstance(data, dict):
            return None, None, ""
        interaction_id = data.get("id") if isinstance(data.get("id"), str) else ""

        candidates = []
        direct = data.get("output_image")
        if isinstance(direct, dict):
            candidates.append(direct)
        for step in data.get("steps", []) if isinstance(data.get("steps"), list) else []:
            if not isinstance(step, dict):
                continue
            for block in step.get("content", []) if isinstance(step.get("content"), list) else []:
                if isinstance(block, dict) and block.get("type") == "image":
                    candidates.append(block)

        for block in reversed(candidates):
            encoded = block.get("data")
            mime_type = block.get("mime_type") or block.get("mimeType") or "image/jpeg"
            if not isinstance(encoded, str) or mime_type not in _SUPPORTED_OUTPUT_MIME_TYPES:
                continue
            try:
                decoded = base64.b64decode(encoded, validate=True)
            except Exception:
                continue
            if decoded:
                return decoded, mime_type, interaction_id
        return None, None, interaction_id

    async def generate_image(self, params: ImageGenerationParams) -> ImageJobResult:
        if not self.validate_config({}):
            return self._failure("INVALID_CONFIG")
        if contains_secret(params.model_dump()):
            return self._failure("INVALID_PARAMETERS")
        if params.aspect_ratio not in _SUPPORTED_ASPECT_RATIOS:
            return self._failure("UNSUPPORTED_ASPECT_RATIO")
        # Gemini Interactions image generation does not expose deterministic seed
        # semantics through this adapter; silently dropping a requested seed is forbidden.
        if params.seed is not None:
            return self._failure("UNSUPPORTED_SEED")

        extras = params.provider_specific_params or {}
        if set(extras) - {"image_size", "mime_type"}:
            return self._failure("UNSUPPORTED_PROVIDER_PARAMETERS")
        image_size = str(extras.get("image_size") or self._default_image_size)
        output_mime = str(extras.get("mime_type") or "image/jpeg")
        if image_size not in _SUPPORTED_IMAGE_SIZES or output_mime not in _SUPPORTED_OUTPUT_MIME_TYPES:
            return self._failure("INVALID_PARAMETERS")

        prompt = self._safe_prompt(params)
        if not prompt:
            return self._failure("INVALID_PARAMETERS")

        try:
            reference_blocks = self._resolve_references(params)
        except ValueError as exc:
            return self._failure(str(exc))
        except Exception:
            return self._failure("REFERENCE_RESOLUTION_FAILED")

        payload = {
            "model": self._model,
            "input": [*reference_blocks, {"type": "text", "text": prompt}],
            "response_format": {
                "type": "image",
                "mime_type": output_mime,
                "aspect_ratio": params.aspect_ratio,
                "image_size": image_size,
            },
        }
        headers = {
            "x-goog-api-key": self._api_key,
            "Content-Type": "application/json",
        }
        endpoint = f"{self._base_url}/interactions"

        try:
            async with httpx.AsyncClient(timeout=float(self._timeout_seconds)) as client:
                response = await client.post(endpoint, json=payload, headers=headers)
        except (httpx.ConnectError, httpx.ConnectTimeout, httpx.PoolTimeout):
            return self._failure("CONNECTION_ERROR", retryable=True)
        except (httpx.ReadTimeout, httpx.WriteTimeout, httpx.NetworkError):
            return self._failure("TRANSPORT_ERROR", retryable=True, uncertain=True)
        except Exception:
            return self._failure("TRANSPORT_ERROR", uncertain=True)

        if response.status_code not in (200, 201):
            retryable = response.status_code == 429 or response.status_code in (500, 502, 503, 504)
            return self._failure(
                "HTTP_ERROR",
                status_code=response.status_code,
                retryable=retryable,
                uncertain=response.status_code >= 500,
            )

        try:
            data = response.json()
        except Exception:
            return self._failure("INVALID_RESPONSE", uncertain=True)

        image_bytes, content_type, interaction_id = self._extract_output(data)
        if not image_bytes or not content_type:
            return self._failure("INVALID_RESPONSE", uncertain=False, job_id=interaction_id)

        # Provider billing is token-based and may include input image/text cost.
        # Do not invent an actual dollar amount here; core retains the pre-call
        # estimate until provider billing evidence is reconciled.
        return ImageJobResult(
            provider_job_id=interaction_id or f"gemini-sync-{params.shot_id}",
            status="COMPLETED",
            image_data=image_bytes,
            content_type=content_type,
            cost_usd=None,
            raw_response={
                "provider": self.provider_id,
                "model": self._model,
                "interaction_id": interaction_id or None,
                "aspect_ratio": params.aspect_ratio,
                "image_size": image_size,
                "reference_count": len(reference_blocks),
            },
        )

    async def check_job_status(self, provider_job_id: str) -> ImageJobResult:
        # This adapter uses the synchronous Interactions API. Core will only poll
        # providers that return QUEUED/PROCESSING; Gemini never does so here.
        return self._failure("ASYNC_STATUS_UNSUPPORTED", job_id=provider_job_id)
