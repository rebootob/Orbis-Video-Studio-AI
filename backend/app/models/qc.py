import uuid
from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy import String, Integer, DateTime, ForeignKey, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class QCRun(Base):
    __tablename__ = "qc_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    timeline_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("assembly_timelines.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    timeline_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="PENDING", index=True
    )  # PENDING, RUNNING, PASSED, BLOCKED, ERROR
    blocker_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    warning_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    actor: Mapped[str] = mapped_column(String(100), nullable=False, default="system")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

    project: Mapped["Project"] = relationship("Project")
    timeline: Mapped["AssemblyTimeline"] = relationship("AssemblyTimeline")
    findings: Mapped[List["QCFinding"]] = relationship(
        "QCFinding", back_populates="qc_run", cascade="all, delete-orphan", order_by="QCFinding.created_at"
    )
    decisions: Mapped[List["WarningDecision"]] = relationship(
        "WarningDecision", back_populates="qc_run", cascade="all, delete-orphan"
    )
    approvals: Mapped[List["ApprovalRecord"]] = relationship(
        "ApprovalRecord", back_populates="qc_run", cascade="all, delete-orphan"
    )


class QCFinding(Base):
    __tablename__ = "qc_findings"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    qc_run_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("qc_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    timeline_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("assembly_timelines.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    rule_code: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(
        String(20), nullable=False, index=True
    )  # BLOCKER, WARNING (PASS is NOT a finding severity!)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    why_it_matters: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    recommended_fix: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    target_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    target_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True), nullable=True, index=True
    )
    target_label: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    action_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )

    qc_run: Mapped["QCRun"] = relationship("QCRun", back_populates="findings")
    decisions: Mapped[List["WarningDecision"]] = relationship(
        "WarningDecision", back_populates="finding", cascade="all, delete-orphan"
    )


class WarningDecision(Base):
    __tablename__ = "qc_warning_decisions"
    __table_args__ = (
        UniqueConstraint("finding_id", "decision_sequence", name="uq_qc_warning_decisions_finding_seq"),
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
    qc_run_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("qc_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    finding_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("qc_findings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    timeline_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("assembly_timelines.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    decision: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # FIX_REQUIRED, ACCEPTED_WITH_REASON
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    actor: Mapped[str] = mapped_column(String(100), nullable=False, default="USER")
    decided_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    decision_sequence: Mapped[int] = mapped_column(Integer, nullable=False, default=1, index=True)

    qc_run: Mapped["QCRun"] = relationship("QCRun", back_populates="decisions")
    finding: Mapped["QCFinding"] = relationship("QCFinding", back_populates="decisions")
    timeline: Mapped["AssemblyTimeline"] = relationship("AssemblyTimeline")


class ApprovalRecord(Base):
    __tablename__ = "production_approvals"
    __table_args__ = (
        UniqueConstraint("project_id", "timeline_id", name="uq_production_approvals_project_timeline"),
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
    timeline_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("assembly_timelines.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    timeline_version: Mapped[int] = mapped_column(Integer, nullable=False)
    qc_run_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("qc_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="APPROVED"
    )  # APPROVED, REVOKED
    actor: Mapped[str] = mapped_column(String(100), nullable=False, default="USER")
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    approved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )

    project: Mapped["Project"] = relationship("Project")
    timeline: Mapped["AssemblyTimeline"] = relationship("AssemblyTimeline")
    qc_run: Mapped["QCRun"] = relationship("QCRun", back_populates="approvals")
