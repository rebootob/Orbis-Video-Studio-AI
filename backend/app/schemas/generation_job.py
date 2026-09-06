import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, ConfigDict, Field


class JobCreateRequest(BaseModel):
    shot_id: uuid.UUID
    provider_name: str = "vidu"
    idempotency_key: Optional[str] = None
    custom_params: Optional[Dict[str, Any]] = None
    max_retries: int = Field(default=3, ge=1, le=10)
    reference_images: Optional[List[Dict[str, Any]]] = None


class JobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    shot_id: uuid.UUID
    provider_name: str
    provider_job_id: Optional[str] = None
    status: str
    idempotency_key: Optional[str] = None
    cost_usd: Optional[float] = None
    error_message: Optional[str] = None
    retry_count: int
    max_retries: int
    poll_count: int = 0
    max_polls: int = 60
    claimed_by: Optional[str] = None
    claim_expires_at: Optional[datetime] = None
    next_retry_at: Optional[datetime] = None
    next_poll_at: Optional[datetime] = None
    submission_attempt_id: Optional[str] = None
    payload: Optional[Dict[str, Any]] = None
    result: Optional[Dict[str, Any]] = None
    output_asset_id: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime


class ClaimResponse(JobResponse):
    claim_token: str
    claimed_by: str
    claim_expires_at: datetime


class DispatchRequest(BaseModel):
    claim_token: Optional[str] = None
