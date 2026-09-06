import uuid
from datetime import datetime, timezone
from typing import Optional, List, Any, TYPE_CHECKING
from sqlalchemy import String, Text, Integer, Float, Boolean, JSON, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base_class import Base

if TYPE_CHECKING:
    from app.models.scene import Scene
    from app.models.generation_job import GenerationJob
    from app.models.asset import Asset


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Shot(Base):
    __tablename__ = "shots"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    scene_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("scenes.id", ondelete="CASCADE"),
        nullable=False,
    )
    shot_number: Mapped[int] = mapped_column(Integer, nullable=False)
    shot_type: Mapped[str] = mapped_column(String(50), nullable=False)
    source_asset_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("assets.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    source_metadata: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    provider_config: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    visual_prompt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    image_prompt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    video_prompt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    camera: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    subject: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    action: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    duration_seconds: Mapped[float] = mapped_column(Float, default=4.0, nullable=False)
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="PENDING", nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    # Relationships
    scene: Mapped["Scene"] = relationship("Scene", back_populates="shots")
    source_asset: Mapped[Optional["Asset"]] = relationship("Asset", foreign_keys=[source_asset_id])
    generation_jobs: Mapped[List["GenerationJob"]] = relationship(
        "GenerationJob", back_populates="shot", cascade="all, delete-orphan"
    )
