import uuid
from datetime import datetime
from typing import Optional, List, Any, Dict
from pydantic import BaseModel, ConfigDict, Field


class RenderJobSubmitRequest(BaseModel):
    timeline_id: Optional[uuid.UUID] = None
    render_profile: str = Field(default="MASTER_HD", description="Render output profile (e.g. MASTER_HD)")
    idempotency_key: Optional[str] = Field(default=None, description="Optional custom idempotency key")


class ExportBatchSubmitRequest(BaseModel):
    timeline_id: Optional[uuid.UUID] = None
    preset_ids: List[str] = Field(..., description="List of export preset IDs to execute")


class RenderJobRead(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    timeline_id: uuid.UUID
    timeline_version: int
    approval_id: uuid.UUID
    render_profile: str
    render_variant_key: str = "MASTER"
    batch_id: Optional[uuid.UUID] = None
    status: str
    idempotency_key: str
    output_asset_id: Optional[uuid.UUID] = None
    progress: float
    claimed_by: Optional[str] = None
    claim_expires_at: Optional[datetime] = None
    retry_count: int
    max_retries: int
    estimated_cost_usd: float
    actual_cost_usd: Optional[float] = None
    error_message: Optional[str] = None
    render_metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RenderBatchRead(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    timeline_id: uuid.UUID
    timeline_version: int
    status: str
    total_variants: int
    completed_variants: int
    failed_variants: int
    estimated_total_cost_usd: float
    created_at: datetime
    updated_at: datetime
    child_jobs: Optional[List[RenderJobRead]] = None

    model_config = ConfigDict(from_attributes=True)


class ExportPresetRead(BaseModel):
    preset_id: str
    target_platform: str
    aspect_ratio: str
    width: int
    height: int
    video_codec: str
    video_profile: str
    audio_codec: str
    audio_bitrate_kbps: int
    video_bitrate_kbps: int
    estimated_cost_usd: float
    framing_mode: str


class RenderJobListResponse(BaseModel):
    renders: List[RenderJobRead]
    total_count: int
    offset: int
    limit: int
