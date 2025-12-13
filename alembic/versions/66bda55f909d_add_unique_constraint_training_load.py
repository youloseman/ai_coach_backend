"""add_unique_constraint_training_load

Revision ID: 66bda55f909d
Revises: b3be3b9ef231
Create Date: 2025-12-13 06:59:13.916737

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '66bda55f909d'
down_revision = 'b3be3b9ef231'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### Add unique constraint and index to training_load table ###
    # Check if table exists and add constraints
    op.execute("""
        DO $$ 
        DECLARE
            table_exists BOOLEAN;
        BEGIN
            -- Check if table exists
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'training_load'
            ) INTO table_exists;
            
            IF table_exists THEN
                -- Create unique constraint if it doesn't exist
                IF NOT EXISTS (
                    SELECT 1 FROM pg_constraint 
                    WHERE conname = 'uix_training_load_user_date'
                ) THEN
                    ALTER TABLE training_load 
                    ADD CONSTRAINT uix_training_load_user_date 
                    UNIQUE (user_id, date);
                END IF;
                
                -- Create index if it doesn't exist
                IF NOT EXISTS (
                    SELECT 1 FROM pg_indexes 
                    WHERE indexname = 'idx_training_load_user_date'
                ) THEN
                    CREATE INDEX idx_training_load_user_date 
                    ON training_load (user_id, date);
                END IF;
            END IF;
        END $$;
    """)


def downgrade() -> None:
    # ### Remove unique constraint and index from training_load table ###
    op.execute("""
        DO $$ 
        DECLARE
            table_exists BOOLEAN;
        BEGIN
            -- Check if table exists
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'training_load'
            ) INTO table_exists;
            
            IF table_exists THEN
                -- Drop unique constraint if it exists
                IF EXISTS (
                    SELECT 1 FROM pg_constraint 
                    WHERE conname = 'uix_training_load_user_date'
                ) THEN
                    ALTER TABLE training_load 
                    DROP CONSTRAINT uix_training_load_user_date;
                END IF;
                
                -- Drop index if it exists
                IF EXISTS (
                    SELECT 1 FROM pg_indexes 
                    WHERE indexname = 'idx_training_load_user_date'
                ) THEN
                    DROP INDEX idx_training_load_user_date;
                END IF;
            END IF;
        END $$;
    """)
