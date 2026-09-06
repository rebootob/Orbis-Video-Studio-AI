"""Add audio_plan_versions and audio_clip_history tables.

Revision ID: 015_audio_history_and_lock_audit
Revises: 014_audio_production_pipeline
Create Date: 2026-09-06
"""
from alembic import op
import sqlalchemy as sa


revision = "015_audio_history_and_lock_audit"
down_revision = "014_audio_production_pipeline"
branch_labels = None
depends_on = None


def upgrade():
    # 1. Create audio_plan_versions table
    op.create_table(
        "audio_plan_versions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("audio_plan_id", sa.Uuid(), sa.ForeignKey("audio_plans.id", ondelete="CASCADE"), nullable=False),
        sa.Column("project_id", sa.Uuid(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("plan_data", sa.JSON(), nullable=True),
        sa.Column("actor", sa.String(length=100), nullable=False, server_default="USER"),
        sa.Column("action", sa.String(length=50), nullable=False, server_default="CREATE"),
        sa.Column("change_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_audio_plan_versions_project_id", "audio_plan_versions", ["project_id"])
    op.create_index("ix_audio_plan_versions_plan_id", "audio_plan_versions", ["audio_plan_id"])
    op.create_index("ix_audio_plan_versions_plan_version", "audio_plan_versions", ["audio_plan_id", "version_number"])

    # 2. Create audio_clip_history table
    op.create_table(
        "audio_clip_history",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("clip_id", sa.Uuid(), sa.ForeignKey("audio_clips.id", ondelete="CASCADE"), nullable=False),
        sa.Column("project_id", sa.Uuid(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("audio_type", sa.String(length=50), nullable=False),
        sa.Column("source_type", sa.String(length=50), nullable=False),
        sa.Column("generation_mode", sa.String(length=50), nullable=False),
        sa.Column("scope", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=True),
        sa.Column("start_time", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("duration_seconds", sa.Float(), nullable=True),
        sa.Column("volume", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("mute", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("fade_in", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("fade_out", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("ducking_role", sa.String(length=50), nullable=False, server_default="BACKGROUND"),
        sa.Column("ducking_amount_db", sa.Float(), nullable=False, server_default="-12.0"),
        sa.Column("language", sa.String(length=50), nullable=True),
        sa.Column("speaker", sa.String(length=100), nullable=True),
        sa.Column("is_locked", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="PENDING"),
        sa.Column("asset_id", sa.Uuid(), sa.ForeignKey("assets.id", ondelete="SET NULL"), nullable=True),
        sa.Column("provenance", sa.JSON(), nullable=True),
        sa.Column("actor", sa.String(length=100), nullable=False, server_default="USER"),
        sa.Column("action", sa.String(length=50), nullable=False, server_default="CREATE"),
        sa.Column("change_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_audio_clip_history_project_id", "audio_clip_history", ["project_id"])
    op.create_index("ix_audio_clip_history_clip_id", "audio_clip_history", ["clip_id"])
    op.create_index("ix_audio_clip_history_clip_version", "audio_clip_history", ["clip_id", "version_number"])


def downgrade():
    op.drop_table("audio_clip_history")
    op.drop_table("audio_plan_versions")
