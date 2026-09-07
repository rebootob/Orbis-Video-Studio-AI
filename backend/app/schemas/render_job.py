import uuid
from datetime import datetime
from typing import Optional, List, Any, Dict
from pydantic import BaseModel, ConfigDict, Field


class RenderJobSubmitRequest(BaseModel):
    timeline_id: Optional[uuid.UUID] = None
    render_profile: str = Field(default="MASTER_HD", description="Render output profile (e.g. MASTER_HD)")
    idempotency_key: Optional[str] = Field(default=None, description="Optional custom idempotency key")


class RenderJobRead(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    timeline_id: uuid.UUID
    timeline_version: int
    approval_id: uuid.UUID
    render_profile: str
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


class RenderJobListResponse(BaseModel):
    renders: List[RenderJobRead]
    total_count: int
    offset: int
    limit: int
