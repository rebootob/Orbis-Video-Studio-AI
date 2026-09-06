import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.project import Project
from app.models.scene import Scene
from app.services.video_modes import validate_video_mode
from app.schemas.project import ProjectCreateRequest, ProjectResponse, ProjectUpdateRequest
from app.schemas.shot import SceneCreateRequest, SceneUpdateRequest, SceneDetailResponse
from app.services.lock_machine import LockMachineService

router = APIRouter()


@router.get(
    "/projects",
    response_model=List[ProjectResponse],
    status_code=status.HTTP_200_OK,
)
def list_projects(
    db: Session = Depends(get_db),
):
    projects = db.query(Project).order_by(Project.updated_at.desc()).all()
    return projects


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


@router.patch(
    "/projects/{project_id}",
    response_model=ProjectResponse,
    status_code=status.HTTP_200_OK,
)
def update_project(
    project_id: uuid.UUID,
    request: ProjectUpdateRequest,
    db: Session = Depends(get_db),
):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found",
        )

    if request.title is not None:
        project.title = request.title
    if request.description is not None:
        project.description = request.description
    if request.status is not None:
        project.status = request.status
    if request.purpose is not None:
        project.purpose = request.purpose
    if request.target_platform is not None:
        project.target_platform = request.target_platform
    if request.target_duration_seconds is not None:
        project.target_duration_seconds = request.target_duration_seconds
    if request.preferred_aspect_ratio is not None:
        project.preferred_aspect_ratio = request.preferred_aspect_ratio
    if request.mode_config is not None:
        project.mode_config = request.mode_config
    if request.default_config is not None:
        project.default_config = request.default_config

    db.commit()
    db.refresh(project)
    return project


@router.delete(
    "/projects/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_project(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found",
        )
    db.delete(project)
    db.commit()
    return None


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


@router.patch(
    "/scenes/{scene_id}",
    response_model=SceneDetailResponse,
    status_code=status.HTTP_200_OK,
)
def update_scene(
    scene_id: uuid.UUID,
    request: SceneUpdateRequest,
    db: Session = Depends(get_db),
):
    scene = db.get(Scene, scene_id)
    if not scene:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scene '{scene_id}' not found",
        )

    LockMachineService.check_mutation_allowed(db, "SCENE", scene_id)

    if request.scene_number is not None:
        scene.scene_number = request.scene_number
    if request.heading is not None:
        scene.heading = request.heading
    if request.description is not None:
        scene.description = request.description
    if request.purpose is not None:
        scene.purpose = request.purpose
    if request.setting is not None:
        scene.setting = request.setting
    if request.duration_seconds is not None:
        scene.duration_seconds = request.duration_seconds
    if request.narration is not None:
        scene.narration = request.narration
    if request.dialogue is not None:
        scene.dialogue = request.dialogue
    if request.scene_config is not None:
        scene.scene_config = request.scene_config

    db.commit()
    db.refresh(scene)
    return scene


@router.delete(
    "/scenes/{scene_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_scene(
    scene_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    scene = db.get(Scene, scene_id)
    if not scene:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scene '{scene_id}' not found",
        )

    LockMachineService.check_mutation_allowed(db, "SCENE", scene_id)

    db.delete(scene)
    db.commit()
    return None
