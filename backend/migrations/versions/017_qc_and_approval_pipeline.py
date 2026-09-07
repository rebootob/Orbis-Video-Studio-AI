"""Add qc_runs, qc_findings, qc_warning_decisions, and production_approvals tables.

Revision ID: 017_qc_and_approval_pipeline
Revises: 016_simplified_assembly_timeline
Create Date: 2026-09-07
"""
from alembic import op
import sqlalchemy as sa

revision = "017_qc_and_approval_pipeline"
down_revision = "016_simplified_assembly_timeline"
branch_labels = None
depends_on = None


def upgrade():
    # 1. Create qc_runs
    op.create_table(
        "qc_runs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("project_id", sa.Uuid(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("timeline_id", sa.Uuid(), sa.ForeignKey("assembly_timelines.id", ondelete="CASCADE"), nullable=False),
        sa.Column("timeline_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="PENDING"),
        sa.Column("blocker_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("warning_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("actor", sa.String(length=100), nullable=False, server_default="system"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_qc_runs_project_id", "qc_runs", ["project_id"])
    op.create_index("ix_qc_runs_timeline_id", "qc_runs", ["timeline_id"])
    op.create_index("ix_qc_runs_status", "qc_runs", ["status"])

    # 2. Create qc_findings
    op.create_table(
        "qc_findings",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("project_id", sa.Uuid(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("qc_run_id", sa.Uuid(), sa.ForeignKey("qc_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("timeline_id", sa.Uuid(), sa.ForeignKey("assembly_timelines.id", ondelete="CASCADE"), nullable=False),
        sa.Column("rule_code", sa.String(length=100), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("why_it_matters", sa.Text(), nullable=True),
        sa.Column("recommended_fix", sa.Text(), nullable=True),
        sa.Column("target_type", sa.String(length=50), nullable=True),
        sa.Column("target_id", sa.Uuid(), nullable=True),
        sa.Column("target_label", sa.String(length=255), nullable=True),
        sa.Column("action_type", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_qc_findings_project_id", "qc_findings", ["project_id"])
    op.create_index("ix_qc_findings_qc_run_id", "qc_findings", ["qc_run_id"])
    op.create_index("ix_qc_findings_timeline_id", "qc_findings", ["timeline_id"])
    op.create_index("ix_qc_findings_rule_code", "qc_findings", ["rule_code"])
    op.create_index("ix_qc_findings_severity", "qc_findings", ["severity"])
    op.create_index("ix_qc_findings_target_id", "qc_findings", ["target_id"])

    # 3. Create qc_warning_decisions (append-only decision audit event history)
    op.create_table(
        "qc_warning_decisions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("project_id", sa.Uuid(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("qc_run_id", sa.Uuid(), sa.ForeignKey("qc_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("finding_id", sa.Uuid(), sa.ForeignKey("qc_findings.id", ondelete="CASCADE"), nullable=False),
        sa.Column("timeline_id", sa.Uuid(), sa.ForeignKey("assembly_timelines.id", ondelete="CASCADE"), nullable=False),
        sa.Column("decision", sa.String(length=50), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("actor", sa.String(length=100), nullable=False, server_default="USER"),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_qc_warning_decisions_project_id", "qc_warning_decisions", ["project_id"])
    op.create_index("ix_qc_warning_decisions_qc_run_id", "qc_warning_decisions", ["qc_run_id"])
    op.create_index("ix_qc_warning_decisions_finding_id", "qc_warning_decisions", ["finding_id"])
    op.create_index("ix_qc_warning_decisions_timeline_id", "qc_warning_decisions", ["timeline_id"])

    # 4. Create production_approvals (with uniqueness constraint on project + timeline + qc_run)
    op.create_table(
        "production_approvals",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("project_id", sa.Uuid(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("timeline_id", sa.Uuid(), sa.ForeignKey("assembly_timelines.id", ondelete="CASCADE"), nullable=False),
        sa.Column("timeline_version", sa.Integer(), nullable=False),
        sa.Column("qc_run_id", sa.Uuid(), sa.ForeignKey("qc_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="APPROVED"),
        sa.Column("actor", sa.String(length=100), nullable=False, server_default="USER"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("project_id", "timeline_id", "qc_run_id", name="uq_production_approvals_project_timeline_qc"),
    )
    op.create_index("ix_production_approvals_project_id", "production_approvals", ["project_id"])
    op.create_index("ix_production_approvals_timeline_id", "production_approvals", ["timeline_id"])
    op.create_index("ix_production_approvals_qc_run_id", "production_approvals", ["qc_run_id"])


def downgrade():
    op.drop_table("production_approvals")
    op.drop_table("qc_warning_decisions")
    op.drop_table("qc_findings")
    op.drop_table("qc_runs")
