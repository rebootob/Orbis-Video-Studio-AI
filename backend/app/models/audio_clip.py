import uuid
from enum import Enum
from datetime import datetime, timezone
from typing import Optional, Any, TYPE_CHECKING
from sqlalchemy import String, Text, Integer, Float, Boolean, JSON, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base_class import Base

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.scene import Scene
    from app.models.shot import Shot
    from app.models.asset import Asset


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class AudioSourceType(str, Enum):
    EMBEDDED_VIDEO_AUDIO = "EMBEDDED_VIDEO_AUDIO"
    GENERATED_AUDIO = "GENERATED_AUDIO"
    IMPORTED_AUDIO = "IMPORTED_AUDIO"
    RECORDED_AUDIO = "RECORDED_AUDIO"


class AudioType(str, Enum):
    ORIGINAL_AUDIO = "ORIGINAL_AUDIO"
    VO = "VO"
    DIALOGUE = "DIALOGUE"
    BGM = "BGM"
    SFX = "SFX"
    AMBIENCE = "AMBIENCE"


class AudioGenerationMode(str, Enum):
    WITH_VIDEO = "WITH_VIDEO"
    SEPARATE_AUDIO = "SEPARATE_AUDIO"
    EMBEDDED_EXISTING = "EMBEDDED_EXISTING"


class AudioScope(str, Enum):
    PROJECT = "PROJECT"
    SCENE = "SCENE"
    SHOT = "SHOT"
    VIDEO_CLIP = "VIDEO_CLIP"


class DuckingRole(str, Enum):
    FOREGROUND = "FOREGROUND"
    BACKGROUND = "BACKGROUND"
    EVENT = "EVENT"
    EMBEDDED = "EMBEDDED"


class AudioClip(Base):
    __tablename__ = "audio_clips"
    __table_args__ = (
        Index("ix_audio_clips_project_id", "project_id"),
        Index("ix_audio_clips_scene_id", "scene_id"),
        Index("ix_audio_clips_shot_id", "shot_id"),
        Index("ix_audio_clips_audio_type", "audio_type"),
        Index("ix_audio_clips_scope", "scope"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    scene_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("scenes.id", ondelete="CASCADE"),
        nullable=True,
    )
    shot_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("shots.id", ondelete="CASCADE"),
        nullable=True,
    )
    video_asset_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("assets.id", ondelete="SET NULL"),
        nullable=True,
    )
    asset_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("assets.id", ondelete="SET NULL"),
        nullable=True,
    )

    audio_type: Mapped[str] = mapped_column(String(50), nullable=False)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    generation_mode: Mapped[str] = mapped_column(String(50), nullable=False)
    scope: Mapped[str] = mapped_column(String(50), nullable=False)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    prompt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    start_time: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    duration_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    volume: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    mute: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    fade_in: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    fade_out: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    ducking_role: Mapped[str] = mapped_column(String(50), default="BACKGROUND", nullable=False)
    ducking_amount_db: Mapped[float] = mapped_column(Float, default=-12.0, nullable=False)

    language: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    speaker: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    provenance: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="PENDING", nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    # Relationships
    project: Mapped["Project"] = relationship("Project")
    scene: Mapped[Optional["Scene"]] = relationship("Scene")
    shot: Mapped[Optional["Shot"]] = relationship("Shot")
    asset: Mapped[Optional["Asset"]] = relationship("Asset", foreign_keys=[asset_id])
    video_asset: Mapped[Optional["Asset"]] = relationship("Asset", foreign_keys=[video_asset_id])
