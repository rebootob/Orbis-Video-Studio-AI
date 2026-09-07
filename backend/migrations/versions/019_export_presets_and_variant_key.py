"""Add render_batches table, render_variant_key column, and uq_render_jobs_active_variant index.

Revision ID: 019_export_presets_and_variant_key
Revises: 018_cloud_render_workers
Create Date: 2026-09-07
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text

revision = "019_export_presets_and_variant_key"
down_revision = "018_cloud_render_workers"
branch_labels = None
depends_on = None


def upgrade():
    # 1. Create render_batches table
    op.create_table(
        "render_batches",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("project_id", sa.Uuid(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("timeline_id", sa.Uuid(), sa.ForeignKey("assembly_timelines.id", ondelete="CASCADE"), nullable=False),
        sa.Column("timeline_version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="PROCESSING"),
        sa.Column("total_variants", sa.Integer(), nullable=False),
        sa.Column("completed_variants", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed_variants", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("estimated_total_cost_usd", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_render_batches_project_id", "render_batches", ["project_id"])
    op.create_index("ix_render_batches_timeline_id", "render_batches", ["timeline_id"])
    op.create_index("ix_render_batches_status", "render_batches", ["status"])

    # 2. Add columns to render_jobs table
    with op.batch_alter_table("render_jobs") as batch_op:
        batch_op.add_column(
            sa.Column("render_variant_key", sa.String(length=100), nullable=False, server_default="MASTER")
        )
        batch_op.add_column(
            sa.Column("batch_id", sa.Uuid(), sa.ForeignKey("render_batches.id", ondelete="SET NULL", name="fk_render_jobs_batch_id"), nullable=True)
        )
        batch_op.create_index("ix_render_jobs_render_variant_key", ["render_variant_key"])
        batch_op.create_index("ix_render_jobs_batch_id", ["batch_id"])

    # 3. Swap unique partial index on render_jobs
    op.drop_index("uq_render_jobs_active_timeline", table_name="render_jobs")
    op.create_index(
        "uq_render_jobs_active_variant",
        "render_jobs",
        ["project_id", "timeline_id", "render_variant_key"],
        unique=True,
        postgresql_where=sa.text("status IN ('QUEUED', 'CLAIMED', 'RUNNING', 'RECONCILIATION_REQUIRED')"),
        sqlite_where=sa.text("status IN ('QUEUED', 'CLAIMED', 'RUNNING', 'RECONCILIATION_REQUIRED')"),
    )


def downgrade():
    # Fail-closed downgrade contract check
    bind = op.get_bind()
    conflicts = bind.execute(text("""
        SELECT project_id, timeline_id, COUNT(*)
        FROM render_jobs
        WHERE status IN ('QUEUED', 'CLAIMED', 'RUNNING', 'RECONCILIATION_REQUIRED')
        GROUP BY project_id, timeline_id
        HAVING COUNT(*) > 1
    """)).fetchall()

    if conflicts:
        raise RuntimeError(
            f"Downgrade ABORTED: {len(conflicts)} timeline(s) have multiple active/reconciliation export variants. "
            "The WP017 schema permits at most ONE active render job per timeline. "
            "An operator must resolve active variant jobs before downgrade can proceed."
        )

    # Revert index swap if safe
    op.drop_index("uq_render_jobs_active_variant", table_name="render_jobs")
    op.drop_index("ix_render_jobs_batch_id", table_name="render_jobs")
    op.drop_index("ix_render_jobs_render_variant_key", table_name="render_jobs")
    op.create_index(
        "uq_render_jobs_active_timeline",
        "render_jobs",
        ["project_id", "timeline_id"],
        unique=True,
        postgresql_where=sa.text("status IN ('QUEUED', 'CLAIMED', 'RUNNING', 'RECONCILIATION_REQUIRED')"),
        sqlite_where=sa.text("status IN ('QUEUED', 'CLAIMED', 'RUNNING', 'RECONCILIATION_REQUIRED')"),
    )

    with op.batch_alter_table("render_jobs") as batch_op:
        batch_op.drop_column("batch_id")
        batch_op.drop_column("render_variant_key")

    op.drop_table("render_batches")
