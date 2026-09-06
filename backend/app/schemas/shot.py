import uuid
from datetime import datetime
from typing import Optional, List, Any, Dict
from pydantic import BaseModel, ConfigDict, Field


class ShotCreateRequest(BaseModel):
    shot_number: int = Field(..., ge=1)
    shot_type: str = Field(default="AI_GENERATED", description="AI_GENERATED, IMPORTED_VIDEO, IMPORTED_IMAGE, RECORDED_FOOTAGE, STOCK_ASSET, MIXED")
    source_asset_id: Optional[uuid.UUID] = None
    source_metadata: Optional[Dict[str, Any]] = None
    provider_config: Optional[Dict[str, Any]] = None
    visual_prompt: Optional[str] = None
    image_prompt: Optional[str] = None
    video_prompt: Optional[str] = None
    camera: Optional[str] = None
    subject: Optional[str] = None
    action: Optional[str] = None
    duration_seconds: float = Field(default=4.0, gt=0.0)


class ShotUpdateRequest(BaseModel):
    shot_type: Optional[str] = None
    source_asset_id: Optional[uuid.UUID] = None
    source_metadata: Optional[Dict[str, Any]] = None
    provider_config: Optional[Dict[str, Any]] = None
    visual_prompt: Optional[str] = None
    image_prompt: Optional[str] = None
    video_prompt: Optional[str] = None
    camera: Optional[str] = None
    subject: Optional[str] = None
    action: Optional[str] = None
    duration_seconds: Optional[float] = Field(default=None, gt=0.0)


class ShotDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    scene_id: uuid.UUID
    shot_number: int
    shot_type: str
    source_asset_id: Optional[uuid.UUID] = None
    source_metadata: Optional[Dict[str, Any]] = None
    provider_config: Optional[Dict[str, Any]] = None
    visual_prompt: Optional[str] = None
    image_prompt: Optional[str] = None
    video_prompt: Optional[str] = None
    camera: Optional[str] = None
    subject: Optional[str] = None
    action: Optional[str] = None
    duration_seconds: float
    is_locked: bool
    status: str
    created_at: datetime
    updated_at: datetime


class EffectiveShotConfigResponse(BaseModel):
    shot_id: uuid.UUID
    scene_id: uuid.UUID
    project_id: uuid.UUID
    resolved_aspect_ratio: str
    resolved_duration_seconds: float
    effective_config: Dict[str, Any]


class SceneCreateRequest(BaseModel):
    scene_number: int = Field(..., ge=1)
    heading: Optional[str] = None
    description: Optional[str] = None
    purpose: Optional[str] = None
    setting: Optional[str] = None
    duration_seconds: Optional[float] = Field(default=None, gt=0.0)
    narration: Optional[str] = None
    dialogue: Optional[Any] = None
    scene_config: Optional[Dict[str, Any]] = None


class SceneDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: Optional[uuid.UUID] = None
    story_id: Optional[uuid.UUID] = None
    scene_number: int
    heading: Optional[str] = None
    description: Optional[str] = None
    purpose: Optional[str] = None
    setting: Optional[str] = None
    duration_seconds: Optional[float] = None
    narration: Optional[str] = None
    dialogue: Optional[Any] = None
    scene_config: Optional[Dict[str, Any]] = None
    is_locked: bool
    created_at: datetime
    updated_at: datetime
    shots: List[ShotDetailResponse] = Field(default_factory=list)
