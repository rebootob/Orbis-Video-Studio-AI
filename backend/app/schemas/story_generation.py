import uuid
from datetime import datetime
from typing import Optional, List, Any, Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator


class StoryGenerateRequest(BaseModel):
    target_duration_seconds: float = Field(default=60.0, gt=0.0)
    tone: str = "cinematic"
    language: str = "th"
    target_audience: Optional[str] = None
    custom_instructions: Optional[str] = None
    profile: Literal["FAST", "BALANCED", "QUALITY"] = "BALANCED"
    generate_scenes: bool = True


class SceneGenerateRequest(BaseModel):
    custom_instructions: Optional[str] = None
    profile: Literal["FAST", "BALANCED", "QUALITY"] = "BALANCED"
    generate_shots: bool = True


class ShotGenerateRequest(BaseModel):
    custom_instructions: Optional[str] = None
    profile: Literal["FAST", "BALANCED", "QUALITY"] = "BALANCED"


class ShotResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    scene_id: uuid.UUID
    shot_number: int
    shot_type: str
    visual_prompt: Optional[str] = None
    image_prompt: Optional[str] = None
    video_prompt: Optional[str] = None
    camera: Optional[str] = None
    subject: Optional[str] = None
    action: Optional[str] = None
    duration_seconds: float
    is_locked: bool
    status: str


class SceneResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    story_id: Optional[uuid.UUID] = None
    scene_number: int
    heading: Optional[str] = None
    purpose: Optional[str] = None
    setting: Optional[str] = None
    duration_seconds: Optional[float] = None
    narration: Optional[str] = None
    dialogue: Optional[Any] = None
    is_locked: bool
    shots: List[ShotResponse] = Field(default_factory=list)

    @field_validator("shots", mode="before")
    @classmethod
    def filter_archived_shots(cls, v):
        if isinstance(v, list):
            return [sh for sh in v if getattr(sh, "status", None) != "ARCHIVED"]
        return v


class StoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    title: Optional[str] = None
    logline: Optional[str] = None
    synopsis: Optional[str] = None
    tone: Optional[str] = None
    target_duration_seconds: Optional[float] = None
    language: Optional[str] = None
    is_locked: bool
    status: str
    created_at: datetime
    updated_at: datetime
    scenes: List[SceneResponse] = Field(default_factory=list)

    @field_validator("scenes", mode="before")
    @classmethod
    def filter_archived_scenes(cls, v):
        if isinstance(v, list):
            return [s for s in v if not (getattr(s, "scene_config", None) or {}).get("archived")]
        return v
