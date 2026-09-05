import uuid
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, ConfigDict, Field


class CreativeGenerationError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


class GenerationRequestOptions(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    profile: Literal["FAST", "BALANCED", "QUALITY"] = "BALANCED"
    model_override: Optional[str] = None
    timeout_seconds: Optional[float] = None
    max_retries: Optional[int] = None


class GeneratedShotDTO(BaseModel):
    shot_number: int = Field(..., ge=1)
    description: str
    camera: Optional[str] = "Medium shot, eye level, neutral motion"
    subject: Optional[str] = None
    action: Optional[str] = None
    duration_seconds: float = Field(default=4.0, gt=0.0)
    image_prompt: str
    video_prompt: str


class GeneratedSceneDTO(BaseModel):
    scene_number: int = Field(..., ge=1)
    title: str = Field(description="Scene heading, e.g. INT. RESEARCH LAB - DAY")
    purpose: Optional[str] = None
    setting: Optional[str] = None
    duration_seconds: float = Field(default=15.0, gt=0.0)
    narration: Optional[str] = None
    dialogue: Optional[List[Dict[str, str]]] = Field(default_factory=list)
    shots: List[GeneratedShotDTO] = Field(default_factory=list)


class GeneratedStoryDTO(BaseModel):
    title: str
    logline: str
    synopsis: str
    tone: Optional[str] = "cinematic"
    target_duration_seconds: float = Field(default=60.0, gt=0.0)
    language: str = "en"
    scenes: List[GeneratedSceneDTO] = Field(default_factory=list)


class ProviderGenerationResult(BaseModel):
    provider: str
    model: str
    input_character_count: int = 0
    output_character_count: int = 0
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    duration_ms: float
    data: Any


class CreativeGenerationProvider(ABC):
    """Abstract interface for LLM-based creative generation providers (OpenAI, Fakes, etc.)."""

    @abstractmethod
    def generate_story(
        self,
        prompt: str,
        options: Optional[GenerationRequestOptions] = None,
    ) -> ProviderGenerationResult:
        """Generate full structured story (Story + Scenes + Shots)."""
        pass

    @abstractmethod
    def generate_scenes(
        self,
        prompt: str,
        options: Optional[GenerationRequestOptions] = None,
    ) -> ProviderGenerationResult:
        """Generate structured scene list for an existing story context."""
        pass

    @abstractmethod
    def generate_shots(
        self,
        prompt: str,
        options: Optional[GenerationRequestOptions] = None,
    ) -> ProviderGenerationResult:
        """Generate structured shot list for an existing scene context."""
        pass
