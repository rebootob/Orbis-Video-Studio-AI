import uuid
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.asset_lock import AssetLock
from app.models.project import Project
from app.models.story import Story
from app.models.scene import Scene
from app.models.shot import Shot
from app.models.reference_library import CharacterBible, LocationBible
from app.services.video_modes import validate_lock_target, ALLOWED_LOCK_TARGETS


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class LockMachineService:
    @staticmethod
    def _get_entity_model_and_instance(db: Session, entity_type: str, entity_id: uuid.UUID):
        normalized_type = validate_lock_target(entity_type)
        if normalized_type == "SHOT":
            return Shot, db.get(Shot, entity_id)
        elif normalized_type == "SCENE":
            return Scene, db.get(Scene, entity_id)
        elif normalized_type == "SCRIPT":
            # SCRIPT maps to Story model or dedicated script context
            return Story, db.get(Story, entity_id)
        elif normalized_type == "CHARACTER":
            return CharacterBible, db.get(CharacterBible, entity_id)
        elif normalized_type == "LOCATION":
            return LocationBible, db.get(LocationBible, entity_id)
        elif normalized_type in ("VOICE", "TIMING"):
            # May be tracked via lock table for timeline/voice entities
            return None, None
        return None, None

    @classmethod
    def _resolve_entity_project_id(cls, instance) -> Optional[uuid.UUID]:
        if instance is None:
            return None
        if hasattr(instance, "project_id") and instance.project_id:
            return instance.project_id
        if isinstance(instance, Scene):
            return instance.project_id or (instance.story.project_id if instance.story else None)
        if isinstance(instance, Shot):
            if instance.scene:
                return instance.scene.project_id or (instance.scene.story.project_id if instance.scene.story else None)
        return None

    @classmethod
    def lock(
        cls,
        db: Session,
        project_id: uuid.UUID,
        entity_type: str,
        entity_id: uuid.UUID,
        actor: str = "system",
        reason: Optional[str] = None,
    ) -> AssetLock:
        norm_type = validate_lock_target(entity_type)
        project = db.get(Project, project_id)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project '{project_id}' not found",
            )

        model_cls, instance = cls._get_entity_model_and_instance(db, norm_type, entity_id)
        if model_cls is not None and instance is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{norm_type} entity '{entity_id}' not found",
            )

        # Verify entity project ownership where applicable
        entity_project_id = cls._resolve_entity_project_id(instance)
        if entity_project_id is not None and entity_project_id != project_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{norm_type} '{entity_id}' does not belong to Project '{project_id}'",
            )

        lock_record = db.query(AssetLock).filter(
            AssetLock.entity_type == norm_type,
            AssetLock.entity_id == entity_id,
        ).first()

        if lock_record is not None and lock_record.project_id != project_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Lock for {norm_type} '{entity_id}' belongs to Project '{lock_record.project_id}', not Project '{project_id}'",
            )

        now = utc_now()
        if lock_record is None:
            lock_record = AssetLock(
                id=uuid.uuid4(),
                project_id=project_id,
                entity_type=norm_type,
                entity_id=entity_id,
                is_locked=True,
                locked_by=actor,
                locked_at=now,
                lock_reason=reason,
                created_at=now,
                updated_at=now,
            )
            db.add(lock_record)
        else:
            lock_record.is_locked = True
            lock_record.locked_by = actor
            lock_record.locked_at = now
            lock_record.lock_reason = reason
            lock_record.updated_at = now

        # Update entity instance is_locked attribute if present
        if instance is not None and hasattr(instance, "is_locked"):
            instance.is_locked = True

        db.commit()
        db.refresh(lock_record)
        return lock_record

    @classmethod
    def unlock(
        cls,
        db: Session,
        project_id: uuid.UUID,
        entity_type: str,
        entity_id: uuid.UUID,
        actor: str = "system",
        reason: Optional[str] = None,
    ) -> AssetLock:
        norm_type = validate_lock_target(entity_type)
        project = db.get(Project, project_id)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project '{project_id}' not found",
            )

        model_cls, instance = cls._get_entity_model_and_instance(db, norm_type, entity_id)
        if model_cls is not None and instance is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{norm_type} entity '{entity_id}' not found",
            )

        # Verify entity project ownership where applicable
        entity_project_id = cls._resolve_entity_project_id(instance)
        if entity_project_id is not None and entity_project_id != project_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{norm_type} '{entity_id}' does not belong to Project '{project_id}'",
            )

        lock_record = db.query(AssetLock).filter(
            AssetLock.entity_type == norm_type,
            AssetLock.entity_id == entity_id,
        ).first()

        # Reject if existing lock record belongs to another project
        if lock_record is not None and lock_record.project_id != project_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Lock for {norm_type} '{entity_id}' belongs to Project '{lock_record.project_id}', not Project '{project_id}'",
            )

        now = utc_now()
        if lock_record is None:
            # Create unlocked audit record
            lock_record = AssetLock(
                id=uuid.uuid4(),
                project_id=project_id,
                entity_type=norm_type,
                entity_id=entity_id,
                is_locked=False,
                unlocked_by=actor,
                unlocked_at=now,
                unlock_reason=reason,
                created_at=now,
                updated_at=now,
            )
            db.add(lock_record)
        else:
            # Idempotent unlock: update audit info
            lock_record.is_locked = False
            lock_record.unlocked_by = actor
            lock_record.unlocked_at = now
            lock_record.unlock_reason = reason
            lock_record.updated_at = now

        # Update entity instance is_locked attribute if present
        if instance is not None and hasattr(instance, "is_locked"):
            instance.is_locked = False

        db.commit()
        db.refresh(lock_record)
        return lock_record

    @classmethod
    def is_entity_locked(cls, db: Session, entity_type: str, entity_id: uuid.UUID) -> bool:
        norm_type = validate_lock_target(entity_type)
        lock_record = db.query(AssetLock).filter(
            AssetLock.entity_type == norm_type,
            AssetLock.entity_id == entity_id,
        ).first()
        if lock_record is not None:
            return lock_record.is_locked

        model_cls, instance = cls._get_entity_model_and_instance(db, norm_type, entity_id)
        if instance is not None and hasattr(instance, "is_locked"):
            return bool(instance.is_locked)
        return False

    @classmethod
    def get_lock(cls, db: Session, entity_type: str, entity_id: uuid.UUID) -> Optional[AssetLock]:
        norm_type = validate_lock_target(entity_type)
        return db.query(AssetLock).filter(
            AssetLock.entity_type == norm_type,
            AssetLock.entity_id == entity_id,
        ).first()

    @classmethod
    def get_project_locks(cls, db: Session, project_id: uuid.UUID) -> List[AssetLock]:
        return db.query(AssetLock).filter(AssetLock.project_id == project_id).all()

    @classmethod
    def check_mutation_allowed(cls, db: Session, entity_type: str, entity_id: uuid.UUID):
        norm_type = validate_lock_target(entity_type)
        if cls.is_entity_locked(db, norm_type, entity_id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Cannot mutate locked {norm_type} '{entity_id}'. Explicit unlock required.",
            )

        # Check hierarchical parent locks (fail closed)
        if norm_type == "SHOT":
            shot = db.get(Shot, entity_id)
            if shot and shot.scene_id:
                if cls.is_entity_locked(db, "SCENE", shot.scene_id):
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"Cannot mutate Shot '{entity_id}' because parent SCENE '{shot.scene_id}' is locked.",
                    )
                if shot.scene and shot.scene.story_id:
                    if cls.is_entity_locked(db, "SCRIPT", shot.scene.story_id):
                        raise HTTPException(
                            status_code=status.HTTP_409_CONFLICT,
                            detail=f"Cannot mutate Shot '{entity_id}' because parent SCRIPT '{shot.scene.story_id}' is locked.",
                        )
        elif norm_type == "SCENE":
            scene = db.get(Scene, entity_id)
            if scene and scene.story_id:
                if cls.is_entity_locked(db, "SCRIPT", scene.story_id):
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"Cannot mutate Scene '{entity_id}' because parent SCRIPT '{scene.story_id}' is locked.",
                    )

    @classmethod
    def check_regeneration_allowed(cls, db: Session, shot_id: uuid.UUID):
        shot = db.get(Shot, shot_id)
        if not shot:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Shot '{shot_id}' not found",
            )
        if cls.is_entity_locked(db, "SHOT", shot_id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Cannot regenerate locked Shot '{shot_id}'. Explicit unlock required.",
            )
        if shot.scene_id and cls.is_entity_locked(db, "SCENE", shot.scene_id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Cannot regenerate Shot '{shot_id}' because parent SCENE '{shot.scene_id}' is locked.",
            )
        if shot.scene and shot.scene.story_id and cls.is_entity_locked(db, "SCRIPT", shot.scene.story_id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Cannot regenerate Shot '{shot_id}' because parent SCRIPT '{shot.scene.story_id}' is locked.",
            )
