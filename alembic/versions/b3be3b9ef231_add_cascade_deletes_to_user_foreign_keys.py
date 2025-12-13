"""add_cascade_deletes_to_user_foreign_keys

Revision ID: b3be3b9ef231
Revises: f5fe23df9eda
Create Date: 2025-12-13 06:49:51.171906

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b3be3b9ef231'
down_revision = 'f5fe23df9eda'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### Modify existing foreign keys to add CASCADE delete ###
    # List of tables with user_id foreign key
    tables_with_user_fk = [
        'athlete_profiles',
        'goals',
        'weekly_plans',
        'activities',
        'training_load',
        'segment_efforts',
        'personal_records',
        'injury_risks',
        'nutrition_targets',
        'nutrition_plans'
    ]
    
    # For each table, drop existing foreign key and create new one with CASCADE
    for table_name in tables_with_user_fk:
        # Check if table exists and has foreign key, then modify it
        op.execute(f"""
            DO $$ 
            DECLARE
                r RECORD;
                table_exists BOOLEAN;
            BEGIN
                -- Check if table exists
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = '{table_name}'
                ) INTO table_exists;
                
                IF table_exists THEN
                    -- Drop existing foreign key constraint (find it dynamically)
                    FOR r IN (
                        SELECT constraint_name 
                        FROM information_schema.table_constraints 
                        WHERE table_name = '{table_name}' 
                        AND constraint_type = 'FOREIGN KEY'
                        AND constraint_name LIKE '%user_id%'
                    ) LOOP
                        EXECUTE 'ALTER TABLE {table_name} DROP CONSTRAINT IF EXISTS ' || quote_ident(r.constraint_name);
                    END LOOP;
                    
                    -- Create new foreign key with CASCADE
                    EXECUTE 'ALTER TABLE {table_name} ADD CONSTRAINT {table_name}_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE';
                END IF;
            END $$;
        """)


def downgrade() -> None:
    # ### Revert CASCADE deletes - remove CASCADE and restore normal foreign keys ###
    # List of tables with user_id foreign key
    tables_with_user_fk = [
        'athlete_profiles',
        'goals',
        'weekly_plans',
        'activities',
        'training_load',
        'segment_efforts',
        'personal_records',
        'injury_risks',
        'nutrition_targets',
        'nutrition_plans'
    ]
    
    # For each table, drop CASCADE foreign key and create normal one without CASCADE
    for table_name in tables_with_user_fk:
        # Check if table exists and modify foreign key
        op.execute(f"""
            DO $$ 
            DECLARE
                r RECORD;
                table_exists BOOLEAN;
            BEGIN
                -- Check if table exists
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = '{table_name}'
                ) INTO table_exists;
                
                IF table_exists THEN
                    -- Drop existing CASCADE foreign key constraint (find it dynamically)
                    FOR r IN (
                        SELECT constraint_name 
                        FROM information_schema.table_constraints 
                        WHERE table_name = '{table_name}' 
                        AND constraint_type = 'FOREIGN KEY'
                        AND constraint_name LIKE '%user_id%'
                    ) LOOP
                        EXECUTE 'ALTER TABLE {table_name} DROP CONSTRAINT IF EXISTS ' || quote_ident(r.constraint_name);
                    END LOOP;
                    
                    -- Create normal foreign key without CASCADE
                    EXECUTE 'ALTER TABLE {table_name} ADD CONSTRAINT {table_name}_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id)';
                END IF;
            END $$;
        """)
