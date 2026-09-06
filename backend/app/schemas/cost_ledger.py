"""Pydantic schemas for budget control and usage cost ledger."""
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict, Field


class BudgetUpdateRequest(BaseModel):
    budget_limit: Optional[float] = Field(None, ge=0.0, description="Hard budget cap for the project")
    budget_currency: Optional[str] = Field("USD", max_length=10, description="Budget currency code")
    budget_threshold_percentage: Optional[float] = Field(
        80.0, ge=0.0, le=100.0, description="Soft alert threshold percentage"
    )


class BudgetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    project_id: uuid.UUID
    budget_limit: Optional[float]
    budget_currency: str
    budget_threshold_percentage: Optional[float]
    soft_limit_threshold_amount: Optional[float]
    total_committed_cost: float
    remaining_budget: Optional[float]
    is_soft_limit_exceeded: bool
    is_hard_limit_exceeded: bool


class LedgerAdjustmentDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    ledger_id: uuid.UUID
    actor: str
    reason: str
    previous_cost: Optional[float]
    adjusted_cost: float
    created_at: datetime


class LedgerAdjustmentCreate(BaseModel):
    actor: str = Field(..., min_length=1, max_length=255, description="Actor performing adjustment")
    reason: str = Field(..., min_length=1, description="Audit reason for the adjustment")
    adjusted_cost: float = Field(..., ge=0.0, description="Corrected actual cost amount")


class UsageLedgerDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    shot_id: Optional[uuid.UUID] = None
    job_id: Optional[uuid.UUID] = None
    provider: str
    operation: str
    model: Optional[str] = None
    usage_units: Optional[Dict[str, Any]] = None
    estimated_cost: Optional[float] = None
    actual_cost: Optional[float] = None
    currency: str = "USD"
    cost_status: str
    provider_event_id: Optional[str] = None
    idempotency_key: Optional[str] = None
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    adjustments: List[LedgerAdjustmentDTO] = []


class ProviderCostSummary(BaseModel):
    provider: str
    total_cost: float
    event_count: int


class OperationCostSummary(BaseModel):
    operation: str
    total_cost: float
    event_count: int


class CostSummaryResponse(BaseModel):
    project_id: uuid.UUID
    total_estimated_cost: float
    total_confirmed_cost: float
    total_adjusted_cost: float
    total_actual_cost: float
    total_committed_cost: float
    unknown_cost_count: int
    currency: str
    budget: BudgetResponse
    by_provider: List[ProviderCostSummary]
    by_operation: List[OperationCostSummary]
