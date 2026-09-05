from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field


class ReferenceImageInput(BaseModel):
    type: Literal["character", "location", "style", "first_frame", "last_frame"]
    url: str
    weight: Optional[float] = 1.0


class CameraMotionInput(BaseModel):
    type: str
    intensity: float = 1.0


class VideoGenerationParams(BaseModel):
    shot_id: str
    prompt: str
    negative_prompt: Optional[str] = None
    aspect_ratio: Literal["16:9", "9:16", "1:1"] = "16:9"
    duration_seconds: float = 4.0
    seed: Optional[int] = None
    reference_images: Optional[List[ReferenceImageInput]] = None
    camera_motion: Optional[CameraMotionInput] = None
    provider_specific_params: Optional[Dict[str, Any]] = None


class ProviderJobResult(BaseModel):
    provider_job_id: str
    status: Literal["QUEUED", "PROCESSING", "COMPLETED", "FAILED"]
    progress_percentage: Optional[float] = 0.0
    video_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    cost_usd: Optional[float] = None
    error_message: Optional[str] = None
    raw_response: Optional[Dict[str, Any]] = None


class IVideoGenerationProviderAdapter(ABC):
    @property
    @abstractmethod
    def provider_id(self) -> str:
        """Returns provider identifier, e.g. 'vidu'"""
        pass

    @abstractmethod
    async def submit_generation_job(self, params: VideoGenerationParams) -> ProviderJobResult:
        """Submit job to third party provider."""
        pass

    @abstractmethod
    async def check_job_status(self, provider_job_id: str) -> ProviderJobResult:
        """Query current job status from third party provider."""
        pass

    @abstractmethod
    async def cancel_job(self, provider_job_id: str) -> bool:
        """Cancel running job at third party provider."""
        pass

    @abstractmethod
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate adapter settings / API keys."""
        pass
