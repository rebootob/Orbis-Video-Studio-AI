"""Add batch_runs and batch_run_items tables and performance indexes.

Revision ID: 011_batch_resume_runs_and_indexes
Revises: 010_story_version_history
Create Date: 2026-09-06
"""
from alembic import op
import sqlalchemy as sa


revision = "011_batch_resume_runs_and_indexes"
down_revision = "010_story_version_history"
branch_labels = None
depends_on = None


def upgrade():
    # 1. Create batch_runs table
    op.create_table(
        "batch_runs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "project_id",
            sa.Uuid(),
            sa.ForeignKey("projects.id", ondelete="CASCADE", name="fk_batch_runs_project_id"),
            nullable=False,
        ),
        sa.Column("operation_type", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="DISPATCHED"),
        sa.Column("requested_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("eligible_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("queued_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("skipped_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completed_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    with op.batch_alter_table("batch_runs") as batch_op:
        batch_op.create_index("ix_batch_runs_project_id", ["project_id"])
        batch_op.create_index("ix_batch_runs_operation_type", ["operation_type"])

    # 2. Create batch_run_items table
    op.create_table(
        "batch_run_items",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "batch_run_id",
            sa.Uuid(),
            sa.ForeignKey("batch_runs.id", ondelete="CASCADE", name="fk_batch_run_items_batch_run_id"),
            nullable=False,
        ),
        sa.Column(
            "shot_id",
            sa.Uuid(),
            nullable=False,
        ),
        sa.Column(
            "job_id",
            sa.Uuid(),
            sa.ForeignKey("generation_jobs.id", ondelete="SET NULL", name="fk_batch_run_items_job_id"),
            nullable=True,
        ),
        sa.Column("decision", sa.String(length=50), nullable=False),
        sa.Column("skip_reason", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("batch_run_id", "shot_id", name="uq_batch_run_items_run_shot"),
    )
    with op.batch_alter_table("batch_run_items") as batch_op:
        batch_op.create_index("ix_batch_run_items_batch_run_id", ["batch_run_id"])
        batch_op.create_index("ix_batch_run_items_shot_id", ["shot_id"])
        batch_op.create_index("ix_batch_run_items_job_id", ["job_id"])

    # 3. Targeted Performance & Scalability Indexes for candidate selection and active job deduplication
    with op.batch_alter_table("shots") as batch_op:
        batch_op.create_index("ix_shots_scene_id", ["scene_id"])

    with op.batch_alter_table("generation_jobs") as batch_op:
        batch_op.create_index("ix_generation_jobs_shot_status", ["shot_id", "status"])
        batch_op.create_index(
            "uq_generation_jobs_active_shot",
            ["shot_id"],
            unique=True,
            sqlite_where=sa.text("status IN ('PENDING', 'CLAIMED', 'SUBMITTING', 'SUBMITTED', 'POLLING', 'QUEUED', 'PROCESSING', 'CANCELLING', 'RECONCILIATION_REQUIRED')"),
            postgresql_where=sa.text("status IN ('PENDING', 'CLAIMED', 'SUBMITTING', 'SUBMITTED', 'POLLING', 'QUEUED', 'PROCESSING', 'CANCELLING', 'RECONCILIATION_REQUIRED')"),
        )


def downgrade():
    with op.batch_alter_table("generation_jobs") as batch_op:
        batch_op.drop_index("uq_generation_jobs_active_shot")
        batch_op.drop_index("ix_generation_jobs_shot_status")

    with op.batch_alter_table("shots") as batch_op:
        batch_op.drop_index("ix_shots_scene_id")

    op.drop_table("batch_run_items")
    op.drop_table("batch_runs")
