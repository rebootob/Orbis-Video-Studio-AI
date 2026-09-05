"""001_initial_domain_schema

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-09-05 16:40:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Projects
    op.create_table(
        'projects',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='DRAFT'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id')
    )

    # 2. Stories
    op.create_table(
        'stories',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('project_id', sa.UUID(), nullable=False),
        sa.Column('logline', sa.Text(), nullable=True),
        sa.Column('synopsis', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='DRAFT'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('project_id')
    )

    # 3. Scenes
    op.create_table(
        'scenes',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('story_id', sa.UUID(), nullable=False),
        sa.Column('scene_number', sa.Integer(), nullable=False),
        sa.Column('heading', sa.String(length=255), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_locked', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['story_id'], ['stories.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # 4. Shots
    op.create_table(
        'shots',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('scene_id', sa.UUID(), nullable=False),
        sa.Column('shot_number', sa.Integer(), nullable=False),
        sa.Column('shot_type', sa.String(length=50), nullable=False),
        sa.Column('visual_prompt', sa.Text(), nullable=True),
        sa.Column('duration_seconds', sa.Float(), nullable=False, server_default='4.0'),
        sa.Column('is_locked', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='PENDING'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['scene_id'], ['scenes.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # 5. Assets
    op.create_table(
        'assets',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('project_id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('asset_type', sa.String(length=50), nullable=False),
        sa.Column('storage_path', sa.String(length=512), nullable=True),
        sa.Column('media_url', sa.String(length=512), nullable=True),
        sa.Column('is_locked', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # 6. GenerationJobs
    op.create_table(
        'generation_jobs',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('shot_id', sa.UUID(), nullable=False),
        sa.Column('provider_name', sa.String(length=50), nullable=False),
        sa.Column('provider_job_id', sa.String(length=255), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='PENDING'),
        sa.Column('idempotency_key', sa.String(length=255), nullable=True),
        sa.Column('cost_usd', sa.Float(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['shot_id'], ['shots.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_generation_jobs_idempotency_key', 'generation_jobs', ['idempotency_key'])


def downgrade() -> None:
    op.drop_index('ix_generation_jobs_idempotency_key', table_name='generation_jobs')
    op.drop_table('generation_jobs')
    op.drop_table('assets')
    op.drop_table('shots')
    op.drop_table('scenes')
    op.drop_table('stories')
    op.drop_table('projects')
