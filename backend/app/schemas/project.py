import uuid
from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, ConfigDict, Field


class ProjectCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    video_mode: str = "STORY"
    purpose: Optional[str] = None
    target_platform: Optional[str] = None
    target_duration_seconds: Optional[float] = Field(default=None, gt=0.0)
    preferred_aspect_ratio: Optional[str] = None
    mode_config: Optional[Any] = None
    default_config: Optional[Any] = None


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    description: Optional[str] = None
    status: str
    video_mode: str
    purpose: Optional[str] = None
    target_platform: Optional[str] = None
    target_duration_seconds: Optional[float] = None
    preferred_aspect_ratio: Optional[str] = None
    mode_config: Optional[Any] = None
    default_config: Optional[Any] = None
    created_at: datetime
    updated_at: datetime
