import uuid
from datetime import datetime, timezone
from typing import Optional, List, Any, TYPE_CHECKING
from sqlalchemy import String, Text, Integer, Float, Boolean, JSON, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base_class import Base

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.story import Story
    from app.models.shot import Shot


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Scene(Base):
    __tablename__ = "scenes"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    story_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("stories.id", ondelete="CASCADE"),
        nullable=True,
    )
    project_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    scene_number: Mapped[int] = mapped_column(Integer, nullable=False)
    heading: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    purpose: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    setting: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    duration_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    narration: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    dialogue: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    scene_config: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    # Relationships
    story: Mapped[Optional["Story"]] = relationship("Story", back_populates="scenes")
    project: Mapped[Optional["Project"]] = relationship("Project", back_populates="scenes", foreign_keys=[project_id])
    shots: Mapped[List["Shot"]] = relationship(
        "Shot", back_populates="scene", cascade="all, delete-orphan", order_by="Shot.shot_number"
    )
