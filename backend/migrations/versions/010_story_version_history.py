"""Add story version history table and stories version_number column.

Revision ID: 010_story_version_history
Revises: 009_cost_ledger_and_budget
Create Date: 2026-09-06
"""
from alembic import op
import sqlalchemy as sa


revision = "010_story_version_history"
down_revision = "009_cost_ledger_and_budget"
branch_labels = None
depends_on = None


def upgrade():
    # 1. Add version_number to stories table
    with op.batch_alter_table("stories") as batch_op:
        batch_op.add_column(
            sa.Column("version_number", sa.Integer(), nullable=False, server_default="1")
        )

    # 2. Create story_versions table
    op.create_table(
        "story_versions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "story_id",
            sa.Uuid(),
            sa.ForeignKey("stories.id", ondelete="CASCADE", name="fk_story_versions_story_id"),
            nullable=False,
        ),
        sa.Column(
            "project_id",
            sa.Uuid(),
            sa.ForeignKey("projects.id", ondelete="CASCADE", name="fk_story_versions_project_id"),
            nullable=False,
        ),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("logline", sa.Text(), nullable=True),
        sa.Column("synopsis", sa.Text(), nullable=True),
        sa.Column("tone", sa.String(length=100), nullable=True),
        sa.Column("target_duration_seconds", sa.Float(), nullable=True),
        sa.Column("language", sa.String(length=50), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="SUPERSEDED"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    with op.batch_alter_table("story_versions") as batch_op:
        batch_op.create_index("ix_story_versions_story_id", ["story_id"])
        batch_op.create_index("ix_story_versions_project_id", ["project_id"])


def downgrade():
    op.drop_table("story_versions")

    with op.batch_alter_table("stories") as batch_op:
        batch_op.drop_column("version_number")
