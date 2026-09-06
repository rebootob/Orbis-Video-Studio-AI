"""Add automation_mode to projects and create orchestration_audits table with indexes.

Revision ID: 012_production_orchestrator_and_staged_approvals
Revises: 011_batch_resume_runs_and_indexes
Create Date: 2026-09-06
"""
from alembic import op
import sqlalchemy as sa


revision = "012_production_orchestrator_and_staged_approvals"
down_revision = "011_batch_resume_runs_and_indexes"
branch_labels = None
depends_on = None


def upgrade():
    # 1. Add automation_mode to projects
    with op.batch_alter_table("projects") as batch_op:
        batch_op.add_column(
            sa.Column("automation_mode", sa.String(length=50), nullable=False, server_default="MANUAL")
        )

    # 2. Create orchestration_audits table
    op.create_table(
        "orchestration_audits",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "project_id",
            sa.Uuid(),
            sa.ForeignKey("projects.id", ondelete="CASCADE", name="fk_orchestration_audits_project_id"),
            nullable=False,
        ),
        sa.Column("from_state", sa.String(length=50), nullable=False),
        sa.Column("to_state", sa.String(length=50), nullable=True),
        sa.Column("action", sa.String(length=50), nullable=False),
        sa.Column("actor", sa.String(length=100), nullable=False, server_default="SYSTEM"),
        sa.Column("result", sa.String(length=50), nullable=False, server_default="APPLIED"),
        sa.Column("reason_code", sa.String(length=100), nullable=True),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    with op.batch_alter_table("orchestration_audits") as batch_op:
        batch_op.create_index("ix_orchestration_audits_project_id", ["project_id"])
        batch_op.create_index("ix_orchestration_audits_created_at", ["created_at"])


def downgrade():
    with op.batch_alter_table("orchestration_audits") as batch_op:
        batch_op.drop_index("ix_orchestration_audits_created_at")
        batch_op.drop_index("ix_orchestration_audits_project_id")
    op.drop_table("orchestration_audits")

    with op.batch_alter_table("projects") as batch_op:
        batch_op.drop_column("automation_mode")
