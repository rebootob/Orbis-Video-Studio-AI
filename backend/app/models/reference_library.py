import uuid
from datetime import datetime, timezone
from typing import Optional, Any
from sqlalchemy import String, Text, Boolean, JSON, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base_class import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ProjectReference(Base):
    __tablename__ = "project_references"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reference_asset_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("assets.id", ondelete="SET NULL"),
        nullable=True,
    )
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    metadata_json: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )


class CharacterBible(Base):
    __tablename__ = "character_bibles"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    appearance: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    wardrobe: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    age_range: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    gender_presentation: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    nationality_cultural_context: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    personality: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    speaking_style: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    continuity_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reference_asset_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("assets.id", ondelete="SET NULL"),
        nullable=True,
    )
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )


class LocationBible(Base):
    __tablename__ = "location_bibles"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    environment: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    visual_features: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    lighting: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    time_of_day_default: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    continuity_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reference_asset_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("assets.id", ondelete="SET NULL"),
        nullable=True,
    )
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )


class StyleBible(Base):
    __tablename__ = "style_bibles"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    visual_style: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    camera_style: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    color_direction: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    lighting_style: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    composition_rules: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    realism_level: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    negative_constraints: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reference_asset_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("assets.id", ondelete="SET NULL"),
        nullable=True,
    )
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )


class BrandBible(Base):
    __tablename__ = "brand_bibles"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    brand_name: Mapped[str] = mapped_column(String(255), nullable=False)
    brand_colors: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    typography_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    do_and_dont_rules: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tone: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    mandatory_wording: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    continuity_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    logo_asset_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("assets.id", ondelete="SET NULL"),
        nullable=True,
    )
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )
