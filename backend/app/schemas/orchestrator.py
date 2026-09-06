import uuid
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict, Field


class AutomationMode(str, Enum):
    MANUAL = "MANUAL"
    ASSISTED = "ASSISTED"
    AUTO = "AUTO"


class OrchestrationActionType(str, Enum):
    APPROVAL = "APPROVAL"
    GENERATION = "GENERATION"
    REVISION = "REVISION"
    RECOVERY = "RECOVERY"
    NAVIGATION = "NAVIGATION"


class OrchestrationActionResult(str, Enum):
    APPLIED = "APPLIED"
    NO_OP = "NO_OP"
    BLOCKED = "BLOCKED"
    FAILED = "FAILED"


class OrchestrationActionModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    action: str
    display_name: str
    description: str
    action_type: OrchestrationActionType
    is_chargeable: bool = False
    is_blocked: bool = False
    blocked_reason: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None


class OrchestrationStateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    project_id: uuid.UUID
    current_stage: str
    video_mode: str
    automation_mode: AutomationMode
    stage_display_name: str
    stage_description: str
    is_approval_required: bool = False
    is_blocked: bool = False
    blocked_reasons: List[str] = Field(default_factory=list)
    recommended_action: Optional[OrchestrationActionModel] = None
    available_actions: List[OrchestrationActionModel] = Field(default_factory=list)
    summary: Dict[str, Any] = Field(default_factory=dict)


class ExecuteActionRequest(BaseModel):
    action: str
    parameters: Optional[Dict[str, Any]] = None


class ExecuteActionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    success: bool
    action: str
    from_stage: str
    to_stage: str
    result: OrchestrationActionResult
    message: str
    orchestration_state: OrchestrationStateResponse


class ApproveStageRequest(BaseModel):
    stage: Optional[str] = None
    notes: Optional[str] = None
    cost_authorized: Optional[bool] = False


class ApproveStageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    success: bool
    from_stage: str
    to_stage: str
    result: OrchestrationActionResult
    message: str
    orchestration_state: OrchestrationStateResponse


class OrchestrationSettingsUpdateRequest(BaseModel):
    automation_mode: Optional[AutomationMode] = None
    auto_cost_authorized: Optional[bool] = None


class OrchestrationAuditResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    from_state: str
    to_state: Optional[str] = None
    action: str
    actor: str
    result: str
    reason_code: Optional[str] = None
    detail: Optional[str] = None
    created_at: datetime


class PaginatedOrchestrationAuditResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    items: List[OrchestrationAuditResponse]
    total: int
    limit: int
    offset: int
