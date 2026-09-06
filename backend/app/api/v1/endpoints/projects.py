import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db.session import get_db
from app.models.project import Project
from app.models.scene import Scene
from app.models.shot import Shot
from app.models.generation_job import GenerationJob
from app.models.usage_ledger import UsageLedger
from app.services.video_modes import validate_video_mode
from app.schemas.project import ProjectCreateRequest, ProjectResponse, ProjectUpdateRequest
from app.schemas.shot import SceneCreateRequest, SceneUpdateRequest, SceneDetailResponse, ReorderRequest
from app.services.lock_machine import LockMachineService

router = APIRouter()


def _enrich_project_response(project: Project, db: Session) -> ProjectResponse:
    scenes = (
        db.query(Scene)
        .filter((Scene.project_id == project.id) | (Scene.story.has(project_id=project.id)))
        .all()
    )
    active_scenes = [s for s in scenes if not (s.scene_config or {}).get("archived")]
    scene_ids = [s.id for s in active_scenes]
    shots = db.query(Shot).filter(Shot.scene_id.in_(scene_ids)).all() if scene_ids else []
    active_shots = [s for s in shots if s.status != "ARCHIVED"]

    resp = ProjectResponse.model_validate(project)
    resp.scene_count = len(active_scenes)
    resp.shot_count = len(active_shots)
    return resp


@router.get(
    "/projects",
    response_model=List[ProjectResponse],
    status_code=status.HTTP_200_OK,
)
def list_projects(
    include_archived: bool = Query(False),
    db: Session = Depends(get_db),
):
    query = db.query(Project)
    if not include_archived:
        query = query.filter(Project.status != "ARCHIVED")
    projects = query.order_by(Project.updated_at.desc()).all()
    return [_enrich_project_response(p, db) for p in projects]


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
        automation_mode=getattr(request, "automation_mode", "MANUAL") or "MANUAL",
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return _enrich_project_response(project, db)


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
    return _enrich_project_response(project, db)


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
        try:
            norm_status = request.validate_and_normalize_status()
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        if norm_status != project.status:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Direct modification of project status via generic PATCH /projects is disallowed. "
                    "Production stage transitions must be executed through canonical orchestration endpoints: "
                    f"POST /api/v1/projects/{project_id}/orchestration/execute or POST /api/v1/projects/{project_id}/orchestration/approve."
                ),
            )
    if request.automation_mode is not None:
        project.automation_mode = request.automation_mode
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
    return _enrich_project_response(project, db)


@router.delete(
    "/projects/{project_id}",
    response_model=ProjectResponse,
    status_code=status.HTTP_200_OK,
)
def delete_project(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    """Soft-archive project to preserve full historical and auditable records."""
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found",
        )
    project.status = "ARCHIVED"
    db.commit()
    db.refresh(project)
    return _enrich_project_response(project, db)


@router.post(
    "/projects/{project_id}/archive",
    response_model=ProjectResponse,
    status_code=status.HTTP_200_OK,
)
def archive_project(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found",
        )
    project.status = "ARCHIVED"
    db.commit()
    db.refresh(project)
    return _enrich_project_response(project, db)


@router.post(
    "/projects/{project_id}/unarchive",
    response_model=ProjectResponse,
    status_code=status.HTTP_200_OK,
)
def unarchive_project(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found",
        )
    project.status = "DRAFT"
    db.commit()
    db.refresh(project)
    return _enrich_project_response(project, db)


@router.post(
    "/projects/{project_id}/duplicate",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
)
def duplicate_project(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    orig = db.get(Project, project_id)
    if not orig:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found",
        )

    new_proj = Project(
        id=uuid.uuid4(),
        title=f"Copy of {orig.title}",
        description=orig.description,
        video_mode=orig.video_mode,
        purpose=orig.purpose,
        target_platform=orig.target_platform,
        target_duration_seconds=orig.target_duration_seconds,
        preferred_aspect_ratio=orig.preferred_aspect_ratio,
        mode_config=orig.mode_config,
        default_config=orig.default_config,
        budget_limit=orig.budget_limit,
        budget_currency=orig.budget_currency,
        budget_threshold_percentage=orig.budget_threshold_percentage,
        status="DRAFT",
    )
    db.add(new_proj)
    db.flush()

    orig_scenes = (
        db.query(Scene)
        .filter((Scene.project_id == orig.id) | (Scene.story.has(project_id=orig.id)))
        .order_by(Scene.scene_number)
        .all()
    )
    for oscene in orig_scenes:
        nscene = Scene(
            id=uuid.uuid4(),
            project_id=new_proj.id,
            scene_number=oscene.scene_number,
            heading=oscene.heading,
            description=oscene.description,
            purpose=oscene.purpose,
            setting=oscene.setting,
            duration_seconds=oscene.duration_seconds,
            narration=oscene.narration,
            dialogue=oscene.dialogue,
            scene_config=oscene.scene_config,
            is_locked=False,
        )
        db.add(nscene)
        db.flush()

        orig_shots = db.query(Shot).filter(Shot.scene_id == oscene.id).order_by(Shot.shot_number).all()
        for oshot in orig_shots:
            nshot = Shot(
                id=uuid.uuid4(),
                scene_id=nscene.id,
                shot_number=oshot.shot_number,
                shot_type=oshot.shot_type,
                source_asset_id=oshot.source_asset_id,
                source_metadata=oshot.source_metadata,
                provider_config=oshot.provider_config,
                visual_prompt=oshot.visual_prompt,
                image_prompt=oshot.image_prompt,
                video_prompt=oshot.video_prompt,
                camera=oshot.camera,
                subject=oshot.subject,
                action=oshot.action,
                duration_seconds=oshot.duration_seconds,
                is_locked=False,
                status="DRAFT",
            )
            db.add(nshot)

    db.commit()
    db.refresh(new_proj)
    return _enrich_project_response(new_proj, db)



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
    include_archived: bool = Query(False),
    db: Session = Depends(get_db),
):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found",
        )
    query = db.query(Scene).filter(
        (Scene.project_id == project_id)
        | (Scene.story.has(project_id=project_id))
    )
    scenes = query.order_by(Scene.scene_number).all()
    if not include_archived:
        scenes = [s for s in scenes if not (s.scene_config or {}).get("archived")]
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


@router.patch(
    "/projects/{project_id}/scenes/reorder",
    response_model=List[SceneDetailResponse],
    status_code=status.HTTP_200_OK,
)
def reorder_project_scenes(
    project_id: uuid.UUID,
    request: ReorderRequest,
    db: Session = Depends(get_db),
):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found",
        )

    for item in request.items:
        scene = db.get(Scene, item.id)
        if scene and (scene.project_id == project_id or (scene.story and scene.story.project_id == project_id)):
            LockMachineService.check_mutation_allowed(db, "SCENE", scene.id)
            scene.scene_number = item.order

    db.commit()
    return list_project_scenes(project_id=project_id, db=db)


@router.post(
    "/scenes/{scene_id}/duplicate",
    response_model=SceneDetailResponse,
    status_code=status.HTTP_201_CREATED,
)
def duplicate_scene(
    scene_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    orig = db.get(Scene, scene_id)
    if not orig:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scene '{scene_id}' not found",
        )

    # Find highest scene number in project
    max_num = db.query(func.max(Scene.scene_number)).filter(
        (Scene.project_id == orig.project_id)
    ).scalar() or 1

    new_scene = Scene(
        id=uuid.uuid4(),
        project_id=orig.project_id,
        story_id=orig.story_id,
        scene_number=max_num + 1,
        heading=f"{orig.heading or 'Scene'} (Copy)",
        description=orig.description,
        purpose=orig.purpose,
        setting=orig.setting,
        duration_seconds=orig.duration_seconds,
        narration=orig.narration,
        dialogue=orig.dialogue,
        scene_config=orig.scene_config,
        is_locked=False,
    )
    db.add(new_scene)
    db.flush()

    orig_shots = db.query(Shot).filter(Shot.scene_id == orig.id).order_by(Shot.shot_number).all()
    for oshot in orig_shots:
        nshot = Shot(
            id=uuid.uuid4(),
            scene_id=new_scene.id,
            shot_number=oshot.shot_number,
            shot_type=oshot.shot_type,
            source_asset_id=oshot.source_asset_id,
            source_metadata=oshot.source_metadata,
            provider_config=oshot.provider_config,
            visual_prompt=oshot.visual_prompt,
            image_prompt=oshot.image_prompt,
            video_prompt=oshot.video_prompt,
            camera=oshot.camera,
            subject=oshot.subject,
            action=oshot.action,
            duration_seconds=oshot.duration_seconds,
            is_locked=False,
            status="DRAFT",
        )
        db.add(nshot)

    db.commit()
    db.refresh(new_scene)
    return new_scene


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

    # Soft-archive scene and contained shots to preserve full historical and auditable lineage
    cfg = dict(scene.scene_config or {})
    cfg["archived"] = True
    scene.scene_config = cfg

    shots = db.query(Shot).filter(Shot.scene_id == scene_id).all()
    for s in shots:
        s.status = "ARCHIVED"

    db.commit()
    return None
