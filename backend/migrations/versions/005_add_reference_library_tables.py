"""005_add_reference_library_tables

Revision ID: 005_ref_library
Revises: 004_story_script_fields
Create Date: 2026-09-05 18:40:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '005_ref_library'
down_revision: Union[str, None] = '004_story_script_fields'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Table project_references
    op.create_table(
        'project_references',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('project_id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('category', sa.String(length=50), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('reference_asset_id', sa.UUID(), nullable=True),
        sa.Column('is_locked', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('metadata_json', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['reference_asset_id'], ['assets.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )

    # 2. Table character_bibles
    op.create_table(
        'character_bibles',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('project_id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('role', sa.String(length=100), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('appearance', sa.Text(), nullable=True),
        sa.Column('wardrobe', sa.Text(), nullable=True),
        sa.Column('age_range', sa.String(length=50), nullable=True),
        sa.Column('gender_presentation', sa.String(length=50), nullable=True),
        sa.Column('nationality_cultural_context', sa.String(length=100), nullable=True),
        sa.Column('personality', sa.Text(), nullable=True),
        sa.Column('speaking_style', sa.Text(), nullable=True),
        sa.Column('continuity_notes', sa.Text(), nullable=True),
        sa.Column('reference_asset_id', sa.UUID(), nullable=True),
        sa.Column('is_locked', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['reference_asset_id'], ['assets.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )

    # 3. Table location_bibles
    op.create_table(
        'location_bibles',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('project_id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('environment', sa.String(length=255), nullable=True),
        sa.Column('visual_features', sa.Text(), nullable=True),
        sa.Column('lighting', sa.Text(), nullable=True),
        sa.Column('time_of_day_default', sa.String(length=50), nullable=True),
        sa.Column('continuity_notes', sa.Text(), nullable=True),
        sa.Column('reference_asset_id', sa.UUID(), nullable=True),
        sa.Column('is_locked', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['reference_asset_id'], ['assets.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )

    # 4. Table style_bibles
    op.create_table(
        'style_bibles',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('project_id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('visual_style', sa.Text(), nullable=True),
        sa.Column('camera_style', sa.Text(), nullable=True),
        sa.Column('color_direction', sa.Text(), nullable=True),
        sa.Column('lighting_style', sa.Text(), nullable=True),
        sa.Column('composition_rules', sa.Text(), nullable=True),
        sa.Column('realism_level', sa.String(length=50), nullable=True),
        sa.Column('negative_constraints', sa.Text(), nullable=True),
        sa.Column('reference_asset_id', sa.UUID(), nullable=True),
        sa.Column('is_locked', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['reference_asset_id'], ['assets.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )

    # 5. Table brand_bibles
    op.create_table(
        'brand_bibles',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('project_id', sa.UUID(), nullable=False),
        sa.Column('brand_name', sa.String(length=255), nullable=False),
        sa.Column('brand_colors', sa.Text(), nullable=True),
        sa.Column('typography_notes', sa.Text(), nullable=True),
        sa.Column('do_and_dont_rules', sa.Text(), nullable=True),
        sa.Column('tone', sa.String(length=100), nullable=True),
        sa.Column('mandatory_wording', sa.Text(), nullable=True),
        sa.Column('continuity_notes', sa.Text(), nullable=True),
        sa.Column('logo_asset_id', sa.UUID(), nullable=True),
        sa.Column('is_locked', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['logo_asset_id'], ['assets.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('brand_bibles')
    op.drop_table('style_bibles')
    op.drop_table('location_bibles')
    op.drop_table('character_bibles')
    op.drop_table('project_references')
