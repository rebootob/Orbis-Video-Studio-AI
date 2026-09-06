"""Provider-neutral Audio Generation interface and request/response models."""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, Literal, List
from pydantic import BaseModel, Field


class AudioProviderCapabilities(BaseModel):
    provider_id: str
    supported_audio_types: List[str] = Field(
        default_factory=lambda: ["VO", "DIALOGUE", "BGM", "SFX", "AMBIENCE"]
    )
    supports_tts: bool = True
    supports_music: bool = True
    supports_sfx: bool = True
    supports_voice_cloning: bool = False
    supported_formats: List[str] = Field(
        default_factory=lambda: ["audio/wav", "audio/mpeg"]
    )


class AudioGenerationParams(BaseModel):
    clip_id: str
    audio_type: Literal["ORIGINAL_AUDIO", "VO", "DIALOGUE", "BGM", "SFX", "AMBIENCE"]
    prompt: str
    negative_prompt: Optional[str] = None
    duration_seconds: Optional[float] = 4.0
    voice_id: Optional[str] = None
    language: Optional[str] = "en"
    speaker: Optional[str] = None
    intensity: Optional[str] = None
    provider_specific_params: Optional[Dict[str, Any]] = None


class AudioJobResult(BaseModel):
    provider_job_id: str
    status: Literal["QUEUED", "PROCESSING", "COMPLETED", "FAILED", "CANCELLED"]
    audio_url: Optional[str] = None
    audio_data: Optional[bytes] = None
    content_type: str = "audio/wav"
    duration_seconds: Optional[float] = None
    cost_usd: Optional[float] = None
    error_message: Optional[str] = None
    error_code: Optional[str] = None
    status_code: Optional[int] = None
    retryable: bool = False
    submission_uncertain: bool = False
    progress_percentage: Optional[float] = None
    raw_response: Optional[Dict[str, Any]] = None


class IAudioProviderAdapter(ABC):
    @property
    @abstractmethod
    def provider_id(self) -> str:
        """Unique provider identifier (e.g. 'mock_audio')"""
        pass

    @abstractmethod
    def get_capabilities(self) -> AudioProviderCapabilities:
        """Return provider capabilities (types, tts, music, sfx, etc.)."""
        pass

    @abstractmethod
    async def generate_audio(self, params: AudioGenerationParams) -> AudioJobResult:
        """Submit audio generation request or generate audio asset."""
        pass

    @abstractmethod
    async def check_job_status(self, provider_job_id: str) -> AudioJobResult:
        """Check asynchronous job status if applicable."""
        pass

    @abstractmethod
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate provider adapter configuration / keys."""
        pass
