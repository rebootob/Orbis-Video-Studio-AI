"""Mock / default Image Generation Provider Adapter for storyboard keyframes."""
import hashlib
import uuid
from typing import Dict, Any, Optional
from app.providers.image.base import (
    IImageGenerationProviderAdapter,
    ImageGenerationParams,
    ImageJobResult,
)


class MockImageProviderAdapter(IImageGenerationProviderAdapter):
    """Provider-neutral mock adapter generating deterministic, self-contained keyframe images."""

    def __init__(self, **kwargs: Any):
        self._config = kwargs

    @property
    def provider_id(self) -> str:
        return "mock_image"

    def validate_config(self, config: Dict[str, Any]) -> bool:
        return True

    async def generate_image(self, params: ImageGenerationParams) -> ImageJobResult:
        # Simulate network / provider failure if instructed via provider_specific_params
        extra = params.provider_specific_params or {}
        if extra.get("simulate_failure"):
            return ImageJobResult(
                provider_job_id=f"img-fail-{uuid.uuid4().hex[:8]}",
                status="FAILED",
                error_message=extra.get("failure_message", "Simulated image provider failure"),
                error_code="PROVIDER_ERROR",
                retryable=True,
            )
        if extra.get("simulate_reconciliation"):
            return ImageJobResult(
                provider_job_id=f"img-recon-{uuid.uuid4().hex[:8]}",
                status="QUEUED",
                submission_uncertain=True,
                error_message="Simulated ambiguous provider response",
                error_code="SUBMISSION_UNCERTAIN",
            )
        if extra.get("simulate_async"):
            return ImageJobResult(
                provider_job_id=f"img-async-{uuid.uuid4().hex[:8]}",
                status="QUEUED",
                cost_usd=0.04,
                raw_response={"simulated_async": True, "shot_id": params.shot_id},
            )

        # Deterministic generation
        prompt_hash = hashlib.sha256(params.prompt.encode("utf-8")).hexdigest()[:12]
        seed_val = params.seed if params.seed is not None else int(prompt_hash[:6], 16) % 1000000
        provider_job_id = f"img-{prompt_hash}-{uuid.uuid4().hex[:6]}"

        # Create a lightweight deterministic SVG image representation
        aspect_ratio = params.aspect_ratio or "16:9"
        width, height = 1280, 720
        if aspect_ratio == "9:16":
            width, height = 720, 1280
        elif aspect_ratio == "1:1":
            width, height = 1024, 1024

        escaped_prompt = (
            params.prompt[:80].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        )
        bg_color = f"#{prompt_hash[:6]}"
        svg_content = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <rect width="100%" height="100%" fill="{bg_color}" />
  <rect x="20" y="20" width="{width - 40}" height="{height - 40}" fill="#0f172a" opacity="0.85" rx="16" />
  <text x="50" y="80" fill="#38bdf8" font-family="sans-serif" font-size="28" font-weight="bold">Orbis Keyframe Blueprint</text>
  <text x="50" y="130" fill="#94a3b8" font-family="sans-serif" font-size="18">Shot: {params.shot_id} | Aspect: {aspect_ratio} | Seed: {seed_val}</text>
  <text x="50" y="180" fill="#e2e8f0" font-family="sans-serif" font-size="20" font-weight="500">{escaped_prompt}...</text>
</svg>"""

        image_bytes = svg_content.encode("utf-8")

        return ImageJobResult(
            provider_job_id=provider_job_id,
            status="COMPLETED",
            image_url=f"/mock-images/{provider_job_id}.svg",
            thumbnail_url=f"/mock-images/{provider_job_id}-thumb.svg",
            image_data=image_bytes,
            content_type="image/svg+xml",
            cost_usd=0.04,
            raw_response={
                "provider": self.provider_id,
                "seed": seed_val,
                "aspect_ratio": aspect_ratio,
                "prompt_hash": prompt_hash,
            },
        )

    async def check_job_status(self, provider_job_id: str) -> ImageJobResult:
        # Deterministic completed SVG representation for polled asynchronous job
        prompt_hash = hashlib.sha256(provider_job_id.encode("utf-8")).hexdigest()[:12]
        bg_color = f"#{prompt_hash[:6]}"
        svg_content = f"""<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="720" viewBox="0 0 1280 720">
  <rect width="100%" height="100%" fill="{bg_color}" />
  <rect x="20" y="20" width="1240" height="680" fill="#0f172a" opacity="0.85" rx="16" />
  <text x="50" y="80" fill="#38bdf8" font-family="sans-serif" font-size="28" font-weight="bold">Orbis Keyframe Blueprint</text>
  <text x="50" y="130" fill="#94a3b8" font-family="sans-serif" font-size="18">Polled Job: {provider_job_id}</text>
</svg>"""
        return ImageJobResult(
            provider_job_id=provider_job_id,
            status="COMPLETED",
            image_url=f"/mock-images/{provider_job_id}.svg",
            image_data=svg_content.encode("utf-8"),
            content_type="image/svg+xml",
            cost_usd=0.04,
            raw_response={"polled": True, "provider_job_id": provider_job_id},
        )
