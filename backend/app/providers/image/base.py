"""Provider-neutral Image Generation interface and request/response models."""
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field


class ReferenceImageInput(BaseModel):
    type: Literal["character", "location", "style", "first_frame", "last_frame", "reference"]
    url: str
    weight: Optional[float] = 1.0


class ImageGenerationParams(BaseModel):
    shot_id: str
    prompt: str
    negative_prompt: Optional[str] = None
    aspect_ratio: Literal["16:9", "9:16", "1:1", "4:3", "3:4"] = "16:9"
    seed: Optional[int] = None
    reference_images: Optional[List[ReferenceImageInput]] = None
    provider_specific_params: Optional[Dict[str, Any]] = None


class ImageJobResult(BaseModel):
    provider_job_id: str
    status: Literal["QUEUED", "PROCESSING", "COMPLETED", "FAILED", "CANCELLED"]
    image_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    image_data: Optional[bytes] = None
    content_type: str = "image/png"
    cost_usd: Optional[float] = None
    error_message: Optional[str] = None
    error_code: Optional[str] = None
    status_code: Optional[int] = None
    retryable: bool = False
    submission_uncertain: bool = False
    raw_response: Optional[Dict[str, Any]] = None


class IImageGenerationProviderAdapter(ABC):
    @property
    @abstractmethod
    def provider_id(self) -> str:
        """Unique provider identifier (e.g. 'mock_image', 'standard_image')"""
        pass

    @abstractmethod
    async def generate_image(self, params: ImageGenerationParams) -> ImageJobResult:
        """Submit image generation request or generate keyframe image."""
        pass

    @abstractmethod
    async def check_job_status(self, provider_job_id: str) -> ImageJobResult:
        """Check asynchronous job status if applicable."""
        pass

    @abstractmethod
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate provider adapter configuration / keys."""
        pass
