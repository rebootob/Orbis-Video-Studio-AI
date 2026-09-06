import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class LockEntityRequest(BaseModel):
    project_id: uuid.UUID
    entity_type: str = Field(..., description="SCRIPT, SCENE, SHOT, CHARACTER, LOCATION, VOICE, TIMING")
    entity_id: uuid.UUID
    actor: str = "system"
    reason: Optional[str] = None


class UnlockEntityRequest(BaseModel):
    project_id: uuid.UUID
    entity_type: str = Field(..., description="SCRIPT, SCENE, SHOT, CHARACTER, LOCATION, VOICE, TIMING")
    entity_id: uuid.UUID
    actor: str = "system"
    reason: Optional[str] = None


class AssetLockResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    entity_type: str
    entity_id: uuid.UUID
    is_locked: bool
    locked_by: Optional[str] = None
    locked_at: Optional[datetime] = None
    lock_reason: Optional[str] = None
    unlocked_by: Optional[str] = None
    unlocked_at: Optional[datetime] = None
    unlock_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime
