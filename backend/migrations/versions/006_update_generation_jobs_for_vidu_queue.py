"""006_update_generation_jobs_for_vidu_queue

Revision ID: 006_vidu_queue
Revises: 005_ref_library
Create Date: 2026-09-06 07:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '006_vidu_queue'
down_revision: Union[str, None] = '005_ref_library'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('generation_jobs') as batch_op:
        batch_op.add_column(sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'))
        batch_op.add_column(sa.Column('max_retries', sa.Integer(), nullable=False, server_default='3'))
        batch_op.add_column(sa.Column('payload', sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column('result', sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column('output_asset_id', sa.UUID(), nullable=True))
        batch_op.create_foreign_key(
            'fk_generation_jobs_output_asset_id',
            'assets',
            ['output_asset_id'],
            ['id'],
            ondelete='SET NULL'
        )
        batch_op.create_index('ix_generation_jobs_status', ['status'])
        batch_op.create_unique_constraint(
            'uq_generation_jobs_shot_idempotency_key',
            ['shot_id', 'idempotency_key']
        )


def downgrade() -> None:
    with op.batch_alter_table('generation_jobs') as batch_op:
        batch_op.drop_constraint('uq_generation_jobs_shot_idempotency_key', type_='unique')
        batch_op.drop_index('ix_generation_jobs_status')
        batch_op.drop_constraint('fk_generation_jobs_output_asset_id', type_='foreignkey')
        batch_op.drop_column('output_asset_id')
        batch_op.drop_column('result')
        batch_op.drop_column('payload')
        batch_op.drop_column('max_retries')
        batch_op.drop_column('retry_count')
