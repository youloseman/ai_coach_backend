"""Initial schema with all tables

Revision ID: d0f411149017
Revises: 
Create Date: 2025-12-06 10:44:08.185716
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = 'd0f411149017'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Check if tables exist before creating them (idempotent migration)
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_tables = inspector.get_table_names()
    
    # Users table
    if 'users' not in existing_tables:
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
            sa.Column('is_active', sa.Boolean(), nullable=True),
            sa.Column('is_verified', sa.Boolean(), nullable=True),
            sa.Column('email_verified_at', sa.DateTime(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
            sa.Column('last_login_at', sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
        op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
        op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)
    
    # Athlete profiles
    if 'athlete_profiles' not in existing_tables:
        op.create_table('athlete_profiles',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('height_cm', sa.Float(), nullable=True),
            sa.Column('weight_kg', sa.Float(), nullable=True),
            sa.Column('age', sa.Integer(), nullable=True),
            sa.Column('gender', sa.String(), nullable=True),
            sa.Column('training_zones_run', sa.JSON(), nullable=True),
            sa.Column('training_zones_bike', sa.JSON(), nullable=True),
            sa.Column('training_zones_swim', sa.JSON(), nullable=True),
            sa.Column('zones_last_updated', sa.DateTime(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('user_id')
        )
        op.create_index(op.f('ix_athlete_profiles_user_id'), 'athlete_profiles', ['user_id'], unique=True)
    
    # Goals
    if 'goals' not in existing_tables:
        op.create_table('goals',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('goal_type', sa.String(), nullable=False),
            sa.Column('target_time', sa.String(), nullable=True),
            sa.Column('race_date', sa.Date(), nullable=True),
            sa.Column('is_primary', sa.Boolean(), nullable=True),
            sa.Column('is_completed', sa.Boolean(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_goals_user_id'), 'goals', ['user_id'], unique=False)
    
    # Weekly plans
    if 'weekly_plans' not in existing_tables:
        op.create_table('weekly_plans',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('week_start_date', sa.Date(), nullable=False),
            sa.Column('plan_data', sa.JSON(), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_weekly_plans_user_id'), 'weekly_plans', ['user_id'], unique=False)
        op.create_index(op.f('ix_weekly_plans_week_start_date'), 'weekly_plans', ['week_start_date'], unique=False)
    
    # Activities
    if 'activities' not in existing_tables:
        op.create_table('activities',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('strava_activity_id', sa.String(), nullable=False),
            sa.Column('name', sa.String(), nullable=True),
            sa.Column('sport_type', sa.String(), nullable=True),
            sa.Column('start_date', sa.DateTime(), nullable=True),
            sa.Column('distance_m', sa.Float(), nullable=True),
            sa.Column('moving_time_s', sa.Integer(), nullable=True),
            sa.Column('elapsed_time_s', sa.Integer(), nullable=True),
            sa.Column('total_elevation_gain_m', sa.Float(), nullable=True),
            sa.Column('average_speed_ms', sa.Float(), nullable=True),
            sa.Column('max_speed_ms', sa.Float(), nullable=True),
            sa.Column('average_heartrate', sa.Float(), nullable=True),
            sa.Column('max_heartrate', sa.Float(), nullable=True),
            sa.Column('average_watts', sa.Float(), nullable=True),
            sa.Column('kilojoules', sa.Float(), nullable=True),
            sa.Column('raw_data', sa.JSON(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_activities_strava_activity_id'), 'activities', ['strava_activity_id'], unique=True)
        op.create_index(op.f('ix_activities_user_id'), 'activities', ['user_id'], unique=False)
        op.create_index(op.f('ix_activities_start_date'), 'activities', ['start_date'], unique=False)
    
    # Training load
    if 'training_load' not in existing_tables:
        op.create_table('training_load',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('date', sa.Date(), nullable=False),
            sa.Column('ctl', sa.Float(), nullable=True),
            sa.Column('atl', sa.Float(), nullable=True),
            sa.Column('tsb', sa.Float(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_training_load_date'), 'training_load', ['date'], unique=False)
        op.create_index(op.f('ix_training_load_user_id'), 'training_load', ['user_id'], unique=False)
    
    # Segments
    if 'segments' not in existing_tables:
        op.create_table('segments',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('strava_segment_id', sa.String(), nullable=False),
            sa.Column('name', sa.String(), nullable=False),
            sa.Column('activity_type', sa.String(), nullable=False),
            sa.Column('distance_meters', sa.Float(), nullable=False),
            sa.Column('city', sa.String(), nullable=True),
            sa.Column('state', sa.String(), nullable=True),
            sa.Column('country', sa.String(), nullable=True),
            sa.Column('average_grade', sa.Float(), nullable=True),
            sa.Column('maximum_grade', sa.Float(), nullable=True),
            sa.Column('elevation_high', sa.Float(), nullable=True),
            sa.Column('elevation_low', sa.Float(), nullable=True),
            sa.Column('total_elevation_gain', sa.Float(), nullable=True),
            sa.Column('athlete_count', sa.Integer(), nullable=True),
            sa.Column('effort_count', sa.Integer(), nullable=True),
            sa.Column('star_count', sa.Integer(), nullable=True),
            sa.Column('raw_data', sa.JSON(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_segments_strava_segment_id'), 'segments', ['strava_segment_id'], unique=True)
    
    # Segment efforts
    if 'segment_efforts' not in existing_tables:
        op.create_table('segment_efforts',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('activity_id', sa.Integer(), nullable=True),
            sa.Column('segment_id', sa.Integer(), nullable=False),
            sa.Column('strava_effort_id', sa.String(), nullable=False),
            sa.Column('start_date', sa.DateTime(), nullable=False),
            sa.Column('elapsed_time_seconds', sa.Integer(), nullable=False),
            sa.Column('moving_time_seconds', sa.Integer(), nullable=True),
            sa.Column('average_heartrate', sa.Float(), nullable=True),
            sa.Column('max_heartrate', sa.Float(), nullable=True),
            sa.Column('average_watts', sa.Float(), nullable=True),
            sa.Column('average_cadence', sa.Float(), nullable=True),
            sa.Column('pr_rank', sa.Integer(), nullable=True),
            sa.Column('kom_rank', sa.Integer(), nullable=True),
            sa.Column('is_pr', sa.Boolean(), nullable=True),
            sa.Column('device_watts', sa.Boolean(), nullable=True),
            sa.Column('raw_data', sa.JSON(), nullable=True),
            sa.Column('synced_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['activity_id'], ['activities.id'], ),
            sa.ForeignKeyConstraint(['segment_id'], ['segments.id'], ),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_segment_efforts_activity_id'), 'segment_efforts', ['activity_id'], unique=False)
        op.create_index(op.f('ix_segment_efforts_is_pr'), 'segment_efforts', ['is_pr'], unique=False)
        op.create_index(op.f('ix_segment_efforts_segment_id'), 'segment_efforts', ['segment_id'], unique=False)
        op.create_index(op.f('ix_segment_efforts_start_date'), 'segment_efforts', ['start_date'], unique=False)
        op.create_index(op.f('ix_segment_efforts_strava_effort_id'), 'segment_efforts', ['strava_effort_id'], unique=True)
        op.create_index(op.f('ix_segment_efforts_user_id'), 'segment_efforts', ['user_id'], unique=False)
    
    # Personal records
    if 'personal_records' not in existing_tables:
        op.create_table('personal_records',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('activity_id', sa.Integer(), nullable=True),
            sa.Column('sport_type', sa.String(), nullable=False),
            sa.Column('distance_category', sa.String(), nullable=False),
            sa.Column('distance_meters', sa.Float(), nullable=False),
            sa.Column('time_seconds', sa.Integer(), nullable=False),
            sa.Column('pace_per_km', sa.Float(), nullable=True),
            sa.Column('speed_kmh', sa.Float(), nullable=True),
            sa.Column('average_heartrate', sa.Float(), nullable=True),
            sa.Column('average_watts', sa.Float(), nullable=True),
            sa.Column('elevation_gain', sa.Float(), nullable=True),
            sa.Column('achieved_date', sa.DateTime(), nullable=False),
            sa.Column('activity_name', sa.String(), nullable=True),
            sa.Column('is_current_pr', sa.Boolean(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('superseded_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['activity_id'], ['activities.id'], ),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_personal_records_achieved_date'), 'personal_records', ['achieved_date'], unique=False)
        op.create_index(op.f('ix_personal_records_activity_id'), 'personal_records', ['activity_id'], unique=False)
        op.create_index(op.f('ix_personal_records_distance_category'), 'personal_records', ['distance_category'], unique=False)
        op.create_index(op.f('ix_personal_records_is_current_pr'), 'personal_records', ['is_current_pr'], unique=False)
        op.create_index(op.f('ix_personal_records_sport_type'), 'personal_records', ['sport_type'], unique=False)
        op.create_index(op.f('ix_personal_records_user_id'), 'personal_records', ['user_id'], unique=False)
    
    # Injury risks
    if 'injury_risks' not in existing_tables:
        op.create_table('injury_risks',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('risk_level', sa.String(), nullable=False),
            sa.Column('risk_type', sa.String(), nullable=False),
            sa.Column('title', sa.String(), nullable=False),
            sa.Column('description', sa.Text(), nullable=False),
            sa.Column('recommendation', sa.Text(), nullable=False),
            sa.Column('trigger_metrics', sa.JSON(), nullable=True),
            sa.Column('detected_date', sa.Date(), nullable=False),
            sa.Column('acknowledged', sa.Boolean(), nullable=True),
            sa.Column('acknowledged_at', sa.DateTime(), nullable=True),
            sa.Column('resolved', sa.Boolean(), nullable=True),
            sa.Column('resolved_at', sa.DateTime(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_injury_risks_detected_date'), 'injury_risks', ['detected_date'], unique=False)
        op.create_index(op.f('ix_injury_risks_user_id'), 'injury_risks', ['user_id'], unique=False)
    
    # App state
    if 'app_state' not in existing_tables:
        op.create_table('app_state',
            sa.Column('key', sa.String(), nullable=False),
            sa.Column('value', sa.JSON(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint('key')
        )
    
    # Nutrition targets
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
    
    # Nutrition plans
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
    op.drop_table('app_state')
    op.drop_index(op.f('ix_injury_risks_user_id'), table_name='injury_risks')
    op.drop_index(op.f('ix_injury_risks_detected_date'), table_name='injury_risks')
    op.drop_table('injury_risks')
    op.drop_index(op.f('ix_personal_records_user_id'), table_name='personal_records')
    op.drop_index(op.f('ix_personal_records_sport_type'), table_name='personal_records')
    op.drop_index(op.f('ix_personal_records_is_current_pr'), table_name='personal_records')
    op.drop_index(op.f('ix_personal_records_distance_category'), table_name='personal_records')
    op.drop_index(op.f('ix_personal_records_activity_id'), table_name='personal_records')
    op.drop_index(op.f('ix_personal_records_achieved_date'), table_name='personal_records')
    op.drop_table('personal_records')
    op.drop_index(op.f('ix_segment_efforts_user_id'), table_name='segment_efforts')
    op.drop_index(op.f('ix_segment_efforts_strava_effort_id'), table_name='segment_efforts')
    op.drop_index(op.f('ix_segment_efforts_start_date'), table_name='segment_efforts')
    op.drop_index(op.f('ix_segment_efforts_segment_id'), table_name='segment_efforts')
    op.drop_index(op.f('ix_segment_efforts_is_pr'), table_name='segment_efforts')
    op.drop_index(op.f('ix_segment_efforts_activity_id'), table_name='segment_efforts')
    op.drop_table('segment_efforts')
    op.drop_index(op.f('ix_segments_strava_segment_id'), table_name='segments')
    op.drop_table('segments')
    op.drop_index(op.f('ix_training_load_user_id'), table_name='training_load')
    op.drop_index(op.f('ix_training_load_date'), table_name='training_load')
    op.drop_table('training_load')
    op.drop_index(op.f('ix_activities_start_date'), table_name='activities')
    op.drop_index(op.f('ix_activities_user_id'), table_name='activities')
    op.drop_index(op.f('ix_activities_strava_activity_id'), table_name='activities')
    op.drop_table('activities')
    op.drop_index(op.f('ix_weekly_plans_week_start_date'), table_name='weekly_plans')
    op.drop_index(op.f('ix_weekly_plans_user_id'), table_name='weekly_plans')
    op.drop_table('weekly_plans')
    op.drop_index(op.f('ix_goals_user_id'), table_name='goals')
    op.drop_table('goals')
    op.drop_index(op.f('ix_athlete_profiles_user_id'), table_name='athlete_profiles')
    op.drop_table('athlete_profiles')
    op.drop_index(op.f('ix_users_username'), table_name='users')
    op.drop_index(op.f('ix_users_id'), table_name='users')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
