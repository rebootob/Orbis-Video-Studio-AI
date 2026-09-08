"""Add Core V1 timeline-bound subtitle state.

Revision ID: 021_core_v1_subtitles
Revises: 020_project_archive_lineage
Create Date: 2026-09-08
"""
from alembic import op
import sqlalchemy as sa

revision = "021_core_v1_subtitles"
down_revision = "020_project_archive_lineage"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("assembly_timelines") as batch_op:
        batch_op.add_column(sa.Column("subtitle_state", sa.JSON(), nullable=True))


def downgrade():
    with op.batch_alter_table("assembly_timelines") as batch_op:
        batch_op.drop_column("subtitle_state")
