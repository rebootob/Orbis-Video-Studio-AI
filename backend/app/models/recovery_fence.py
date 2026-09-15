"""Provider execution fence and recovery failure audit models for bounded job recovery."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional, TYPE_CHECKING
from sqlalchemy import (
    String,
    DateTime,
    Integer,
    BigInteger,
    ForeignKey,
    CheckConstraint,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base_class import Base

if TYPE_CHECKING:
    pass


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ProviderExecutionFence(Base):
    __tablename__ = "provider_execution_fences"

    fence_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    provider_name: Mapped[str] = mapped_column(String(64), nullable=False, default="vidu")
    provider_job_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    execution_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    task_id: Mapped[str] = mapped_column(String(128), nullable=False)
    authorized_commit_sha: Mapped[str] = mapped_column(String(64), nullable=False)
    runtime_target: Mapped[str] = mapped_column(String(64), nullable=False)
    owner_evidence_anchor: Mapped[str] = mapped_column(String(256), nullable=False)
    auth_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    auth_nonce: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    auth_issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    network_get_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    storage_intent_bucket: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    storage_intent_key: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    storage_intent_sha256: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    storage_intent_bytes: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    storage_is_new_object: Mapped[str] = mapped_column(String(16), nullable=False, default="UNKNOWN")
    target_asset_id: Mapped[Optional[uuid.UUID]] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    target_job_id: Mapped[Optional[uuid.UUID]] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    target_project_id: Mapped[Optional[uuid.UUID]] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    __table_args__ = (
        UniqueConstraint("provider_name", "provider_job_id", name="uq_provider_job_fence"),
        CheckConstraint("network_get_attempts <= 1", name="chk_network_get_attempts"),
    )

    audits: Mapped[list["RecoveryFailureAudit"]] = relationship(
        "RecoveryFailureAudit", back_populates="fence", cascade="all, delete-orphan"
    )


class RecoveryFailureAudit(Base):
    __tablename__ = "recovery_failure_audits"

    audit_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    fence_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("provider_execution_fences.fence_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    provider_job_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    failure_stage: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    error_class: Mapped[str] = mapped_column(String(128), nullable=False)
    error_message: Mapped[str] = mapped_column(String(512), nullable=False)
    orphan_storage_bucket: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    orphan_storage_key: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    db_transaction_state: Mapped[str] = mapped_column(String(64), nullable=False)
    compensation_status: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    fence: Mapped[Optional["ProviderExecutionFence"]] = relationship(
        "ProviderExecutionFence", back_populates="audits"
    )
