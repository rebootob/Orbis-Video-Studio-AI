import uuid
from datetime import datetime, timezone
from typing import Optional, Any, List, TYPE_CHECKING
from sqlalchemy import String, Integer, JSON, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base_class import Base

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.audio_history import AudioPlanVersion


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class AudioPlan(Base):
    __tablename__ = "audio_plans"
    __table_args__ = (
        Index("ix_audio_plans_project_id", "project_id", unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(50), default="DRAFT", nullable=False)
    plan_data: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    # Relationships
    project: Mapped["Project"] = relationship("Project")
    versions: Mapped[List["AudioPlanVersion"]] = relationship("AudioPlanVersion", back_populates="plan", cascade="all, delete-orphan", order_by="AudioPlanVersion.version_number.desc()")
