"""Add nutrition_targets and nutrition_plans tables

Revision ID: 52dfbd53f4e9
Revises: a268693746f1
Create Date: 2025-12-06 09:46:16.425379
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = '52dfbd53f4e9'
down_revision = 'a268693746f1'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Check if tables exist before creating them (idempotent migration)
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_tables = inspector.get_table_names()
    
    if 'nutrition_targets' not in existing_tables:
        op.create_table('nutrition_targets',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('daily_calories', sa.Float(), nullable=True),
            sa.Column('daily_carbs_grams', sa.Float(), nullable=True),
            sa.Column('daily_protein_grams', sa.Float(), nullable=True),
            sa.Column('daily_fat_grams', sa.Float(), nullable=True),
            sa.Column('activity_level', sa.String(), nullable=True),
            sa.Column('training_days_per_week', sa.Integer(), nullable=True),
            sa.Column('goal_type', sa.String(), nullable=True),
            sa.Column('target_weight_kg', sa.Float(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_nutrition_targets_user_id'), 'nutrition_targets', ['user_id'], unique=False)
    
    if 'nutrition_plans' not in existing_tables:
        op.create_table('nutrition_plans',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('plan_type', sa.String(), nullable=False),
            sa.Column('race_type', sa.String(), nullable=True),
            sa.Column('race_duration_hours', sa.Float(), nullable=True),
            sa.Column('pre_race_meals', sa.JSON(), nullable=True),
            sa.Column('during_race_fueling', sa.JSON(), nullable=True),
            sa.Column('recovery_nutrition', sa.JSON(), nullable=True),
            sa.Column('daily_meals', sa.JSON(), nullable=True),
            sa.Column('notes', sa.Text(), nullable=True),
            sa.Column('recommendations', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_nutrition_plans_user_id'), 'nutrition_plans', ['user_id'], unique=False)
        op.create_index(op.f('ix_nutrition_plans_plan_type'), 'nutrition_plans', ['plan_type'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_nutrition_plans_plan_type'), table_name='nutrition_plans')
    op.drop_index(op.f('ix_nutrition_plans_user_id'), table_name='nutrition_plans')
    op.drop_table('nutrition_plans')
    op.drop_index(op.f('ix_nutrition_targets_user_id'), table_name='nutrition_targets')
    op.drop_table('nutrition_targets')
