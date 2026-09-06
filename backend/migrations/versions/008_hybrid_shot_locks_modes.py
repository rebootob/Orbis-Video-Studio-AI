"""Add hybrid shot fields, asset locks table, and base video modes.

Revision ID: 008_hybrid_shot_locks_modes
Revises: 007_queue_safety
Create Date: 2026-09-06
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "008_hybrid_shot_locks_modes"
down_revision = "007_queue_safety"
branch_labels = None
depends_on = None


def upgrade():
    # 1. Projects: add mode and config fields
    with op.batch_alter_table("projects") as batch_op:
        batch_op.add_column(
            sa.Column("video_mode", sa.String(length=50), nullable=False, server_default="STORY")
        )
        batch_op.add_column(sa.Column("purpose", sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column("target_platform", sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column("target_duration_seconds", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("preferred_aspect_ratio", sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column("mode_config", sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column("default_config", sa.JSON(), nullable=True))

    # 2. Scenes: make story_id nullable, add project_id and scene_config
    with op.batch_alter_table("scenes") as batch_op:
        batch_op.add_column(
            sa.Column(
                "project_id",
                sa.Uuid(),
                sa.ForeignKey("projects.id", ondelete="CASCADE", name="fk_scenes_project_id"),
                nullable=True,
            )
        )
        batch_op.add_column(sa.Column("scene_config", sa.JSON(), nullable=True))
        batch_op.alter_column("story_id", existing_type=sa.Uuid(), nullable=True)
        batch_op.create_index("ix_scenes_project_id", ["project_id"])

    # 3. Shots: add source_asset_id, source_metadata, provider_config
    with op.batch_alter_table("shots") as batch_op:
        batch_op.add_column(
            sa.Column(
                "source_asset_id",
                sa.Uuid(),
                sa.ForeignKey("assets.id", ondelete="SET NULL", name="fk_shots_source_asset_id"),
                nullable=True,
            )
        )
        batch_op.add_column(sa.Column("source_metadata", sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column("provider_config", sa.JSON(), nullable=True))
        batch_op.create_index("ix_shots_source_asset_id", ["source_asset_id"])

    # 4. Create asset_locks table
    op.create_table(
        "asset_locks",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "project_id",
            sa.Uuid(),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("entity_type", sa.String(length=50), nullable=False),
        sa.Column("entity_id", sa.Uuid(), nullable=False),
        sa.Column("is_locked", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("locked_by", sa.String(length=255), nullable=True),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("lock_reason", sa.Text(), nullable=True),
        sa.Column("unlocked_by", sa.String(length=255), nullable=True),
        sa.Column("unlocked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("unlock_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    with op.batch_alter_table("asset_locks") as batch_op:
        batch_op.create_index("ix_asset_locks_project_id", ["project_id"])
        batch_op.create_index("ix_asset_locks_entity_type", ["entity_type"])
        batch_op.create_index("ix_asset_locks_entity_id", ["entity_id"])
        batch_op.create_unique_constraint("uq_asset_locks_entity", ["entity_type", "entity_id"])

    # 5. Deterministic backfill: scenes.project_id from stories.project_id
    connection = op.get_bind()
    scenes = sa.table(
        "scenes",
        sa.column("id", sa.Uuid()),
        sa.column("story_id", sa.Uuid()),
        sa.column("project_id", sa.Uuid()),
    )
    stories = sa.table(
        "stories",
        sa.column("id", sa.Uuid()),
        sa.column("project_id", sa.Uuid()),
    )
    story_records = connection.execute(
        sa.select(stories.c.id, stories.c.project_id).where(stories.c.id.isnot(None))
    ).all()
    for s_id, p_id in story_records:
        connection.execute(
            scenes.update().where(scenes.c.story_id == s_id).values(project_id=p_id)
        )


def downgrade():
    connection = op.get_bind()
    scenes = sa.table(
        "scenes",
        sa.column("id", sa.Uuid()),
        sa.column("story_id", sa.Uuid()),
    )
    direct_scene_count = connection.execute(
        sa.select(sa.func.count(scenes.c.id)).where(scenes.c.story_id.is_(None))
    ).scalar()
    if direct_scene_count and direct_scene_count > 0:
        raise RuntimeError(
            f"Cannot downgrade migration 008: {direct_scene_count} direct Project->Scene row(s) exist with story_id=NULL. "
            "Downgrade to 007 requires scenes.story_id NOT NULL. Remove or attach direct scenes before downgrading."
        )

    op.drop_table("asset_locks")

    with op.batch_alter_table("shots") as batch_op:
        batch_op.drop_index("ix_shots_source_asset_id")
        batch_op.drop_column("provider_config")
        batch_op.drop_column("source_metadata")
        batch_op.drop_column("source_asset_id")

    with op.batch_alter_table("scenes") as batch_op:
        batch_op.drop_index("ix_scenes_project_id")
        batch_op.alter_column("story_id", existing_type=sa.Uuid(), nullable=False)
        batch_op.drop_column("scene_config")
        batch_op.drop_column("project_id")

    with op.batch_alter_table("projects") as batch_op:
        batch_op.drop_column("default_config")
        batch_op.drop_column("mode_config")
        batch_op.drop_column("preferred_aspect_ratio")
        batch_op.drop_column("target_duration_seconds")
        batch_op.drop_column("target_platform")
        batch_op.drop_column("purpose")
        batch_op.drop_column("video_mode")
