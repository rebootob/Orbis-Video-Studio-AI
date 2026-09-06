import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.lock_machine import LockMachineService
from app.schemas.lock import LockEntityRequest, UnlockEntityRequest, AssetLockResponse

router = APIRouter()


@router.post(
    "/locks/lock",
    response_model=AssetLockResponse,
    status_code=status.HTTP_200_OK,
)
def lock_entity(
    request: LockEntityRequest,
    db: Session = Depends(get_db),
):
    lock = LockMachineService.lock(
        db=db,
        project_id=request.project_id,
        entity_type=request.entity_type,
        entity_id=request.entity_id,
        actor=request.actor,
        reason=request.reason,
    )
    return lock


@router.post(
    "/locks/unlock",
    response_model=AssetLockResponse,
    status_code=status.HTTP_200_OK,
)
def unlock_entity(
    request: UnlockEntityRequest,
    db: Session = Depends(get_db),
):
    lock = LockMachineService.unlock(
        db=db,
        project_id=request.project_id,
        entity_type=request.entity_type,
        entity_id=request.entity_id,
        actor=request.actor,
        reason=request.reason,
    )
    return lock


@router.get(
    "/locks/{entity_type}/{entity_id}",
    response_model=AssetLockResponse,
    status_code=status.HTTP_200_OK,
)
def get_lock_status(
    entity_type: str,
    entity_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    lock = LockMachineService.get_lock(db=db, entity_type=entity_type, entity_id=entity_id)
    if not lock:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lock record for {entity_type} '{entity_id}' not found",
        )
    return lock


@router.get(
    "/projects/{project_id}/locks",
    response_model=List[AssetLockResponse],
    status_code=status.HTTP_200_OK,
)
def list_project_locks(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    locks = LockMachineService.get_project_locks(db=db, project_id=project_id)
    return locks
