"""Add project archive lineage, imported_historical flags, and update active partial unique indexes.

Revision ID: 020_project_archive_lineage
Revises: 019_export_presets_and_variant_key
Create Date: 2026-09-07
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text

revision = "020_project_archive_lineage"
down_revision = "019_export_presets_and_variant_key"
branch_labels = None
depends_on = None


def upgrade():
    # 1. Projects table lineage fields
    with op.batch_alter_table("projects") as batch_op:
        batch_op.add_column(sa.Column("source_project_id", sa.Uuid(), nullable=True))
        batch_op.add_column(sa.Column("source_archive_checksum", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("imported_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.create_index("ix_projects_source_project_id", ["source_project_id"])
        batch_op.create_index("ix_projects_source_archive_checksum", ["source_archive_checksum"])

    # 2. Render jobs table lineage and active index swap
    with op.batch_alter_table("render_jobs") as batch_op:
        batch_op.add_column(
            sa.Column("imported_historical", sa.Boolean(), nullable=False, server_default=sa.text("false"))
        )
        batch_op.add_column(
            sa.Column("execution_disabled", sa.Boolean(), nullable=False, server_default=sa.text("false"))
        )
        batch_op.create_index("ix_render_jobs_imported_historical", ["imported_historical"])

    op.drop_index("uq_render_jobs_active_variant", table_name="render_jobs")
    op.create_index(
        "uq_render_jobs_active_variant",
        "render_jobs",
        ["project_id", "timeline_id", "render_variant_key"],
        unique=True,
        postgresql_where=sa.text("status IN ('QUEUED', 'CLAIMED', 'RUNNING', 'RECONCILIATION_REQUIRED') AND imported_historical IS NOT TRUE"),
        sqlite_where=sa.text("status IN ('QUEUED', 'CLAIMED', 'RUNNING', 'RECONCILIATION_REQUIRED') AND imported_historical IS NOT TRUE"),
    )

    # 3. Generation jobs table lineage and active index swap
    with op.batch_alter_table("generation_jobs") as batch_op:
        batch_op.add_column(
            sa.Column("imported_historical", sa.Boolean(), nullable=False, server_default=sa.text("false"))
        )
        batch_op.add_column(
            sa.Column("execution_disabled", sa.Boolean(), nullable=False, server_default=sa.text("false"))
        )
        batch_op.create_index("ix_generation_jobs_imported_historical", ["imported_historical"])

    op.drop_index("uq_generation_jobs_active_shot", table_name="generation_jobs")
    op.create_index(
        "uq_generation_jobs_active_shot",
        "generation_jobs",
        ["shot_id"],
        unique=True,
        postgresql_where=sa.text("status IN ('PENDING', 'CLAIMED', 'SUBMITTING', 'SUBMITTED', 'POLLING', 'QUEUED', 'PROCESSING', 'CANCELLING', 'RECONCILIATION_REQUIRED') AND imported_historical IS NOT TRUE"),
        sqlite_where=sa.text("status IN ('PENDING', 'CLAIMED', 'SUBMITTING', 'SUBMITTED', 'POLLING', 'QUEUED', 'PROCESSING', 'CANCELLING', 'RECONCILIATION_REQUIRED') AND imported_historical IS NOT TRUE"),
    )

    # 4. Usage ledger table lineage and provider event index swap
    with op.batch_alter_table("usage_ledger") as batch_op:
        batch_op.add_column(
            sa.Column("imported_historical", sa.Boolean(), nullable=False, server_default=sa.text("false"))
        )
        batch_op.create_index("ix_usage_ledger_imported_historical", ["imported_historical"])

    op.drop_index("uq_usage_ledger_provider_event", table_name="usage_ledger")
    op.create_index(
        "uq_usage_ledger_provider_event",
        "usage_ledger",
        ["provider", "provider_event_id"],
        unique=True,
        postgresql_where=sa.text("provider_event_id IS NOT NULL AND imported_historical IS NOT TRUE"),
        sqlite_where=sa.text("provider_event_id IS NOT NULL AND imported_historical IS NOT TRUE"),
    )


def downgrade():
    bind = op.get_bind()

    # Fail-closed check: render_jobs
    render_conflicts = bind.execute(text("""
        SELECT project_id, timeline_id, render_variant_key, COUNT(*)
        FROM render_jobs
        WHERE status IN ('QUEUED', 'CLAIMED', 'RUNNING', 'RECONCILIATION_REQUIRED')
        GROUP BY project_id, timeline_id, render_variant_key
        HAVING COUNT(*) > 1
    """)).fetchall()

    if render_conflicts:
        raise RuntimeError(
            f"Downgrade ABORTED: {len(render_conflicts)} variant(s) have multiple active-status render jobs. "
            "Recreating the pre-020 unique index would cause uniqueness collisions. "
            "Downgrade aborted to prevent silent history loss."
        )

    # Fail-closed check: generation_jobs
    gen_conflicts = bind.execute(text("""
        SELECT shot_id, COUNT(*)
        FROM generation_jobs
        WHERE status IN ('PENDING', 'CLAIMED', 'SUBMITTING', 'SUBMITTED', 'POLLING', 'QUEUED', 'PROCESSING', 'CANCELLING', 'RECONCILIATION_REQUIRED')
        GROUP BY shot_id
        HAVING COUNT(*) > 1
    """)).fetchall()

    if gen_conflicts:
        raise RuntimeError(
            f"Downgrade ABORTED: {len(gen_conflicts)} shot(s) have multiple active-status generation jobs. "
            "Recreating the pre-020 unique index would cause uniqueness collisions. "
            "Downgrade aborted to prevent silent history loss."
        )

    # Revert generation_jobs index and columns
    op.drop_index("uq_generation_jobs_active_shot", table_name="generation_jobs")
    op.create_index(
        "uq_generation_jobs_active_shot",
        "generation_jobs",
        ["shot_id"],
        unique=True,
        postgresql_where=sa.text("status IN ('PENDING', 'CLAIMED', 'SUBMITTING', 'SUBMITTED', 'POLLING', 'QUEUED', 'PROCESSING', 'CANCELLING', 'RECONCILIATION_REQUIRED')"),
        sqlite_where=sa.text("status IN ('PENDING', 'CLAIMED', 'SUBMITTING', 'SUBMITTED', 'POLLING', 'QUEUED', 'PROCESSING', 'CANCELLING', 'RECONCILIATION_REQUIRED')"),
    )
    with op.batch_alter_table("generation_jobs") as batch_op:
        batch_op.drop_index("ix_generation_jobs_imported_historical")
        batch_op.drop_column("execution_disabled")
        batch_op.drop_column("imported_historical")

    # Revert render_jobs index and columns
    op.drop_index("uq_render_jobs_active_variant", table_name="render_jobs")
    op.create_index(
        "uq_render_jobs_active_variant",
        "render_jobs",
        ["project_id", "timeline_id", "render_variant_key"],
        unique=True,
        postgresql_where=sa.text("status IN ('QUEUED', 'CLAIMED', 'RUNNING', 'RECONCILIATION_REQUIRED')"),
        sqlite_where=sa.text("status IN ('QUEUED', 'CLAIMED', 'RUNNING', 'RECONCILIATION_REQUIRED')"),
    )
    with op.batch_alter_table("render_jobs") as batch_op:
        batch_op.drop_index("ix_render_jobs_imported_historical")
        batch_op.drop_column("execution_disabled")
        batch_op.drop_column("imported_historical")

    # Revert usage_ledger index and columns
    op.drop_index("uq_usage_ledger_provider_event", table_name="usage_ledger")
    op.create_index(
        "uq_usage_ledger_provider_event",
        "usage_ledger",
        ["provider", "provider_event_id"],
        unique=True,
        postgresql_where=sa.text("provider_event_id IS NOT NULL"),
        sqlite_where=sa.text("provider_event_id IS NOT NULL"),
    )
    with op.batch_alter_table("usage_ledger") as batch_op:
        batch_op.drop_index("ix_usage_ledger_imported_historical")
        batch_op.drop_column("imported_historical")

    # Revert projects
    with op.batch_alter_table("projects") as batch_op:
        batch_op.drop_index("ix_projects_source_archive_checksum")
        batch_op.drop_index("ix_projects_source_project_id")
        batch_op.drop_column("imported_at")
        batch_op.drop_column("source_archive_checksum")
        batch_op.drop_column("source_project_id")
