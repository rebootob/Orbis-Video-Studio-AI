import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, ConfigDict


class JobCreateRequest(BaseModel):
    shot_id: uuid.UUID
    provider_name: str = "vidu"
    idempotency_key: Optional[str] = None
    custom_params: Optional[Dict[str, Any]] = None
    max_retries: int = 3


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
    payload: Optional[Dict[str, Any]] = None
    result: Optional[Dict[str, Any]] = None
    output_asset_id: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime
