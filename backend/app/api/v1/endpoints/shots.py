import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from sqlalchemy.orm import joinedload
from app.models.shot import Shot
from app.models.scene import Scene
from app.services.storage.factory import get_storage_provider
from app.services.storage.base import ObjectStorageProvider
from app.services.hybrid_shot import HybridShotService
from app.services.lock_machine import LockMachineService
from app.models.generation_job import GenerationJob
from app.models.usage_ledger import UsageLedger
from app.schemas.shot import (
    ShotCreateRequest,
    ShotUpdateRequest,
    ShotDetailResponse,
    EffectiveShotConfigResponse,
    ReorderRequest,
)


router = APIRouter()


def _shot_to_response(shot: Shot, storage: Optional[ObjectStorageProvider] = None) -> ShotDetailResponse:
    resp = ShotDetailResponse.model_validate(shot)
    if shot.keyframe_asset:
        if storage is None:
            storage = get_storage_provider()
        resp.keyframe_url = storage.generate_presigned_url(
            shot.keyframe_asset.storage_bucket,
            shot.keyframe_asset.storage_key,
        )
    return resp




@router.post(
    "/scenes/{scene_id}/shots",
    response_model=ShotDetailResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_scene_shot(
    scene_id: uuid.UUID,
    request: ShotCreateRequest,
    db: Session = Depends(get_db),
    storage: ObjectStorageProvider = Depends(get_storage_provider),
):
    shot = HybridShotService.create_shot(db=db, scene_id=scene_id, request=request)
    return _shot_to_response(shot, storage)


@router.get(
    "/scenes/{scene_id}/shots",
    response_model=List[ShotDetailResponse],
    status_code=status.HTTP_200_OK,
)
def list_scene_shots(
    scene_id: uuid.UUID,
    include_archived: bool = False,
    db: Session = Depends(get_db),
    storage: ObjectStorageProvider = Depends(get_storage_provider),
):
    scene = db.get(Scene, scene_id)
    if not scene:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scene '{scene_id}' not found",
        )
    query = db.query(Shot).options(joinedload(Shot.keyframe_asset)).filter(Shot.scene_id == scene_id)
    if not include_archived:
        query = query.filter(Shot.status != "ARCHIVED")
    shots = query.order_by(Shot.shot_number).all()
    return [_shot_to_response(s, storage) for s in shots]


@router.get(
    "/shots/{shot_id}",
    response_model=ShotDetailResponse,
    status_code=status.HTTP_200_OK,
)
def get_shot(
    shot_id: uuid.UUID,
    db: Session = Depends(get_db),
    storage: ObjectStorageProvider = Depends(get_storage_provider),
):
    shot = db.query(Shot).options(joinedload(Shot.keyframe_asset)).filter(Shot.id == shot_id).first()
    if not shot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Shot '{shot_id}' not found",
        )
    return _shot_to_response(shot, storage)


@router.patch(
    "/shots/{shot_id}",
    response_model=ShotDetailResponse,
    status_code=status.HTTP_200_OK,
)
def update_shot(
    shot_id: uuid.UUID,
    request: ShotUpdateRequest,
    db: Session = Depends(get_db),
    storage: ObjectStorageProvider = Depends(get_storage_provider),
):
    shot = HybridShotService.update_shot(db=db, shot_id=shot_id, request=request)
    return _shot_to_response(shot, storage)


@router.delete(
    "/shots/{shot_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_shot(
    shot_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    shot = db.get(Shot, shot_id)
    if not shot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Shot '{shot_id}' not found",
        )

    LockMachineService.check_mutation_allowed(db, "SHOT", shot_id)

    # Soft-archive shot to preserve full production lineage and audit history
    shot.status = "ARCHIVED"
    db.commit()
    return None


@router.patch(
    "/scenes/{scene_id}/shots/reorder",
    response_model=List[ShotDetailResponse],
    status_code=status.HTTP_200_OK,
)
def reorder_scene_shots(
    scene_id: uuid.UUID,
    request: ReorderRequest,
    db: Session = Depends(get_db),
):
    scene = db.get(Scene, scene_id)
    if not scene:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scene '{scene_id}' not found",
        )

    for item in request.items:
        shot = db.get(Shot, item.id)
        if shot and shot.scene_id == scene_id:
            LockMachineService.check_mutation_allowed(db, "SHOT", shot.id)
            shot.shot_number = item.order

    db.commit()
    shots = db.query(Shot).options(joinedload(Shot.keyframe_asset)).filter(Shot.scene_id == scene_id).order_by(Shot.shot_number).all()
    storage = get_storage_provider()
    return [_shot_to_response(s, storage) for s in shots]



@router.get(
    "/shots/{shot_id}/effective-config",
    response_model=EffectiveShotConfigResponse,
    status_code=status.HTTP_200_OK,
)
def get_effective_shot_config(
    shot_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    config = HybridShotService.resolve_inherited_config(db=db, shot_id=shot_id)
    return config
