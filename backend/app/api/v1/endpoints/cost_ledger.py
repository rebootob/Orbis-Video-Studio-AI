"""API endpoints for project budget and cost ledger."""
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, Path
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.cost_ledger import (
    BudgetUpdateRequest,
    BudgetResponse,
    CostSummaryResponse,
    UsageLedgerDTO,
    LedgerAdjustmentCreate,
    LedgerAdjustmentDTO,
)
from app.services.budget import BudgetService
from app.services.cost_ledger import CostLedgerService

router = APIRouter()


@router.get("/projects/{project_id}/budget", response_model=BudgetResponse)
def get_project_budget(
    project_id: uuid.UUID = Path(...),
    db: Session = Depends(get_db),
):
    """Get project budget configuration and current utilization status."""
    return BudgetService.get_budget_status(db, project_id)


@router.put("/projects/{project_id}/budget", response_model=BudgetResponse)
def update_project_budget(
    payload: BudgetUpdateRequest,
    project_id: uuid.UUID = Path(...),
    db: Session = Depends(get_db),
):
    """Set or update project budget limits and soft alert thresholds."""
    return BudgetService.update_budget(
        db,
        project_id,
        budget_limit=payload.budget_limit,
        budget_currency=payload.budget_currency,
        budget_threshold_percentage=payload.budget_threshold_percentage,
    )


@router.get("/projects/{project_id}/costs/summary", response_model=CostSummaryResponse)
def get_project_cost_summary(
    project_id: uuid.UUID = Path(...),
    db: Session = Depends(get_db),
):
    """Get aggregate cost summary grouped by provider and operation, including budget."""
    return CostLedgerService.get_project_summary(db, project_id)


@router.get("/projects/{project_id}/costs/ledger", response_model=List[UsageLedgerDTO])
def list_project_ledger_entries(
    project_id: uuid.UUID = Path(...),
    provider: Optional[str] = Query(None, description="Filter by provider"),
    operation: Optional[str] = Query(None, description="Filter by operation"),
    cost_status: Optional[str] = Query(None, description="Filter by cost status"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """List detailed audit ledger entries for a project with optional filters."""
    return CostLedgerService.list_entries(
        db,
        project_id=project_id,
        provider=provider,
        operation=operation,
        cost_status=cost_status,
        limit=limit,
        offset=offset,
    )


@router.post(
    "/projects/{project_id}/costs/ledger/{ledger_id}/adjustments",
    response_model=LedgerAdjustmentDTO,
)
def record_ledger_adjustment(
    payload: LedgerAdjustmentCreate,
    project_id: uuid.UUID = Path(...),
    ledger_id: uuid.UUID = Path(...),
    db: Session = Depends(get_db),
):
    """Record an auditable manual cost adjustment without overwriting history."""
    return CostLedgerService.record_adjustment(
        db,
        project_id=project_id,
        ledger_id=ledger_id,
        actor=payload.actor,
        reason=payload.reason,
        adjusted_cost=payload.adjusted_cost,
    )
