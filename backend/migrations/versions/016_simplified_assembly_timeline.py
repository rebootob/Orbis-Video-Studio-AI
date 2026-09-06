"""Add assembly_timelines, assembly_scenes, assembly_shot_placements, timeline_checkpoints, and timeline_audits tables.

Revision ID: 016_simplified_assembly_timeline
Revises: 015_audio_history_and_lock_audit
Create Date: 2026-09-07
"""
from alembic import op
import sqlalchemy as sa

revision = "016_simplified_assembly_timeline"
down_revision = "015_audio_history_and_lock_audit"
branch_labels = None
depends_on = None


def upgrade():
    # 1. Create assembly_timelines
    op.create_table(
        "assembly_timelines",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("project_id", sa.Uuid(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="DRAFT"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_assembly_timelines_project_id", "assembly_timelines", ["project_id"])
    op.create_index("ix_assembly_timelines_is_active", "assembly_timelines", ["is_active"])

    # 2. Create assembly_scenes
    op.create_table(
        "assembly_scenes",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("timeline_id", sa.Uuid(), sa.ForeignKey("assembly_timelines.id", ondelete="CASCADE"), nullable=False),
        sa.Column("scene_id", sa.Uuid(), sa.ForeignKey("scenes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("scene_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_assembly_scenes_timeline_id", "assembly_scenes", ["timeline_id"])
    op.create_index("ix_assembly_scenes_scene_id", "assembly_scenes", ["scene_id"])

    # 3. Create assembly_shot_placements
    op.create_table(
        "assembly_shot_placements",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("timeline_id", sa.Uuid(), sa.ForeignKey("assembly_timelines.id", ondelete="CASCADE"), nullable=False),
        sa.Column("assembly_scene_id", sa.Uuid(), sa.ForeignKey("assembly_scenes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("scene_id", sa.Uuid(), sa.ForeignKey("scenes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("shot_id", sa.Uuid(), sa.ForeignKey("shots.id", ondelete="CASCADE"), nullable=False),
        sa.Column("shot_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("visual_asset_id", sa.Uuid(), sa.ForeignKey("assets.id", ondelete="SET NULL"), nullable=True),
        sa.Column("source_type", sa.String(length=50), nullable=False, server_default="VIDEO"),
        sa.Column("trim_in", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("trim_out", sa.Float(), nullable=True),
        sa.Column("effective_duration", sa.Float(), nullable=False, server_default="4.0"),
        sa.Column("still_duration", sa.Float(), nullable=False, server_default="4.0"),
        sa.Column("transition_to_next", sa.String(length=50), nullable=False, server_default="CUT"),
        sa.Column("is_locked", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_assembly_shot_placements_timeline_id", "assembly_shot_placements", ["timeline_id"])
    op.create_index("ix_assembly_shot_placements_assembly_scene_id", "assembly_shot_placements", ["assembly_scene_id"])
    op.create_index("ix_assembly_shot_placements_scene_id", "assembly_shot_placements", ["scene_id"])
    op.create_index("ix_assembly_shot_placements_shot_id", "assembly_shot_placements", ["shot_id"])
    op.create_index("ix_assembly_shot_placements_visual_asset_id", "assembly_shot_placements", ["visual_asset_id"])

    # 4. Create timeline_checkpoints
    op.create_table(
        "timeline_checkpoints",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("project_id", sa.Uuid(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("timeline_id", sa.Uuid(), sa.ForeignKey("assembly_timelines.id", ondelete="CASCADE"), nullable=False),
        sa.Column("checkpoint_number", sa.Integer(), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=False),
        sa.Column("snapshot_data", sa.JSON(), nullable=False),
        sa.Column("actor", sa.String(length=100), nullable=False, server_default="system"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_timeline_checkpoints_project_id", "timeline_checkpoints", ["project_id"])
    op.create_index("ix_timeline_checkpoints_timeline_id", "timeline_checkpoints", ["timeline_id"])

    # 5. Create timeline_audits
    op.create_table(
        "timeline_audits",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("project_id", sa.Uuid(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("timeline_id", sa.Uuid(), sa.ForeignKey("assembly_timelines.id", ondelete="CASCADE"), nullable=False),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("actor", sa.String(length=100), nullable=False, server_default="system"),
        sa.Column("change_reason", sa.Text(), nullable=True),
        sa.Column("snapshot_data", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_timeline_audits_project_id", "timeline_audits", ["project_id"])
    op.create_index("ix_timeline_audits_timeline_id", "timeline_audits", ["timeline_id"])


def downgrade():
    op.drop_table("timeline_audits")
    op.drop_table("timeline_checkpoints")
    op.drop_table("assembly_shot_placements")
    op.drop_table("assembly_scenes")
    op.drop_table("assembly_timelines")
