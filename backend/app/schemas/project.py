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


VALID_PROJECT_STATUSES = {
    "DRAFT",
    "STORY_GENERATED",
    "STORY_APPROVED",
    "STORYBOARD_GENERATED",
    "STORYBOARD_APPROVED",
    "SHOT_PLAN_GENERATED",
    "SHOT_PLAN_APPROVED",
    "IMAGES_GENERATED",
    "VIDEO_IN_PROGRESS",
    "FINAL_REVIEW",
    "APPROVED",
    "COMPLETED",
    "ARCHIVED",
}


class ProjectUpdateRequest(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = None
    status: Optional[str] = None
    purpose: Optional[str] = None
    target_platform: Optional[str] = None
    target_duration_seconds: Optional[float] = Field(default=None, gt=0.0)
    preferred_aspect_ratio: Optional[str] = None
    mode_config: Optional[Any] = None
    default_config: Optional[Any] = None

    def validate_and_normalize_status(self) -> Optional[str]:
        if self.status is not None:
            norm = self.status.strip().upper()
            if norm not in VALID_PROJECT_STATUSES:
                raise ValueError(
                    f"Invalid project status '{self.status}'. Allowed: {sorted(list(VALID_PROJECT_STATUSES))}"
                )
            return norm
        return None



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
    budget_limit: Optional[float] = None
    budget_currency: Optional[str] = "USD"
    budget_threshold_percentage: Optional[float] = 80.0
    scene_count: int = 0
    shot_count: int = 0
    thumbnail_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime
