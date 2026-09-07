import uuid
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, field_validator


class WarningDecisionCreate(BaseModel):
    decision: str  # FIX_REQUIRED, ACCEPTED_WITH_REASON
    reason: Optional[str] = None

    @field_validator("decision")
    @classmethod
    def validate_decision_enum(cls, v: str) -> str:
        v_upper = v.upper()
        if v_upper not in ("FIX_REQUIRED", "ACCEPTED_WITH_REASON"):
            raise ValueError("decision must be either FIX_REQUIRED or ACCEPTED_WITH_REASON")
        return v_upper

    @field_validator("reason")
    @classmethod
    def validate_reason_for_accepted(cls, v: Optional[str], info) -> Optional[str]:
        decision = info.data.get("decision")
        if decision == "ACCEPTED_WITH_REASON":
            if not v or not v.strip():
                raise ValueError("Reason is required and cannot be empty when accepting a warning")
            return v.strip()
        return v.strip() if v else None


class WarningDecisionRead(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    qc_run_id: uuid.UUID
    finding_id: uuid.UUID
    timeline_id: uuid.UUID
    decision: str
    reason: Optional[str] = None
    actor: str
    decided_at: datetime

    model_config = ConfigDict(from_attributes=True)


class QCFindingRead(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    qc_run_id: uuid.UUID
    timeline_id: uuid.UUID
    rule_code: str
    severity: str  # BLOCKER, WARNING (PASS is NOT a finding severity!)
    message: str
    why_it_matters: Optional[str] = None
    recommended_fix: Optional[str] = None
    target_type: Optional[str] = None
    target_id: Optional[uuid.UUID] = None
    target_label: Optional[str] = None
    action_type: Optional[str] = None
    created_at: datetime
    current_decision: Optional[WarningDecisionRead] = None

    model_config = ConfigDict(from_attributes=True)


class QCRunRead(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    timeline_id: uuid.UUID
    timeline_version: int
    status: str  # PENDING, RUNNING, PASSED, BLOCKED, ERROR
    blocker_count: int
    warning_count: int
    actor: str
    created_at: datetime
    updated_at: datetime
    findings: List[QCFindingRead] = []

    model_config = ConfigDict(from_attributes=True)


class SimpleFindingRead(BaseModel):
    id: uuid.UUID
    rule_code: str
    severity: str
    message: str
    why_it_matters: Optional[str] = None
    recommended_fix: Optional[str] = None
    target_label: Optional[str] = None
    action_type: Optional[str] = None
    decision: Optional[str] = None
    reason: Optional[str] = None


class QCRunSummaryRead(BaseModel):
    qc_run_id: uuid.UUID
    project_id: uuid.UUID
    timeline_id: uuid.UUID
    timeline_version: int
    status: str
    overall_state: str  # READY_FOR_APPROVAL, NEEDS_ATTENTION, BLOCKED
    total_blockers: int
    total_warnings: int
    unresolved_warnings: int
    recommended_next_action: str
    simple_findings: List[SimpleFindingRead] = []


class FinalApprovalCreate(BaseModel):
    timeline_id: Optional[uuid.UUID] = None
    qc_run_id: Optional[uuid.UUID] = None
    notes: Optional[str] = None


class ApprovalRecordRead(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    timeline_id: uuid.UUID
    timeline_version: int
    qc_run_id: uuid.UUID
    status: str
    actor: str
    notes: Optional[str] = None
    approved_at: datetime

    model_config = ConfigDict(from_attributes=True)


class QCHistoryPagination(BaseModel):
    qc_runs: List[QCRunRead]
    total_count: int
    offset: int
    limit: int
