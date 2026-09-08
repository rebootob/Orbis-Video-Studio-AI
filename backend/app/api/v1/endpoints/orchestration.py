import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.production_orchestrator import ProductionOrchestrator
from app.services.manual_creative import ManualCreativeService
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

router = APIRouter()


def _overlay_state(db: Session, state: OrchestrationStateResponse) -> OrchestrationStateResponse:
    return ManualCreativeService.overlay_state(db, state)


def _overlay_execute_response(db: Session, response: ExecuteActionResponse) -> ExecuteActionResponse:
    response.orchestration_state = _overlay_state(db, response.orchestration_state)
    return response


def _overlay_approve_response(db: Session, response: ApproveStageResponse) -> ApproveStageResponse:
    response.orchestration_state = _overlay_state(db, response.orchestration_state)
    return response


@router.get(
    "/projects/{project_id}/orchestration",
    response_model=OrchestrationStateResponse,
    status_code=status.HTTP_200_OK,
)
def get_orchestration_state(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    """Read canonical orchestration state with MANUAL next-best-action overlay where applicable."""
    state = ProductionOrchestrator.evaluate_state(db=db, project_id=project_id)
    return _overlay_state(db, state)


@router.post(
    "/projects/{project_id}/orchestration/execute",
    response_model=ExecuteActionResponse,
    status_code=status.HTTP_200_OK,
)
def execute_orchestration_action(
    project_id: uuid.UUID,
    request: ExecuteActionRequest,
    db: Session = Depends(get_db),
):
    """Execute an allowed action. Manual submissions never resolve or call CreativeProvider."""
    if ManualCreativeService.handles_action(request.action):
        return ManualCreativeService.execute_submission(
            db=db,
            project_id=project_id,
            action=request.action,
            actor="USER",
        )

    response = ProductionOrchestrator.execute_action(
        db=db,
        project_id=project_id,
        action=request.action,
        parameters=request.parameters,
        actor="USER",
        provider=None,
    )
    return _overlay_execute_response(db, response)


@router.post(
    "/projects/{project_id}/orchestration/approve",
    response_model=ApproveStageResponse,
    status_code=status.HTTP_200_OK,
)
def approve_production_stage(
    project_id: uuid.UUID,
    request: Optional[ApproveStageRequest] = None,
    db: Session = Depends(get_db),
):
    """Approve current production stage gate and advance to next stage."""
    req = request or ApproveStageRequest()
    response = ProductionOrchestrator.approve_stage(
        db=db,
        project_id=project_id,
        stage=req.stage,
        notes=req.notes,
        cost_authorized=bool(req.cost_authorized),
        actor="USER",
        provider=None,
    )
    return _overlay_approve_response(db, response)


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
    state = ProductionOrchestrator.update_settings(
        db=db,
        project_id=project_id,
        automation_mode=request.automation_mode,
        auto_cost_authorized=request.auto_cost_authorized,
        actor="USER",
    )
    return _overlay_state(db, state)


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
