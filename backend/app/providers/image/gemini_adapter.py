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
            numeric_rates = (
                settings.GEMINI_IMAGE_INPUT_COST_PER_MILLION_USD,
                settings.GEMINI_IMAGE_OUTPUT_TEXT_COST_PER_MILLION_USD,
                settings.GEMINI_IMAGE_OUTPUT_IMAGE_COST_PER_MILLION_USD,
            )
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
                and self._default_image_size == "1K"
                and 1 <= self._max_reference_count <= 14
                and 0 < self._max_inline_reference_bytes <= 19 * 1024 * 1024
                and all(isinstance(v, (int, float)) and math.isfinite(v) and v >= 0 for v in numeric_rates)
            )
        except (TypeError, ValueError):
            return False

    def _failure(
        self,
        code: str,
        *,
        status_code: Optional[int] = None,
        retryable: bool = False,
        uncertain: bool = False,
        job_id: str = "",
    ) -> ImageJobResult:
        sanitized_evidence = None
        if status_code is not None:
            sanitized_evidence = {
                "provider": self.provider_id,
                "model": self._model,
                "http_status": status_code,
                "error_code": code,
                "retryable": retryable,
                "submission_uncertain": uncertain,
            }
        return ImageJobResult(
            provider_job_id=job_id,
            status="FAILED",
            error_code=code,
            error_message=code,
            status_code=status_code,
            retryable=retryable,
            submission_uncertain=uncertain,
            raw_response=sanitized_evidence,
        )

    def _resolve_references(self, params: ImageGenerationParams):
        refs = params.reference_images or []
        if not refs:
            return []
        if len(refs) > self._max_reference_count:
            raise ValueError("REFERENCE_COUNT_UNSUPPORTED")

        character_count = sum(1 for ref in refs if ref.type == "character")
        location_count = sum(1 for ref in refs if ref.type == "location")
        if character_count > 4:
            raise ValueError("CHARACTER_REFERENCE_COUNT_UNSUPPORTED")
        if location_count > 10:
            raise ValueError("LOCATION_REFERENCE_COUNT_UNSUPPORTED")
        if character_count + location_count != len(refs):
            raise ValueError("REFERENCE_TYPE_UNSUPPORTED")

        if self._reference_resolver is not None:
            resolver = self._reference_resolver
        else:
            from app.services.image_generation.reference_materializer import materialize_reference_image

            resolver = lambda url: materialize_reference_image(url, params.shot_id)

        blocks = []
        total_bytes = 0
        for ref in refs:
            payload, mime_type = resolver(ref.url)
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

    @staticmethod
    def _usage_cost(data: Dict[str, Any]) -> Tuple[Optional[float], Optional[Dict[str, int]]]:
        usage = data.get("usage")
        if not isinstance(usage, dict):
            return None, None

        summary = {
            "input_tokens": 0,
            "output_text_tokens": 0,
            "output_image_tokens": 0,
            "thought_tokens": 0,
        }
        for row in usage.get("input_tokens_by_modality", []) if isinstance(usage.get("input_tokens_by_modality"), list) else []:
            if isinstance(row, dict) and isinstance(row.get("tokens"), int) and row["tokens"] >= 0:
                summary["input_tokens"] += row["tokens"]
        for row in usage.get("output_tokens_by_modality", []) if isinstance(usage.get("output_tokens_by_modality"), list) else []:
            if not isinstance(row, dict) or not isinstance(row.get("tokens"), int) or row["tokens"] < 0:
                continue
            if row.get("modality") == "image":
                summary["output_image_tokens"] += row["tokens"]
            else:
                summary["output_text_tokens"] += row["tokens"]
        thought_tokens = usage.get("total_thought_tokens")
        if isinstance(thought_tokens, int) and thought_tokens >= 0:
            summary["thought_tokens"] = thought_tokens

        if summary["output_image_tokens"] <= 0:
            return None, summary

        text_and_thinking_tokens = summary["output_text_tokens"] + summary["thought_tokens"]
        cost = (
            summary["input_tokens"] * float(settings.GEMINI_IMAGE_INPUT_COST_PER_MILLION_USD)
            + text_and_thinking_tokens * float(settings.GEMINI_IMAGE_OUTPUT_TEXT_COST_PER_MILLION_USD)
            + summary["output_image_tokens"] * float(settings.GEMINI_IMAGE_OUTPUT_IMAGE_COST_PER_MILLION_USD)
        ) / 1_000_000.0
        return round(cost, 6), summary

    async def generate_image(self, params: ImageGenerationParams) -> ImageJobResult:
        if not self.validate_config({}):
            return self._failure("INVALID_CONFIG")
        if contains_secret(params.model_dump()):
            return self._failure("INVALID_PARAMETERS")
        if params.aspect_ratio not in _SUPPORTED_ASPECT_RATIOS:
            return self._failure("UNSUPPORTED_ASPECT_RATIO")
        if params.seed is not None:
            return self._failure("UNSUPPORTED_SEED")

        extras = params.provider_specific_params or {}
        if set(extras) - {"mime_type"}:
            return self._failure("UNSUPPORTED_PROVIDER_PARAMETERS")
        image_size = self._default_image_size
        output_mime = str(extras.get("mime_type") or "image/jpeg")
        if output_mime not in _SUPPORTED_OUTPUT_MIME_TYPES:
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

        cost_usd, usage_summary = self._usage_cost(data)
        if cost_usd is None:
            return ImageJobResult(
                provider_job_id=interaction_id or f"gemini-sync-{params.shot_id}",
                status="COMPLETED",
                image_data=image_bytes,
                content_type=content_type,
                error_code="COST_EVIDENCE_MISSING",
                error_message="COST_EVIDENCE_MISSING",
                submission_uncertain=True,
                raw_response={
                    "provider": self.provider_id,
                    "model": self._model,
                    "interaction_id": interaction_id or None,
                    "usage_summary": usage_summary,
                },
            )

        return ImageJobResult(
            provider_job_id=interaction_id or f"gemini-sync-{params.shot_id}",
            status="COMPLETED",
            image_data=image_bytes,
            content_type=content_type,
            cost_usd=cost_usd,
            raw_response={
                "provider": self.provider_id,
                "model": self._model,
                "interaction_id": interaction_id or None,
                "aspect_ratio": params.aspect_ratio,
                "image_size": image_size,
                "reference_count": len(reference_blocks),
                "usage_summary": usage_summary,
            },
        )

    async def check_job_status(self, provider_job_id: str) -> ImageJobResult:
        return self._failure("ASYNC_STATUS_UNSUPPORTED", job_id=provider_job_id)
