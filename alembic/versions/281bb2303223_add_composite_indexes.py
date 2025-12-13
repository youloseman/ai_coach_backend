"""add_composite_indexes

Revision ID: 281bb2303223
Revises: 66bda55f909d
Create Date: 2025-12-13 07:04:26.141478

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '281bb2303223'
down_revision = '66bda55f909d'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### Add composite indexes to existing tables ###
    op.execute("""
        DO $$ 
        DECLARE
            table_exists BOOLEAN;
        BEGIN
            -- Add indexes for activities table
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'activities'
            ) INTO table_exists;
            
            IF table_exists THEN
                -- idx_activities_user_date
                IF NOT EXISTS (
                    SELECT 1 FROM pg_indexes 
                    WHERE indexname = 'idx_activities_user_date'
                ) THEN
                    CREATE INDEX idx_activities_user_date 
                    ON activities (user_id, start_date);
                END IF;
                
                -- idx_activities_user_sport
                IF NOT EXISTS (
                    SELECT 1 FROM pg_indexes 
                    WHERE indexname = 'idx_activities_user_sport'
                ) THEN
                    CREATE INDEX idx_activities_user_sport 
                    ON activities (user_id, sport_type);
                END IF;
                
                -- idx_activities_strava
                IF NOT EXISTS (
                    SELECT 1 FROM pg_indexes 
                    WHERE indexname = 'idx_activities_strava'
                ) THEN
                    CREATE INDEX idx_activities_strava 
                    ON activities (strava_id);
                END IF;
            END IF;
            
            -- Add indexes for goals table
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'goals'
            ) INTO table_exists;
            
            IF table_exists THEN
                -- idx_goals_user_date
                IF NOT EXISTS (
                    SELECT 1 FROM pg_indexes 
                    WHERE indexname = 'idx_goals_user_date'
                ) THEN
                    CREATE INDEX idx_goals_user_date 
                    ON goals (user_id, race_date);
                END IF;
                
                -- idx_goals_user_type
                IF NOT EXISTS (
                    SELECT 1 FROM pg_indexes 
                    WHERE indexname = 'idx_goals_user_type'
                ) THEN
                    CREATE INDEX idx_goals_user_type 
                    ON goals (user_id, goal_type);
                END IF;
            END IF;
            
            -- Add indexes for weekly_plans table
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'weekly_plans'
            ) INTO table_exists;
            
            IF table_exists THEN
                -- idx_weekly_plans_user_date
                IF NOT EXISTS (
                    SELECT 1 FROM pg_indexes 
                    WHERE indexname = 'idx_weekly_plans_user_date'
                ) THEN
                    CREATE INDEX idx_weekly_plans_user_date 
                    ON weekly_plans (user_id, week_start_date);
                END IF;
            END IF;
        END $$;
    """)


def downgrade() -> None:
    # ### Remove composite indexes from tables ###
    op.execute("""
        DO $$ 
        BEGIN
            -- Drop indexes for activities table
            IF EXISTS (
                SELECT 1 FROM pg_indexes 
                WHERE indexname = 'idx_activities_user_date'
            ) THEN
                DROP INDEX idx_activities_user_date;
            END IF;
            
            IF EXISTS (
                SELECT 1 FROM pg_indexes 
                WHERE indexname = 'idx_activities_user_sport'
            ) THEN
                DROP INDEX idx_activities_user_sport;
            END IF;
            
            IF EXISTS (
                SELECT 1 FROM pg_indexes 
                WHERE indexname = 'idx_activities_strava'
            ) THEN
                DROP INDEX idx_activities_strava;
            END IF;
            
            -- Drop indexes for goals table
            IF EXISTS (
                SELECT 1 FROM pg_indexes 
                WHERE indexname = 'idx_goals_user_date'
            ) THEN
                DROP INDEX idx_goals_user_date;
            END IF;
            
            IF EXISTS (
                SELECT 1 FROM pg_indexes 
                WHERE indexname = 'idx_goals_user_type'
            ) THEN
                DROP INDEX idx_goals_user_type;
            END IF;
            
            -- Drop indexes for weekly_plans table
            IF EXISTS (
                SELECT 1 FROM pg_indexes 
                WHERE indexname = 'idx_weekly_plans_user_date'
            ) THEN
                DROP INDEX idx_weekly_plans_user_date;
            END IF;
        END $$;
    """)
