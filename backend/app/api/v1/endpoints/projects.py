import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.project import Project
from app.models.scene import Scene
from app.services.video_modes import validate_video_mode
from app.schemas.project import ProjectCreateRequest, ProjectResponse
from app.schemas.shot import SceneCreateRequest, SceneDetailResponse

router = APIRouter()


@router.post(
    "/projects",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_project(
    request: ProjectCreateRequest,
    db: Session = Depends(get_db),
):
    norm_mode = validate_video_mode(request.video_mode)
    project = Project(
        id=uuid.uuid4(),
        title=request.title,
        description=request.description,
        video_mode=norm_mode,
        purpose=request.purpose,
        target_platform=request.target_platform,
        target_duration_seconds=request.target_duration_seconds,
        preferred_aspect_ratio=request.preferred_aspect_ratio,
        mode_config=request.mode_config,
        default_config=request.default_config,
        status="DRAFT",
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.get(
    "/projects/{project_id}",
    response_model=ProjectResponse,
    status_code=status.HTTP_200_OK,
)
def get_project(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found",
        )
    return project


@router.post(
    "/projects/{project_id}/scenes",
    response_model=SceneDetailResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_project_scene(
    project_id: uuid.UUID,
    request: SceneCreateRequest,
    db: Session = Depends(get_db),
):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found",
        )

    scene = Scene(
        id=uuid.uuid4(),
        project_id=project_id,
        story_id=None,
        scene_number=request.scene_number,
        heading=request.heading,
        description=request.description,
        purpose=request.purpose,
        setting=request.setting,
        duration_seconds=request.duration_seconds,
        narration=request.narration,
        dialogue=request.dialogue,
        scene_config=request.scene_config,
        is_locked=False,
    )
    db.add(scene)
    db.commit()
    db.refresh(scene)
    return scene


@router.get(
    "/projects/{project_id}/scenes",
    response_model=List[SceneDetailResponse],
    status_code=status.HTTP_200_OK,
)
def list_project_scenes(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found",
        )
    # Return scenes belonging directly to project or via story
    scenes = (
        db.query(Scene)
        .filter(
            (Scene.project_id == project_id)
            | (Scene.story.has(project_id=project_id))
        )
        .order_by(Scene.scene_number)
        .all()
    )
    return scenes
