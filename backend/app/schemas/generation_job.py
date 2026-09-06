import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, ConfigDict, Field


class JobCreateRequest(BaseModel):
    shot_id: uuid.UUID
    provider_name: Optional[str] = None
    idempotency_key: Optional[str] = None
    custom_params: Optional[Dict[str, Any]] = None
    max_retries: int = Field(default=3, ge=1, le=10)
    reference_images: Optional[List[Dict[str, Any]]] = None


class JobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    shot_id: uuid.UUID
    job_type: str = "VIDEO"
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
    claim_token: str


class BatchRunItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    batch_run_id: uuid.UUID
    shot_id: uuid.UUID
    job_id: Optional[uuid.UUID] = None
    decision: str
    skip_reason: Optional[str] = None
    created_at: datetime


class BatchRunSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    operation_type: str
    status: str
    requested_count: int
    eligible_count: int
    queued_count: int
    skipped_count: int
    completed_count: int
    failed_count: int
    created_at: datetime
    updated_at: datetime


class BatchRunDetailResponse(BatchRunSummaryResponse):
    items: List[BatchRunItemResponse]
    items_total: int
    item_limit: int
    item_offset: int


# Backward compatibility alias
BatchRunResponse = BatchRunSummaryResponse


from typing import Optional, List, Literal

class BatchResumeRequest(BaseModel):
    operation_type: Literal["CONTINUE_INCOMPLETE", "RETRY_FAILED", "GENERATE_SELECTED"] = "CONTINUE_INCOMPLETE"
    shot_ids: Optional[List[uuid.UUID]] = None
    provider_name: Optional[str] = None
    only_incomplete: bool = True


class BatchResumeEstimateResponse(BaseModel):
    shot_count: int
    skipped_count: int = 0
    total_evaluated: int = 0
    estimated_cost_total: Optional[float] = None
    currency: str = "USD"
    has_unknown_pricing: bool = False
    warning_messages: List[str] = []
