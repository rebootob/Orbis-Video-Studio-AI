import uuid
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.qc import ApprovalRecord
from app.schemas.qc import (
    QCRunRead,
    WarningDecisionCreate,
    WarningDecisionRead,
    QCRunSummaryRead,
    FinalApprovalCreate,
    ApprovalRecordRead,
    QCHistoryPagination,
)
from app.services.qc import QCService

router = APIRouter()


@router.post("/run", response_model=QCRunRead)
def run_qc_evaluation(
    project_id: uuid.UUID,
    actor: str = Query("system", description="Actor running the evaluation"),
    db: Session = Depends(get_db),
):
    """Run automated deterministic Quality Control evaluation against current timeline revision."""
    return QCService.run_qc(db=db, project_id=project_id, actor=actor)


@router.get("/latest", response_model=QCRunSummaryRead)
def get_latest_qc_summary(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    """Get simple QC default summary for current active timeline (hides technical IDs by default)."""
    return QCService.get_simple_summary(db=db, project_id=project_id)


@router.get("/history", response_model=QCHistoryPagination)
def get_qc_history(
    project_id: uuid.UUID,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Get bounded, paginated list of historical QC runs and warning decisions."""
    return QCService.get_qc_history(db=db, project_id=project_id, offset=offset, limit=limit)


@router.post("/findings/{finding_id}/decision", response_model=WarningDecisionRead)
def record_warning_decision(
    project_id: uuid.UUID,
    finding_id: uuid.UUID,
    payload: WarningDecisionCreate,
    actor: str = Query("USER", description="Actor making the decision"),
    db: Session = Depends(get_db),
):
    """Record explicit user decision for a warning finding. Accepts FIX_REQUIRED or ACCEPTED_WITH_REASON."""
    return QCService.record_warning_decision(
        db=db,
        project_id=project_id,
        finding_id=finding_id,
        decision=payload.decision,
        reason=payload.reason,
        actor=actor,
    )


@router.post("/approve", response_model=ApprovalRecordRead)
def approve_production(
    project_id: uuid.UUID,
    payload: FinalApprovalCreate,
    actor: str = Query("USER", description="Actor approving final cut"),
    db: Session = Depends(get_db),
):
    """Canonical production approval gate. Requires PASSED QC run, zero blockers, and all warnings decided."""
    return QCService.approve_production(
        db=db,
        project_id=project_id,
        timeline_id=payload.timeline_id,
        qc_run_id=payload.qc_run_id,
        notes=payload.notes,
        actor=actor,
    )


@router.get("/approvals", response_model=List[ApprovalRecordRead])
def list_production_approvals(
    project_id: uuid.UUID,
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Get bounded, paginated history of production approvals for project."""
    eff_limit = min(max(limit, 1), 100)
    return (
        db.query(ApprovalRecord)
        .filter(ApprovalRecord.project_id == project_id)
        .order_by(ApprovalRecord.approved_at.desc())
        .offset(offset)
        .limit(eff_limit)
        .all()
    )
