import uuid
from datetime import datetime, timezone
from typing import Optional, List, Any, TYPE_CHECKING
from sqlalchemy import String, Text, Float, JSON, DateTime, ForeignKey, Index, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base_class import Base

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.shot import Shot
    from app.models.generation_job import GenerationJob


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class UsageLedger(Base):
    __tablename__ = "usage_ledger"
    __table_args__ = (
        Index("ix_usage_ledger_project_status", "project_id", "cost_status"),
        Index(
            "uq_usage_ledger_project_idempotency_key",
            "project_id",
            "idempotency_key",
            unique=True,
            postgresql_where=text("idempotency_key IS NOT NULL"),
            sqlite_where=text("idempotency_key IS NOT NULL"),
        ),
        Index(
            "uq_usage_ledger_job_operation",
            "job_id",
            "operation",
            unique=True,
            postgresql_where=text("job_id IS NOT NULL"),
            sqlite_where=text("job_id IS NOT NULL"),
        ),
        Index(
            "uq_usage_ledger_provider_event",
            "provider",
            "provider_event_id",
            unique=True,
            postgresql_where=text("provider_event_id IS NOT NULL"),
            sqlite_where=text("provider_event_id IS NOT NULL"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    shot_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("shots.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    job_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("generation_jobs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    provider: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    operation: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    usage_units: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    estimated_cost: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    actual_cost: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    currency: Mapped[str] = mapped_column(String(10), default="USD", nullable=False)
    cost_status: Mapped[str] = mapped_column(
        String(20), default="ESTIMATED", nullable=False, index=True
    )
    provider_event_id: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, index=True
    )
    idempotency_key: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, index=True
    )
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="usage_ledger_entries")
    shot: Mapped[Optional["Shot"]] = relationship("Shot")
    job: Mapped[Optional["GenerationJob"]] = relationship("GenerationJob")
    adjustments: Mapped[List["LedgerAdjustment"]] = relationship(
        "LedgerAdjustment",
        back_populates="ledger_entry",
        cascade="all, delete-orphan",
        order_by="LedgerAdjustment.created_at",
    )


class LedgerAdjustment(Base):
    __tablename__ = "ledger_adjustments"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    ledger_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("usage_ledger.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    actor: Mapped[str] = mapped_column(String(255), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    previous_cost: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    adjusted_cost: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    # Relationships
    ledger_entry: Mapped["UsageLedger"] = relationship(
        "UsageLedger", back_populates="adjustments"
    )
