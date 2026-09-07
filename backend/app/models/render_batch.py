import uuid
from datetime import datetime, timezone
from typing import Optional, List, TYPE_CHECKING
from sqlalchemy import String, Integer, Float, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base_class import Base

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.assembly import AssemblyTimeline
    from app.models.render_job import RenderJob


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class RenderBatch(Base):
    __tablename__ = "render_batches"
    __table_args__ = (
        Index("ix_render_batches_project_id", "project_id"),
        Index("ix_render_batches_timeline_id", "timeline_id"),
        Index("ix_render_batches_status", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    timeline_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("assembly_timelines.id", ondelete="CASCADE"),
        nullable=False,
    )
    timeline_version: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(
        String(50), default="PROCESSING", nullable=False
    )
    total_variants: Mapped[int] = mapped_column(Integer, nullable=False)
    completed_variants: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_variants: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    estimated_total_cost_usd: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    # Relationships
    project: Mapped["Project"] = relationship("Project")
    timeline: Mapped["AssemblyTimeline"] = relationship("AssemblyTimeline")
    child_jobs: Mapped[List["RenderJob"]] = relationship(
        "RenderJob", back_populates="batch"
    )
