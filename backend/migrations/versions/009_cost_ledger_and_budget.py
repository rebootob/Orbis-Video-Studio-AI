"""Add project budget fields, usage ledger table, and ledger adjustments table.

Revision ID: 009_cost_ledger_and_budget
Revises: 008_hybrid_shot_locks_modes
Create Date: 2026-09-06
"""
from alembic import op
import sqlalchemy as sa


revision = "009_cost_ledger_and_budget"
down_revision = "008_hybrid_shot_locks_modes"
branch_labels = None
depends_on = None


def upgrade():
    # 1. Projects: add budget fields
    with op.batch_alter_table("projects") as batch_op:
        batch_op.add_column(sa.Column("budget_limit", sa.Float(), nullable=True))
        batch_op.add_column(
            sa.Column("budget_currency", sa.String(length=10), nullable=False, server_default="USD")
        )
        batch_op.add_column(
            sa.Column("budget_threshold_percentage", sa.Float(), nullable=True, server_default="80.0")
        )

    # 2. Create usage_ledger table
    op.create_table(
        "usage_ledger",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "project_id",
            sa.Uuid(),
            sa.ForeignKey("projects.id", ondelete="CASCADE", name="fk_usage_ledger_project_id"),
            nullable=False,
        ),
        sa.Column(
            "shot_id",
            sa.Uuid(),
            sa.ForeignKey("shots.id", ondelete="SET NULL", name="fk_usage_ledger_shot_id"),
            nullable=True,
        ),
        sa.Column(
            "job_id",
            sa.Uuid(),
            sa.ForeignKey("generation_jobs.id", ondelete="SET NULL", name="fk_usage_ledger_job_id"),
            nullable=True,
        ),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("operation", sa.String(length=50), nullable=False),
        sa.Column("model", sa.String(length=100), nullable=True),
        sa.Column("usage_units", sa.JSON(), nullable=True),
        sa.Column("estimated_cost", sa.Float(), nullable=True),
        sa.Column("actual_cost", sa.Float(), nullable=True),
        sa.Column("currency", sa.String(length=10), nullable=False, server_default="USD"),
        sa.Column("cost_status", sa.String(length=20), nullable=False, server_default="ESTIMATED"),
        sa.Column("provider_event_id", sa.String(length=255), nullable=True),
        sa.Column("idempotency_key", sa.String(length=255), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    with op.batch_alter_table("usage_ledger") as batch_op:
        batch_op.create_index("ix_usage_ledger_project_id", ["project_id"])
        batch_op.create_index("ix_usage_ledger_shot_id", ["shot_id"])
        batch_op.create_index("ix_usage_ledger_job_id", ["job_id"])
        batch_op.create_index("ix_usage_ledger_provider", ["provider"])
        batch_op.create_index("ix_usage_ledger_operation", ["operation"])
        batch_op.create_index("ix_usage_ledger_cost_status", ["cost_status"])
        batch_op.create_index("ix_usage_ledger_idempotency_key", ["idempotency_key"])

    # 3. Create ledger_adjustments table
    op.create_table(
        "ledger_adjustments",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "ledger_id",
            sa.Uuid(),
            sa.ForeignKey("usage_ledger.id", ondelete="CASCADE", name="fk_ledger_adjustments_ledger_id"),
            nullable=False,
        ),
        sa.Column("actor", sa.String(length=255), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("previous_cost", sa.Float(), nullable=True),
        sa.Column("adjusted_cost", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    with op.batch_alter_table("ledger_adjustments") as batch_op:
        batch_op.create_index("ix_ledger_adjustments_ledger_id", ["ledger_id"])


def downgrade():
    op.drop_table("ledger_adjustments")
    op.drop_table("usage_ledger")

    with op.batch_alter_table("projects") as batch_op:
        batch_op.drop_column("budget_threshold_percentage")
        batch_op.drop_column("budget_currency")
        batch_op.drop_column("budget_limit")
