import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, ConfigDict, Field


class RecommendedFix(BaseModel):
    fix_code: str
    label: str
    action_type: str
    payload: Optional[Dict[str, Any]] = None


class AssemblyBlocker(BaseModel):
    code: str
    message: str
    severity: str = "ERROR"  # WARNING, ERROR, CRITICAL
    target_id: Optional[str] = None
    recommended_fixes: List[RecommendedFix] = Field(default_factory=list)


class AssemblyShotPlacementRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: Union[str, uuid.UUID]
    timeline_id: Union[str, uuid.UUID]
    assembly_scene_id: Union[str, uuid.UUID]
    scene_id: Union[str, uuid.UUID]
    shot_id: Union[str, uuid.UUID]
    shot_order: int
    visual_asset_id: Optional[Union[str, uuid.UUID]] = None
    source_type: str  # VIDEO, IMAGE, KEYFRAME, MISSING
    trim_in: float = 0.0
    trim_out: Optional[float] = None
    effective_duration: float = 4.0
    still_duration: float = 4.0
    transition_to_next: str = "CUT"  # CUT, FADE, DISSOLVE
    is_locked: bool = False
    version: int = 1
    asset_url: Optional[str] = None
    asset_thumbnail_url: Optional[str] = None
    shot_title: Optional[str] = None
    shot_prompt: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class AssemblySceneRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: Union[str, uuid.UUID]
    timeline_id: Union[str, uuid.UUID]
    scene_id: Union[str, uuid.UUID]
    scene_order: int
    scene_title: Optional[str] = None
    placements: List[AssemblyShotPlacementRead] = Field(default_factory=list)


class AudioClipSummaryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: Union[str, uuid.UUID]
    audio_type: str
    scope: str
    name: str
    start_time: float
    duration_seconds: Optional[float] = None
    volume: float = 1.0
    is_muted: bool = False
    scene_id: Optional[Union[str, uuid.UUID]] = None
    shot_id: Optional[Union[str, uuid.UUID]] = None


class AssemblyTimelineRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: Union[str, uuid.UUID]
    project_id: Union[str, uuid.UUID]
    version: int
    status: str
    is_active: bool
    total_duration: float
    scene_count: int
    shot_count: int
    scenes: List[AssemblySceneRead] = Field(default_factory=list)
    audio_clips: List[AudioClipSummaryRead] = Field(default_factory=list)
    blockers: List[AssemblyBlocker] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class PlacementUpdate(BaseModel):
    trim_in: Optional[float] = None
    trim_out: Optional[float] = None
    still_duration: Optional[float] = None
    transition_to_next: Optional[str] = None
    is_locked: Optional[bool] = None
    reason: Optional[str] = None


class SceneReorderItem(BaseModel):
    scene_id: str
    order: int


class SceneReorderRequest(BaseModel):
    orders: List[SceneReorderItem]


class ShotReorderItem(BaseModel):
    shot_id: str
    order: int


class ShotReorderRequest(BaseModel):
    orders: List[ShotReorderItem]


class CrossSceneMoveRequest(BaseModel):
    shot_id: str
    target_scene_id: str
    target_position: int = 0
    actor: Optional[str] = "USER"
    reason: Optional[str] = None


class CheckpointCreate(BaseModel):
    label: str
    actor: Optional[str] = "USER"


class CheckpointRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: Union[str, uuid.UUID]
    project_id: Union[str, uuid.UUID]
    timeline_id: Union[str, uuid.UUID]
    checkpoint_number: int
    label: str
    snapshot_data: Dict[str, Any]
    actor: str
    created_at: datetime


class CheckpointRestoreRequest(BaseModel):
    actor: Optional[str] = "USER"
    reason: Optional[str] = None


class ApplyFixRequest(BaseModel):
    blocker_code: str
    target_id: Optional[str] = None
    fix_code: str


class TimelineAuditRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: Union[str, uuid.UUID]
    project_id: Union[str, uuid.UUID]
    timeline_id: Union[str, uuid.UUID]
    action: str
    actor: str
    change_reason: Optional[str] = None
    created_at: datetime
