"""004_add_story_script_fields

Revision ID: 004_story_script_fields
Revises: 003_doc_extraction
Create Date: 2026-09-05 17:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '004_story_script_fields'
down_revision: Union[str, None] = '003_doc_extraction'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Extend stories table
    op.add_column('stories', sa.Column('title', sa.String(length=255), nullable=True))
    op.add_column('stories', sa.Column('tone', sa.String(length=100), nullable=True))
    op.add_column('stories', sa.Column('target_duration_seconds', sa.Float(), nullable=True))
    op.add_column('stories', sa.Column('language', sa.String(length=50), nullable=True))
    op.add_column('stories', sa.Column('is_locked', sa.Boolean(), nullable=False, server_default=sa.text('false')))

    # 2. Extend scenes table
    op.add_column('scenes', sa.Column('purpose', sa.Text(), nullable=True))
    op.add_column('scenes', sa.Column('setting', sa.String(length=255), nullable=True))
    op.add_column('scenes', sa.Column('duration_seconds', sa.Float(), nullable=True))
    op.add_column('scenes', sa.Column('narration', sa.Text(), nullable=True))
    op.add_column('scenes', sa.Column('dialogue', sa.JSON(), nullable=True))

    # 3. Extend shots table
    op.add_column('shots', sa.Column('image_prompt', sa.Text(), nullable=True))
    op.add_column('shots', sa.Column('video_prompt', sa.Text(), nullable=True))
    op.add_column('shots', sa.Column('camera', sa.String(length=255), nullable=True))
    op.add_column('shots', sa.Column('subject', sa.Text(), nullable=True))
    op.add_column('shots', sa.Column('action', sa.Text(), nullable=True))

    # 4. Create generation_audit_logs table
    op.create_table(
        'generation_audit_logs',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('project_id', sa.UUID(), nullable=False),
        sa.Column('provider', sa.String(length=50), nullable=False),
        sa.Column('model', sa.String(length=100), nullable=False),
        sa.Column('request_type', sa.String(length=50), nullable=False),
        sa.Column('input_character_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('output_character_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('prompt_tokens', sa.Integer(), nullable=True),
        sa.Column('completion_tokens', sa.Integer(), nullable=True),
        sa.Column('duration_ms', sa.Float(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('generation_audit_logs')

    op.drop_column('shots', 'action')
    op.drop_column('shots', 'subject')
    op.drop_column('shots', 'camera')
    op.drop_column('shots', 'video_prompt')
    op.drop_column('shots', 'image_prompt')

    op.drop_column('scenes', 'dialogue')
    op.drop_column('scenes', 'narration')
    op.drop_column('scenes', 'duration_seconds')
    op.drop_column('scenes', 'setting')
    op.drop_column('scenes', 'purpose')

    op.drop_column('stories', 'is_locked')
    op.drop_column('stories', 'language')
    op.drop_column('stories', 'target_duration_seconds')
    op.drop_column('stories', 'tone')
    op.drop_column('stories', 'title')
