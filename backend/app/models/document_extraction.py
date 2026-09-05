import uuid
from datetime import datetime, timezone
from typing import Optional, Any, List, TYPE_CHECKING
from sqlalchemy import String, Text, Integer, Float, DateTime, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base_class import Base

if TYPE_CHECKING:
    from app.models.asset import Asset


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class DocumentExtraction(Base):
    __tablename__ = "document_extractions"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    asset_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("assets.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    document_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="SUCCESS")
    extracted_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    segment_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    character_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    extraction_method: Mapped[str] = mapped_column(String(50), nullable=False)
    extraction_duration_ms: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    segments: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    warnings: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    # Relationship
    asset: Mapped["Asset"] = relationship("Asset", back_populates="document_extraction")
