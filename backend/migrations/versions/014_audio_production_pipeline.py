"""Add audio_plans and audio_clips tables for Core V1 Audio Production.

Revision ID: 014_audio_production_pipeline
Revises: 013_image_keyframe_pipeline
Create Date: 2026-09-06
"""
from alembic import op
import sqlalchemy as sa


revision = "014_audio_production_pipeline"
down_revision = "013_image_keyframe_pipeline"
branch_labels = None
depends_on = None


def upgrade():
    # 1. Create audio_plans table
    op.create_table(
        "audio_plans",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("project_id", sa.Uuid(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="DRAFT"),
        sa.Column("plan_data", sa.JSON(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_audio_plans_project_id", "audio_plans", ["project_id"], unique=True)

    # 2. Create audio_clips table
    op.create_table(
        "audio_clips",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("project_id", sa.Uuid(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("scene_id", sa.Uuid(), sa.ForeignKey("scenes.id", ondelete="CASCADE"), nullable=True),
        sa.Column("shot_id", sa.Uuid(), sa.ForeignKey("shots.id", ondelete="CASCADE"), nullable=True),
        sa.Column("video_asset_id", sa.Uuid(), sa.ForeignKey("assets.id", ondelete="SET NULL"), nullable=True),
        sa.Column("asset_id", sa.Uuid(), sa.ForeignKey("assets.id", ondelete="SET NULL"), nullable=True),
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
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("provenance", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="PENDING"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_audio_clips_project_id", "audio_clips", ["project_id"])
    op.create_index("ix_audio_clips_scene_id", "audio_clips", ["scene_id"])
    op.create_index("ix_audio_clips_shot_id", "audio_clips", ["shot_id"])
    op.create_index("ix_audio_clips_audio_type", "audio_clips", ["audio_type"])
    op.create_index("ix_audio_clips_scope", "audio_clips", ["scope"])


def downgrade():
    op.drop_table("audio_clips")
    op.drop_table("audio_plans")
