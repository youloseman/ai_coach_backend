"""Initial schema

Revision ID: 001
Revises: 
Create Date: 2024-12-07 17:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create users table
    op.create_table('users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('username', sa.String(), nullable=False),
        sa.Column('hashed_password', sa.String(), nullable=False),
        sa.Column('full_name', sa.String(), nullable=True),
        sa.Column('strava_athlete_id', sa.String(), nullable=True),
        sa.Column('strava_access_token', sa.String(), nullable=True),
        sa.Column('strava_refresh_token', sa.String(), nullable=True),
        sa.Column('strava_token_expires_at', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.Column('is_verified', sa.Boolean(), nullable=True, default=False),
        sa.Column('email_verified_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('last_login_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)
    op.create_index(op.f('ix_users_strava_athlete_id'), 'users', ['strava_athlete_id'], unique=True)
    
    # Create athlete_profiles table
    op.create_table('athlete_profiles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('age', sa.Integer(), nullable=True),
        sa.Column('gender', sa.String(), nullable=True),
        sa.Column('weight_kg', sa.Float(), nullable=True),
        sa.Column('height_cm', sa.Float(), nullable=True),
        sa.Column('years_of_experience', sa.Integer(), nullable=True, default=0),
        sa.Column('primary_discipline', sa.String(), nullable=True),
        sa.Column('training_zones_run', sa.JSON(), nullable=True),
        sa.Column('training_zones_bike', sa.JSON(), nullable=True),
        sa.Column('training_zones_swim', sa.JSON(), nullable=True),
        sa.Column('zones_last_updated', sa.Date(), nullable=True),
        sa.Column('auto_weeks_analyzed', sa.Integer(), nullable=True, default=0),
        sa.Column('auto_current_weekly_streak_weeks', sa.Integer(), nullable=True, default=0),
        sa.Column('auto_longest_weekly_streak_weeks', sa.Integer(), nullable=True, default=0),
        sa.Column('auto_avg_hours_last_12_weeks', sa.Float(), nullable=True, default=0.0),
        sa.Column('auto_avg_hours_last_52_weeks', sa.Float(), nullable=True, default=0.0),
        sa.Column('auto_discipline_hours_per_week', sa.JSON(), nullable=True),
        sa.Column('preferred_training_days', sa.JSON(), nullable=True),
        sa.Column('available_hours_per_week', sa.Float(), nullable=True, default=8.0),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id')
    )
    
    # Create goals table
    op.create_table('goals',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('goal_type', sa.String(), nullable=False),
        sa.Column('target_time', sa.String(), nullable=True),
        sa.Column('target_date', sa.Date(), nullable=True),
        sa.Column('priority', sa.Integer(), nullable=True, default=1),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create weekly_plans table
    op.create_table('weekly_plans',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('week_start_date', sa.Date(), nullable=False),
        sa.Column('week_end_date', sa.Date(), nullable=False),
        sa.Column('plan_json', sa.JSON(), nullable=False),
        sa.Column('ai_recommendations', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_weekly_plans_user_id'), 'weekly_plans', ['user_id'], unique=False)
    op.create_index(op.f('ix_weekly_plans_week_start_date'), 'weekly_plans', ['week_start_date'], unique=False)
    
    # Create activities table
    op.create_table('activities',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('strava_id', sa.String(), nullable=True),
        sa.Column('activity_type', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=True),
        sa.Column('start_date', sa.DateTime(), nullable=False),
        sa.Column('distance_meters', sa.Float(), nullable=True),
        sa.Column('moving_time_seconds', sa.Integer(), nullable=True),
        sa.Column('elapsed_time_seconds', sa.Integer(), nullable=True),
        sa.Column('total_elevation_gain', sa.Float(), nullable=True),
        sa.Column('average_speed', sa.Float(), nullable=True),
        sa.Column('max_speed', sa.Float(), nullable=True),
        sa.Column('average_heartrate', sa.Float(), nullable=True),
        sa.Column('max_heartrate', sa.Float(), nullable=True),
        sa.Column('average_cadence', sa.Float(), nullable=True),
        sa.Column('average_watts', sa.Float(), nullable=True),
        sa.Column('max_watts', sa.Float(), nullable=True),
        sa.Column('kilojoules', sa.Float(), nullable=True),
        sa.Column('suffer_score', sa.Float(), nullable=True),
        sa.Column('tss', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_activities_strava_id'), 'activities', ['strava_id'], unique=True)
    op.create_index(op.f('ix_activities_user_id'), 'activities', ['user_id'], unique=False)
    op.create_index(op.f('ix_activities_start_date'), 'activities', ['start_date'], unique=False)
    
    # Create training_load table
    op.create_table('training_load',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('tss', sa.Float(), nullable=True, default=0.0),
        sa.Column('ctl', sa.Float(), nullable=True, default=0.0),
        sa.Column('atl', sa.Float(), nullable=True, default=0.0),
        sa.Column('tsb', sa.Float(), nullable=True, default=0.0),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'date', name='uix_user_date')
    )
    op.create_index(op.f('ix_training_load_user_id'), 'training_load', ['user_id'], unique=False)
    op.create_index(op.f('ix_training_load_date'), 'training_load', ['date'], unique=False)
    
    # Create app_state table
    op.create_table('app_state',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('key', sa.String(), nullable=False),
        sa.Column('value', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('key')
    )
    
    # Create segments table
    op.create_table('segments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('strava_segment_id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('activity_type', sa.String(), nullable=False),
        sa.Column('distance', sa.Float(), nullable=True),
        sa.Column('average_grade', sa.Float(), nullable=True),
        sa.Column('maximum_grade', sa.Float(), nullable=True),
        sa.Column('elevation_high', sa.Float(), nullable=True),
        sa.Column('elevation_low', sa.Float(), nullable=True),
        sa.Column('start_latlng', sa.JSON(), nullable=True),
        sa.Column('end_latlng', sa.JSON(), nullable=True),
        sa.Column('climb_category', sa.Integer(), nullable=True),
        sa.Column('city', sa.String(), nullable=True),
        sa.Column('state', sa.String(), nullable=True),
        sa.Column('country', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('strava_segment_id')
    )
    
    # Create segment_efforts table
    op.create_table('segment_efforts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('segment_id', sa.Integer(), nullable=False),
        sa.Column('activity_id', sa.Integer(), nullable=False),
        sa.Column('strava_effort_id', sa.String(), nullable=False),
        sa.Column('elapsed_time', sa.Integer(), nullable=False),
        sa.Column('moving_time', sa.Integer(), nullable=False),
        sa.Column('start_date', sa.DateTime(), nullable=False),
        sa.Column('average_heartrate', sa.Float(), nullable=True),
        sa.Column('max_heartrate', sa.Float(), nullable=True),
        sa.Column('average_watts', sa.Float(), nullable=True),
        sa.Column('device_watts', sa.Boolean(), nullable=True, default=False),
        sa.Column('average_cadence', sa.Float(), nullable=True),
        sa.Column('kom_rank', sa.Integer(), nullable=True),
        sa.Column('pr_rank', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['activity_id'], ['activities.id'], ),
        sa.ForeignKeyConstraint(['segment_id'], ['segments.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('strava_effort_id')
    )
    
    # Create personal_records table
    op.create_table('personal_records',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('segment_id', sa.Integer(), nullable=False),
        sa.Column('effort_id', sa.Integer(), nullable=False),
        sa.Column('elapsed_time', sa.Integer(), nullable=False),
        sa.Column('achieved_at', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['effort_id'], ['segment_efforts.id'], ),
        sa.ForeignKeyConstraint(['segment_id'], ['segments.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'segment_id', name='uix_user_segment_pr')
    )
    
    # Create injury_risk table
    op.create_table('injury_risk',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('risk_level', sa.String(), nullable=False),
        sa.Column('risk_score', sa.Float(), nullable=False),
        sa.Column('contributing_factors', sa.JSON(), nullable=True),
        sa.Column('recommendations', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create nutrition_targets table
    op.create_table('nutrition_targets',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('daily_calories', sa.Float(), nullable=False),
        sa.Column('carbs_grams', sa.Float(), nullable=False),
        sa.Column('protein_grams', sa.Float(), nullable=False),
        sa.Column('fat_grams', sa.Float(), nullable=False),
        sa.Column('hydration_liters', sa.Float(), nullable=False),
        sa.Column('activity_level', sa.String(), nullable=True),
        sa.Column('training_phase', sa.String(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create nutrition_plans table
    op.create_table('nutrition_plans',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('plan_date', sa.Date(), nullable=False),
        sa.Column('plan_type', sa.String(), nullable=False),
        sa.Column('meals', sa.JSON(), nullable=False),
        sa.Column('total_calories', sa.Float(), nullable=True),
        sa.Column('total_carbs', sa.Float(), nullable=True),
        sa.Column('total_protein', sa.Float(), nullable=True),
        sa.Column('total_fat', sa.Float(), nullable=True),
        sa.Column('ai_recommendations', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('nutrition_plans')
    op.drop_table('nutrition_targets')
    op.drop_table('injury_risk')
    op.drop_table('personal_records')
    op.drop_table('segment_efforts')
    op.drop_table('segments')
    op.drop_table('app_state')
    op.drop_table('training_load')
    op.drop_table('activities')
    op.drop_table('weekly_plans')
    op.drop_table('goals')
    op.drop_table('athlete_profiles')
    op.drop_table('users')
