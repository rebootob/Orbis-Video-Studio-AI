"""Add job_type to generation_jobs and keyframe_asset_id to shots.

Revision ID: 013_image_keyframe_pipeline
Revises: 012_production_orchestrator_and_staged_approvals
Create Date: 2026-09-06
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "013_image_keyframe_pipeline"
down_revision = "012_production_orchestrator_and_staged_approvals"
branch_labels = None
depends_on = None


def upgrade():
    # 1. Add job_type to generation_jobs
    with op.batch_alter_table("generation_jobs") as batch_op:
        batch_op.add_column(
            sa.Column("job_type", sa.String(length=50), nullable=False, server_default="VIDEO")
        )
        batch_op.create_index("ix_generation_jobs_job_type", ["job_type"])

    # 2. Add keyframe_asset_id to shots
    with op.batch_alter_table("shots") as batch_op:
        batch_op.add_column(
            sa.Column(
                "keyframe_asset_id",
                sa.Uuid(),
                sa.ForeignKey("assets.id", ondelete="SET NULL", name="fk_shots_keyframe_asset_id"),
                nullable=True,
            )
        )
        batch_op.create_index("ix_shots_keyframe_asset_id", ["keyframe_asset_id"])


def downgrade():
    with op.batch_alter_table("shots") as batch_op:
        batch_op.drop_index("ix_shots_keyframe_asset_id")
        batch_op.drop_column("keyframe_asset_id")

    with op.batch_alter_table("generation_jobs") as batch_op:
        batch_op.drop_index("ix_generation_jobs_job_type")
        batch_op.drop_column("job_type")
