import uuid
from datetime import datetime, timezone
from typing import Optional, TYPE_CHECKING
from enum import Enum
from sqlalchemy import String, Text, Float, Integer, JSON, DateTime, ForeignKey, Index, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base_class import Base

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.assembly import AssemblyTimeline
    from app.models.qc import ApprovalRecord
    from app.models.asset import Asset


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class RenderJobStatus(str, Enum):
    QUEUED = "QUEUED"
    CLAIMED = "CLAIMED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    RECONCILIATION_REQUIRED = "RECONCILIATION_REQUIRED"


class RenderJob(Base):
    __tablename__ = "render_jobs"
    __table_args__ = (
        Index("ix_render_jobs_status", "status"),
        Index("ix_render_jobs_idempotency_key", "idempotency_key"),
        Index("ix_render_jobs_project_id", "project_id"),
        Index("ix_render_jobs_timeline_id", "timeline_id"),
        Index(
            "uq_render_jobs_active_timeline",
            "project_id",
            "timeline_id",
            unique=True,
            sqlite_where=text("status IN ('QUEUED', 'CLAIMED', 'RUNNING')"),
            postgresql_where=text("status IN ('QUEUED', 'CLAIMED', 'RUNNING')"),
        ),
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
    approval_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("production_approvals.id", ondelete="CASCADE"),
        nullable=False,
    )
    render_profile: Mapped[str] = mapped_column(
        String(50), default="MASTER_HD", nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(50), default=RenderJobStatus.QUEUED.value, nullable=False
    )
    idempotency_key: Mapped[str] = mapped_column(
        String(255), nullable=False
    )
    output_asset_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("assets.id", ondelete="SET NULL"),
        nullable=True,
    )
    progress: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    claimed_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    claim_token: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    claim_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_retries: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    estimated_cost_usd: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    actual_cost_usd: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    render_metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, default=dict)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    # Relationships
    project: Mapped["Project"] = relationship("Project")
    timeline: Mapped["AssemblyTimeline"] = relationship("AssemblyTimeline")
    approval: Mapped["ApprovalRecord"] = relationship("ApprovalRecord")
    output_asset: Mapped[Optional["Asset"]] = relationship("Asset")
