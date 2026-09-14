"""Add provider_execution_fences and recovery_failure_audits tables.

Revision ID: 022_provider_execution_fences_and_audits
Revises: 021_core_v1_subtitles
Create Date: 2026-09-14
"""
from alembic import op
import sqlalchemy as sa


revision = "022_provider_execution_fences_and_audits"
down_revision = "021_core_v1_subtitles"
branch_labels = None
depends_on = None


def upgrade():
    # 1. Create provider_execution_fences table
    op.create_table(
        "provider_execution_fences",
        sa.Column("fence_id", sa.Uuid(), primary_key=True),
        sa.Column("provider_name", sa.String(length=64), nullable=False, server_default="vidu"),
        sa.Column("provider_job_id", sa.String(length=128), nullable=False),
        sa.Column("execution_id", sa.String(length=128), nullable=False),
        sa.Column("task_id", sa.String(length=128), nullable=False),
        sa.Column("authorized_commit_sha", sa.String(length=64), nullable=False),
        sa.Column("runtime_target", sa.String(length=64), nullable=False),
        sa.Column("owner_evidence_anchor", sa.String(length=256), nullable=False),
        sa.Column("auth_digest", sa.String(length=64), nullable=False),
        sa.Column("auth_nonce", sa.String(length=64), nullable=False),
        sa.Column("auth_issued_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("network_get_attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("storage_intent_bucket", sa.String(length=64), nullable=True),
        sa.Column("storage_intent_key", sa.String(length=512), nullable=True),
        sa.Column("storage_intent_sha256", sa.String(length=64), nullable=True),
        sa.Column("storage_intent_bytes", sa.BigInteger(), nullable=True),
        sa.Column("storage_is_new_object", sa.String(length=16), nullable=False, server_default="UNKNOWN"),
        sa.Column("target_asset_id", sa.Uuid(), nullable=True),
        sa.Column("target_job_id", sa.Uuid(), nullable=True),
        sa.Column("target_project_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("provider_name", "provider_job_id", name="uq_provider_job_fence"),
        sa.UniqueConstraint("auth_nonce", name="uq_auth_nonce"),
        sa.CheckConstraint("network_get_attempts <= 1", name="chk_network_get_attempts"),
    )
    op.create_index("ix_provider_execution_fences_provider_job_id", "provider_execution_fences", ["provider_job_id"])
    op.create_index("ix_provider_execution_fences_status", "provider_execution_fences", ["status"])
    op.create_index("ix_provider_execution_fences_execution_id", "provider_execution_fences", ["execution_id"])

    # 2. Create recovery_failure_audits table
    op.create_table(
        "recovery_failure_audits",
        sa.Column("audit_id", sa.Uuid(), primary_key=True),
        sa.Column("fence_id", sa.Uuid(), sa.ForeignKey("provider_execution_fences.fence_id", ondelete="SET NULL"), nullable=True),
        sa.Column("provider_job_id", sa.String(length=128), nullable=False),
        sa.Column("failure_stage", sa.String(length=64), nullable=False),
        sa.Column("error_class", sa.String(length=128), nullable=False),
        sa.Column("error_message", sa.String(length=512), nullable=False),
        sa.Column("orphan_storage_bucket", sa.String(length=64), nullable=True),
        sa.Column("orphan_storage_key", sa.String(length=512), nullable=True),
        sa.Column("db_transaction_state", sa.String(length=64), nullable=False),
        sa.Column("compensation_status", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_recovery_failure_audits_fence_id", "recovery_failure_audits", ["fence_id"])
    op.create_index("ix_recovery_failure_audits_provider_job_id", "recovery_failure_audits", ["provider_job_id"])
    op.create_index("ix_recovery_failure_audits_failure_stage", "recovery_failure_audits", ["failure_stage"])


def downgrade():
    op.drop_table("recovery_failure_audits")
    op.drop_table("provider_execution_fences")
