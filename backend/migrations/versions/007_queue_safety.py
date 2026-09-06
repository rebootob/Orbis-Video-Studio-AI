"""Persist queue ownership, submission fencing and scheduling.

Legacy in-flight submissions without a provider identity are quarantined.
Downgrade is schema-only; it never requeues ambiguous work.
"""
import re
from alembic import op
import sqlalchemy as sa

revision = "007_queue_safety"
down_revision = "006_vidu_queue"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("generation_jobs") as batch:
        batch.add_column(sa.Column("poll_count", sa.Integer(), nullable=False, server_default="0"))
        batch.add_column(sa.Column("max_polls", sa.Integer(), nullable=False, server_default="60"))
        batch.add_column(sa.Column("claimed_by", sa.String(255), nullable=True))
        batch.add_column(sa.Column("claim_token", sa.String(64), nullable=True))
        batch.add_column(sa.Column("claim_expires_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("next_poll_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("submission_attempt_id", sa.String(255), nullable=True))
        for field in ("claimed_by", "next_retry_at", "next_poll_at"):
            batch.create_index("ix_generation_jobs_" + field, [field])
    jobs = sa.table("generation_jobs", sa.column("id", sa.Uuid()),
                    sa.column("status", sa.String()), sa.column("provider_job_id", sa.String()),
                    sa.column("payload", sa.JSON()), sa.column("result", sa.JSON()),
                    sa.column("error_message", sa.String()))
    connection = op.get_bind()
    sensitive = re.compile(r"api.?key|authorization|token|secret|password|credential", re.I)

    def unsafe(value):
        if isinstance(value, dict):
            return any(sensitive.search(str(k)) or unsafe(v) for k, v in value.items())
        if isinstance(value, list):
            return any(unsafe(v) for v in value)
        return isinstance(value, str) and bool(sensitive.search(value))

    for row in connection.execute(sa.select(jobs)).mappings().all():
        changes = {"result": None, "error_message": None}
        ambiguous = row["status"] in ("CLAIMED", "SUBMITTING", "PROCESSING", "QUEUED") and not row["provider_job_id"]
        if unsafe(row["payload"]):
            changes["payload"] = None
            ambiguous = ambiguous or row["status"] == "PENDING"
        if ambiguous:
            changes["status"] = "RECONCILIATION_REQUIRED"
        connection.execute(jobs.update().where(jobs.c.id == row["id"]).values(**changes))



def downgrade():
    with op.batch_alter_table("generation_jobs") as batch:
        for field in ("claimed_by", "next_retry_at", "next_poll_at"):
            batch.drop_index("ix_generation_jobs_" + field)
        for field in ("submission_attempt_id", "next_poll_at", "next_retry_at",
                      "claim_expires_at", "claim_token", "claimed_by", "max_polls", "poll_count"):
            batch.drop_column(field)
