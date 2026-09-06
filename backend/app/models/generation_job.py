import uuid
from datetime import datetime, timezone
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, Text, Float, Integer, JSON, DateTime, ForeignKey, UniqueConstraint, Index, func, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base_class import Base

if TYPE_CHECKING:
    from app.models.shot import Shot
    from app.models.asset import Asset


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class GenerationJob(Base):
    __tablename__ = "generation_jobs"
    __table_args__ = (
        UniqueConstraint("shot_id", "idempotency_key", name="uq_generation_jobs_shot_idempotency_key"),
        Index("ix_generation_jobs_status", "status"),
        Index("ix_generation_jobs_job_type", "job_type"),
        Index(
            "uq_generation_jobs_active_shot",
            "shot_id",
            unique=True,
            sqlite_where=text("status IN ('PENDING', 'CLAIMED', 'SUBMITTING', 'SUBMITTED', 'POLLING', 'QUEUED', 'PROCESSING', 'CANCELLING', 'RECONCILIATION_REQUIRED')"),
            postgresql_where=text("status IN ('PENDING', 'CLAIMED', 'SUBMITTING', 'SUBMITTED', 'POLLING', 'QUEUED', 'PROCESSING', 'CANCELLING', 'RECONCILIATION_REQUIRED')"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    shot_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("shots.id", ondelete="CASCADE"),
        nullable=False,
    )
    job_type: Mapped[str] = mapped_column(
        String(50), default="VIDEO", nullable=False
    )
    provider_name: Mapped[str] = mapped_column(String(50), nullable=False)
    provider_job_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(
        String(50), default="PENDING", nullable=False
    )
    idempotency_key: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, index=True
    )
    cost_usd: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_retries: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    poll_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_polls: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    claimed_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    claim_token: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    claim_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    next_retry_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    next_poll_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    submission_attempt_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    payload: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    result: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    output_asset_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("assets.id", ondelete="SET NULL"),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    # Relationships
    shot: Mapped["Shot"] = relationship("Shot", back_populates="generation_jobs")
    output_asset: Mapped[Optional["Asset"]] = relationship("Asset")

