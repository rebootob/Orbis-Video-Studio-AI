import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.production_orchestrator import ProductionOrchestrator
from app.schemas.orchestrator import (
    OrchestrationStateResponse,
    ExecuteActionRequest,
    ExecuteActionResponse,
    ApproveStageRequest,
    ApproveStageResponse,
    OrchestrationSettingsUpdateRequest,
    PaginatedOrchestrationAuditResponse,
    OrchestrationAuditResponse,
)

from app.services.creative_generation.base import CreativeGenerationProvider
from app.services.creative_generation.factory import get_creative_provider

router = APIRouter()


@router.get(
    "/projects/{project_id}/orchestration",
    response_model=OrchestrationStateResponse,
    status_code=status.HTTP_200_OK,
)
def get_orchestration_state(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    """Read canonical orchestration state, current stage, and next recommended action."""
    return ProductionOrchestrator.evaluate_state(db=db, project_id=project_id)


@router.post(
    "/projects/{project_id}/orchestration/execute",
    response_model=ExecuteActionResponse,
    status_code=status.HTTP_200_OK,
)
def execute_orchestration_action(
    project_id: uuid.UUID,
    request: ExecuteActionRequest,
    db: Session = Depends(get_db),
    provider: CreativeGenerationProvider = Depends(get_creative_provider),
):
    """Execute an allowed production orchestration action with precondition validation."""
    return ProductionOrchestrator.execute_action(
        db=db,
        project_id=project_id,
        action=request.action,
        parameters=request.parameters,
        actor="USER",
        provider=provider,
    )


@router.post(
    "/projects/{project_id}/orchestration/approve",
    response_model=ApproveStageResponse,
    status_code=status.HTTP_200_OK,
)
def approve_production_stage(
    project_id: uuid.UUID,
    request: Optional[ApproveStageRequest] = None,
    db: Session = Depends(get_db),
    provider: CreativeGenerationProvider = Depends(get_creative_provider),
):
    """Approve current production stage gate and advance to next stage."""
    req = request or ApproveStageRequest()
    return ProductionOrchestrator.approve_stage(
        db=db,
        project_id=project_id,
        stage=req.stage,
        notes=req.notes,
        actor="USER",
        provider=provider,
    )


@router.patch(
    "/projects/{project_id}/orchestration/settings",
    response_model=OrchestrationStateResponse,
    status_code=status.HTTP_200_OK,
)
def update_orchestration_settings(
    project_id: uuid.UUID,
    request: OrchestrationSettingsUpdateRequest,
    db: Session = Depends(get_db),
):
    """Update project orchestration preferences, including automation mode (MANUAL, ASSISTED, AUTO)."""
    return ProductionOrchestrator.update_settings(
        db=db,
        project_id=project_id,
        automation_mode=request.automation_mode,
        actor="USER",
    )


@router.get(
    "/projects/{project_id}/orchestration/history",
    response_model=PaginatedOrchestrationAuditResponse,
    status_code=status.HTTP_200_OK,
)
def get_orchestration_history(
    project_id: uuid.UUID,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """Read paginated append-only transition audit history for the project."""
    items, total = ProductionOrchestrator.get_history(
        db=db,
        project_id=project_id,
        limit=limit,
        offset=offset,
    )
    return PaginatedOrchestrationAuditResponse(
        items=[OrchestrationAuditResponse.model_validate(i) for i in items],
        total=total,
        limit=limit,
        offset=offset,
    )
