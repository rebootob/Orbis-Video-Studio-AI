import uuid
from typing import Optional

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.story_generation import StoryResponse
from app.services.manual_creative import ManualCreativeService


router = APIRouter()


class ManualStoryUpsertRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    logline: Optional[str] = None
    synopsis: Optional[str] = None
    tone: Optional[str] = Field(default=None, max_length=100)
    target_duration_seconds: Optional[float] = Field(default=None, gt=0.0)
    language: Optional[str] = Field(default=None, max_length=50)


@router.put(
    "/projects/{project_id}/story/manual",
    response_model=StoryResponse,
    status_code=status.HTTP_200_OK,
)
def upsert_manual_story(
    project_id: uuid.UUID,
    request: ManualStoryUpsertRequest,
    db: Session = Depends(get_db),
):
    """Create/update a STORY-mode Story manually with zero CreativeProvider dispatch."""
    return ManualCreativeService.upsert_story(
        db=db,
        project_id=project_id,
        payload=request.model_dump(exclude_unset=True),
        actor="USER",
    )
