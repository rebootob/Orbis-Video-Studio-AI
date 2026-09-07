"""Add render_jobs table and render_job_id column to usage_ledger.

Revision ID: 018_cloud_render_workers
Revises: 017_qc_and_approval_pipeline
Create Date: 2026-09-07
"""
from alembic import op
import sqlalchemy as sa

revision = "018_cloud_render_workers"
down_revision = "017_qc_and_approval_pipeline"
branch_labels = None
depends_on = None


def upgrade():
    # 1. Create render_jobs table
    op.create_table(
        "render_jobs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("project_id", sa.Uuid(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("timeline_id", sa.Uuid(), sa.ForeignKey("assembly_timelines.id", ondelete="CASCADE"), nullable=False),
        sa.Column("timeline_version", sa.Integer(), nullable=False),
        sa.Column("approval_id", sa.Uuid(), sa.ForeignKey("production_approvals.id", ondelete="CASCADE"), nullable=False),
        sa.Column("render_profile", sa.String(length=50), nullable=False, server_default="MASTER_HD"),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="QUEUED"),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.Column("output_asset_id", sa.Uuid(), sa.ForeignKey("assets.id", ondelete="SET NULL"), nullable=True),
        sa.Column("progress", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("claimed_by", sa.String(length=255), nullable=True),
        sa.Column("claim_token", sa.String(length=64), nullable=True),
        sa.Column("claim_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_retries", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("estimated_cost_usd", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("actual_cost_usd", sa.Float(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("current_usage_ledger_id", sa.Uuid(), sa.ForeignKey("usage_ledger.id", ondelete="SET NULL", name="fk_render_jobs_current_usage_ledger_id", use_alter=True), nullable=True),
        sa.Column("render_metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_render_jobs_project_id", "render_jobs", ["project_id"])
    op.create_index("ix_render_jobs_timeline_id", "render_jobs", ["timeline_id"])
    op.create_index("ix_render_jobs_status", "render_jobs", ["status"])
    op.create_index("ix_render_jobs_idempotency_key", "render_jobs", ["idempotency_key"])
    op.create_index("ix_render_jobs_claimed_by", "render_jobs", ["claimed_by"])
    op.create_index("ix_render_jobs_current_usage_ledger_id", "render_jobs", ["current_usage_ledger_id"])

    # Partial index for active timeline render job
    op.create_index(
        "uq_render_jobs_active_timeline",
        "render_jobs",
        ["project_id", "timeline_id"],
        unique=True,
        postgresql_where=sa.text("status IN ('QUEUED', 'CLAIMED', 'RUNNING', 'RECONCILIATION_REQUIRED')"),
        sqlite_where=sa.text("status IN ('QUEUED', 'CLAIMED', 'RUNNING', 'RECONCILIATION_REQUIRED')"),
    )

    # 2. Add render_job_id column to usage_ledger
    with op.batch_alter_table("usage_ledger") as batch_op:
        batch_op.add_column(
            sa.Column(
                "render_job_id",
                sa.Uuid(),
                sa.ForeignKey("render_jobs.id", ondelete="SET NULL", name="fk_usage_ledger_render_job_id"),
                nullable=True,
            )
        )
        batch_op.create_index("ix_usage_ledger_render_job_id", ["render_job_id"])


def downgrade():
    with op.batch_alter_table("usage_ledger") as batch_op:
        batch_op.drop_index("ix_usage_ledger_render_job_id")
        batch_op.drop_column("render_job_id")

    op.drop_table("render_jobs")
