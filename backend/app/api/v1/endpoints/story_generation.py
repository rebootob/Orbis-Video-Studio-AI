import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.story import Story
from app.schemas.story_generation import (
    StoryGenerateRequest,
    SceneGenerateRequest,
    ShotGenerateRequest,
    StoryResponse,
    SceneResponse,
    ShotResponse,
)
from app.services.creative_generation.base import (
    CreativeGenerationProvider,
    CreativeGenerationError,
    GenerationRequestOptions,
)
from app.services.creative_generation.factory import get_creative_provider
from app.services.creative_generation.service import StoryGenerationService

router = APIRouter()


def _map_error(e: CreativeGenerationError) -> HTTPException:
    if e.code in ("PROJECT_NOT_FOUND", "STORY_NOT_FOUND", "SCENE_NOT_FOUND"):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
    elif e.code in ("STORY_LOCKED", "SCENE_LOCKED", "SHOT_LOCKED"):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=e.message)
    elif e.code in ("NO_SOURCE_CONTEXT", "SOURCE_EXTRACTION_NOT_READY"):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.message)
    elif e.code == "PROVIDER_TIMEOUT":
        return HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail=e.message)
    elif e.code == "PROVIDER_UNAVAILABLE":
        return HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=e.message)
    elif e.code == "INVALID_PROVIDER_RESPONSE":
        return HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=e.message)
    else:
        return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=e.message)


@router.post(
    "/projects/{project_id}/story/generate",
    response_model=StoryResponse,
    status_code=status.HTTP_200_OK,
)
def generate_project_story(
    project_id: uuid.UUID,
    request: StoryGenerateRequest = StoryGenerateRequest(),
    db: Session = Depends(get_db),
    provider: CreativeGenerationProvider = Depends(get_creative_provider),
):
    """Generate or regenerate structured Story, Scenes, and Shots from Project brief and documents."""
    service = StoryGenerationService(db=db, provider=provider)
    options = GenerationRequestOptions(profile=request.profile)

    try:
        story = service.generate_project_story(
            project_id=project_id,
            target_duration_seconds=request.target_duration_seconds,
            tone=request.tone,
            language=request.language,
            target_audience=request.target_audience,
            custom_instructions=request.custom_instructions,
            options=options,
        )
        return story
    except CreativeGenerationError as e:
        raise _map_error(e)


@router.post(
    "/stories/{story_id}/scenes/generate",
    response_model=List[SceneResponse],
    status_code=status.HTTP_200_OK,
)
def generate_story_scenes(
    story_id: uuid.UUID,
    request: SceneGenerateRequest = SceneGenerateRequest(),
    db: Session = Depends(get_db),
    provider: CreativeGenerationProvider = Depends(get_creative_provider),
):
    """Generate or regenerate scenes for an existing Story context."""
    service = StoryGenerationService(db=db, provider=provider)
    options = GenerationRequestOptions(profile=request.profile)

    try:
        scenes = service.generate_story_scenes(
            story_id=story_id,
            custom_instructions=request.custom_instructions,
            options=options,
        )
        return scenes
    except CreativeGenerationError as e:
        raise _map_error(e)


@router.post(
    "/scenes/{scene_id}/shots/generate",
    response_model=List[ShotResponse],
    status_code=status.HTTP_200_OK,
)
def generate_scene_shots(
    scene_id: uuid.UUID,
    request: ShotGenerateRequest = ShotGenerateRequest(),
    db: Session = Depends(get_db),
    provider: CreativeGenerationProvider = Depends(get_creative_provider),
):
    """Generate or regenerate shots for an existing Scene context."""
    service = StoryGenerationService(db=db, provider=provider)
    options = GenerationRequestOptions(profile=request.profile)

    try:
        shots = service.generate_scene_shots(
            scene_id=scene_id,
            custom_instructions=request.custom_instructions,
            options=options,
        )
        return shots
    except CreativeGenerationError as e:
        raise _map_error(e)


@router.get(
    "/projects/{project_id}/story",
    response_model=StoryResponse,
    status_code=status.HTTP_200_OK,
)
def get_project_story(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    """Retrieve full Story tree with nested Scenes and Shots for a Project."""
    story = db.query(Story).filter(Story.project_id == project_id).first()
    if not story:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Story record not found for Project '{project_id}'.",
        )
    return story
