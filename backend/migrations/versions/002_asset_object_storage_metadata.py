"""002_asset_object_storage_metadata

Revision ID: 002_asset_storage
Revises: 001_initial_schema
Create Date: 2026-09-05 17:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '002_asset_storage'
down_revision: Union[str, None] = '001_initial_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('assets', sa.Column('original_filename', sa.String(length=255), nullable=False, server_default=''))
    op.add_column('assets', sa.Column('content_type', sa.String(length=100), nullable=False, server_default='application/octet-stream'))
    op.add_column('assets', sa.Column('file_size_bytes', sa.BigInteger(), nullable=False, server_default='0'))
    op.add_column('assets', sa.Column('checksum_sha256', sa.String(length=64), nullable=False, server_default=''))
    op.add_column('assets', sa.Column('storage_bucket', sa.String(length=255), nullable=False, server_default='orbis-assets'))
    op.add_column('assets', sa.Column('storage_key', sa.String(length=512), nullable=False, server_default=''))
    op.drop_column('assets', 'storage_path')
    op.drop_column('assets', 'media_url')


def downgrade() -> None:
    op.add_column('assets', sa.Column('media_url', sa.String(length=512), nullable=True))
    op.add_column('assets', sa.Column('storage_path', sa.String(length=512), nullable=True))
    op.drop_column('assets', 'storage_key')
    op.drop_column('assets', 'storage_bucket')
    op.drop_column('assets', 'checksum_sha256')
    op.drop_column('assets', 'file_size_bytes')
    op.drop_column('assets', 'content_type')
    op.drop_column('assets', 'original_filename')
