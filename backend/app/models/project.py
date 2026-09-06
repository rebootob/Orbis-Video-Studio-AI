import uuid
from datetime import datetime, timezone
from typing import Optional, List, Any, TYPE_CHECKING
from sqlalchemy import String, Text, Float, JSON, DateTime, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base_class import Base

if TYPE_CHECKING:
    from app.models.story import Story
    from app.models.asset import Asset
    from app.models.scene import Scene
    from app.models.asset_lock import AssetLock


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="DRAFT", nullable=False)
    video_mode: Mapped[str] = mapped_column(String(50), default="STORY", nullable=False)
    purpose: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    target_platform: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    target_duration_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    preferred_aspect_ratio: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    mode_config: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    default_config: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    # Relationships
    story: Mapped[Optional["Story"]] = relationship(
        "Story", back_populates="project", cascade="all, delete-orphan", uselist=False
    )
    scenes: Mapped[List["Scene"]] = relationship(
        "Scene", back_populates="project", cascade="all, delete-orphan", foreign_keys="Scene.project_id"
    )
    assets: Mapped[List["Asset"]] = relationship(
        "Asset", back_populates="project", cascade="all, delete-orphan"
    )
    locks: Mapped[List["AssetLock"]] = relationship(
        "AssetLock", back_populates="project", cascade="all, delete-orphan"
    )
