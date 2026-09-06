import uuid
from datetime import datetime, timezone
from typing import Optional, List, Any
from sqlalchemy import String, Integer, Float, Boolean, DateTime, ForeignKey, JSON, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class AssemblyTimeline(Base):
    __tablename__ = "assembly_timelines"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="DRAFT")  # DRAFT, READY, APPROVED
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

    scenes: Mapped[List["AssemblyScene"]] = relationship(
        "AssemblyScene", back_populates="timeline", cascade="all, delete-orphan", order_by="AssemblyScene.scene_order"
    )
    shot_placements: Mapped[List["AssemblyShotPlacement"]] = relationship(
        "AssemblyShotPlacement", back_populates="timeline", cascade="all, delete-orphan", order_by="AssemblyShotPlacement.shot_order"
    )
    checkpoints: Mapped[List["TimelineCheckpoint"]] = relationship(
        "TimelineCheckpoint", back_populates="timeline", cascade="all, delete-orphan", order_by="TimelineCheckpoint.checkpoint_number"
    )
    audits: Mapped[List["TimelineAudit"]] = relationship(
        "TimelineAudit", back_populates="timeline", cascade="all, delete-orphan", order_by="TimelineAudit.created_at"
    )


class AssemblyScene(Base):
    __tablename__ = "assembly_scenes"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    timeline_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("assembly_timelines.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    scene_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("scenes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    scene_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

    timeline: Mapped["AssemblyTimeline"] = relationship("AssemblyTimeline", back_populates="scenes")
    scene: Mapped["Scene"] = relationship("Scene")
    shot_placements: Mapped[List["AssemblyShotPlacement"]] = relationship(
        "AssemblyShotPlacement", back_populates="assembly_scene", cascade="all, delete-orphan", order_by="AssemblyShotPlacement.shot_order"
    )


class AssemblyShotPlacement(Base):
    __tablename__ = "assembly_shot_placements"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    timeline_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("assembly_timelines.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    assembly_scene_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("assembly_scenes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    scene_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("scenes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    shot_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("shots.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    shot_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    visual_asset_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("assets.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    source_type: Mapped[str] = mapped_column(String(50), nullable=False, default="VIDEO")  # VIDEO, IMAGE, KEYFRAME, MISSING
    trim_in: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    trim_out: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    effective_duration: Mapped[float] = mapped_column(Float, nullable=False, default=4.0)
    still_duration: Mapped[float] = mapped_column(Float, nullable=False, default=4.0)
    transition_to_next: Mapped[str] = mapped_column(String(50), nullable=False, default="CUT")  # CUT, FADE, DISSOLVE
    is_locked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

    timeline: Mapped["AssemblyTimeline"] = relationship("AssemblyTimeline", back_populates="shot_placements")
    assembly_scene: Mapped["AssemblyScene"] = relationship("AssemblyScene", back_populates="shot_placements")
    shot: Mapped["Shot"] = relationship("Shot")
    visual_asset: Mapped[Optional["Asset"]] = relationship("Asset")


class TimelineCheckpoint(Base):
    __tablename__ = "timeline_checkpoints"

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
    checkpoint_number: Mapped[int] = mapped_column(Integer, nullable=False)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    snapshot_data: Mapped[Any] = mapped_column(JSON, nullable=False)
    actor: Mapped[str] = mapped_column(String(100), nullable=False, default="system")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )

    timeline: Mapped["AssemblyTimeline"] = relationship("AssemblyTimeline", back_populates="checkpoints")


class TimelineAudit(Base):
    __tablename__ = "timeline_audits"

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
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    actor: Mapped[str] = mapped_column(String(100), nullable=False, default="system")
    change_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    snapshot_data: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )

    timeline: Mapped["AssemblyTimeline"] = relationship("AssemblyTimeline", back_populates="audits")
