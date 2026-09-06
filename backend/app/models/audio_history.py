import uuid
from datetime import datetime, timezone
from typing import Optional, Any, TYPE_CHECKING
from sqlalchemy import String, Text, Integer, Float, Boolean, JSON, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base_class import Base

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.audio_plan import AudioPlan
    from app.models.audio_clip import AudioClip


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class AudioPlanVersion(Base):
    __tablename__ = "audio_plan_versions"
    __table_args__ = (
        Index("ix_audio_plan_versions_project_id", "project_id"),
        Index("ix_audio_plan_versions_plan_id", "audio_plan_id"),
        Index("ix_audio_plan_versions_plan_version", "audio_plan_id", "version_number"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    audio_plan_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("audio_plans.id", ondelete="CASCADE"),
        nullable=False,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    plan_data: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    actor: Mapped[str] = mapped_column(String(100), default="USER", nullable=False)
    action: Mapped[str] = mapped_column(String(50), default="CREATE", nullable=False)
    change_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    # Relationships
    project: Mapped["Project"] = relationship("Project")
    plan: Mapped["AudioPlan"] = relationship("AudioPlan", back_populates="versions")


class AudioClipHistory(Base):
    __tablename__ = "audio_clip_history"
    __table_args__ = (
        Index("ix_audio_clip_history_project_id", "project_id"),
        Index("ix_audio_clip_history_clip_id", "clip_id"),
        Index("ix_audio_clip_history_clip_version", "clip_id", "version_number"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    clip_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("audio_clips.id", ondelete="CASCADE"),
        nullable=False,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
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
    status: Mapped[str] = mapped_column(String(50), default="PENDING", nullable=False)
    asset_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("assets.id", ondelete="SET NULL"),
        nullable=True,
    )
    provenance: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)

    actor: Mapped[str] = mapped_column(String(100), default="USER", nullable=False)
    action: Mapped[str] = mapped_column(String(50), default="CREATE", nullable=False)
    change_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    # Relationships
    project: Mapped["Project"] = relationship("Project")
    clip: Mapped["AudioClip"] = relationship("AudioClip", back_populates="history")
