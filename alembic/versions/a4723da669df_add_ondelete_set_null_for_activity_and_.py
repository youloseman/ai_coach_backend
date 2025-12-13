"""add_ondelete_set_null_for_activity_and_goal_fks

Revision ID: a4723da669df
Revises: 281bb2303223
Create Date: 2025-12-13 07:13:26.440539

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a4723da669df'
down_revision = '281bb2303223'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
    DO $$
    DECLARE
        r RECORD;
        table_exists BOOLEAN;
    BEGIN
        -- segment_efforts.activity_id -> activities.id ON DELETE SET NULL
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_name = 'segment_efforts'
        ) INTO table_exists;
        
        IF table_exists THEN
            FOR r IN (
                SELECT tc.constraint_name
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu
                  ON tc.constraint_name = kcu.constraint_name
                 AND tc.table_name = kcu.table_name
                WHERE tc.table_name = 'segment_efforts'
                  AND tc.constraint_type = 'FOREIGN KEY'
                  AND kcu.column_name = 'activity_id'
            ) LOOP
                EXECUTE 'ALTER TABLE segment_efforts DROP CONSTRAINT IF EXISTS ' || quote_ident(r.constraint_name);
            END LOOP;
            EXECUTE 'ALTER TABLE segment_efforts ADD CONSTRAINT segment_efforts_activity_id_fkey
                     FOREIGN KEY (activity_id) REFERENCES activities(id) ON DELETE SET NULL';
        END IF;

        -- personal_records.activity_id -> activities.id ON DELETE SET NULL
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_name = 'personal_records'
        ) INTO table_exists;
        
        IF table_exists THEN
            FOR r IN (
                SELECT tc.constraint_name
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu
                  ON tc.constraint_name = kcu.constraint_name
                 AND tc.table_name = kcu.table_name
                WHERE tc.table_name = 'personal_records'
                  AND tc.constraint_type = 'FOREIGN KEY'
                  AND kcu.column_name = 'activity_id'
            ) LOOP
                EXECUTE 'ALTER TABLE personal_records DROP CONSTRAINT IF EXISTS ' || quote_ident(r.constraint_name);
            END LOOP;
            EXECUTE 'ALTER TABLE personal_records ADD CONSTRAINT personal_records_activity_id_fkey
                     FOREIGN KEY (activity_id) REFERENCES activities(id) ON DELETE SET NULL';
        END IF;

        -- weekly_plans.goal_id -> goals.id ON DELETE SET NULL
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_name = 'weekly_plans'
        ) INTO table_exists;
        
        IF table_exists THEN
            FOR r IN (
                SELECT tc.constraint_name
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu
                  ON tc.constraint_name = kcu.constraint_name
                 AND tc.table_name = kcu.table_name
                WHERE tc.table_name = 'weekly_plans'
                  AND tc.constraint_type = 'FOREIGN KEY'
                  AND kcu.column_name = 'goal_id'
            ) LOOP
                EXECUTE 'ALTER TABLE weekly_plans DROP CONSTRAINT IF EXISTS ' || quote_ident(r.constraint_name);
            END LOOP;
            EXECUTE 'ALTER TABLE weekly_plans ADD CONSTRAINT weekly_plans_goal_id_fkey
                     FOREIGN KEY (goal_id) REFERENCES goals(id) ON DELETE SET NULL';
        END IF;
    END $$;
    """)


def downgrade() -> None:
    op.execute("""
    DO $$
    DECLARE
        r RECORD;
        table_exists BOOLEAN;
    BEGIN
        -- segment_efforts.activity_id revert
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_name = 'segment_efforts'
        ) INTO table_exists;
        
        IF table_exists THEN
            FOR r IN (
                SELECT tc.constraint_name
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu
                  ON tc.constraint_name = kcu.constraint_name
                 AND tc.table_name = kcu.table_name
                WHERE tc.table_name = 'segment_efforts'
                  AND tc.constraint_type = 'FOREIGN KEY'
                  AND kcu.column_name = 'activity_id'
            ) LOOP
                EXECUTE 'ALTER TABLE segment_efforts DROP CONSTRAINT IF EXISTS ' || quote_ident(r.constraint_name);
            END LOOP;
            EXECUTE 'ALTER TABLE segment_efforts ADD CONSTRAINT segment_efforts_activity_id_fkey
                     FOREIGN KEY (activity_id) REFERENCES activities(id)';
        END IF;

        -- personal_records.activity_id revert
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_name = 'personal_records'
        ) INTO table_exists;
        
        IF table_exists THEN
            FOR r IN (
                SELECT tc.constraint_name
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu
                  ON tc.constraint_name = kcu.constraint_name
                 AND tc.table_name = kcu.table_name
                WHERE tc.table_name = 'personal_records'
                  AND tc.constraint_type = 'FOREIGN KEY'
                  AND kcu.column_name = 'activity_id'
            ) LOOP
                EXECUTE 'ALTER TABLE personal_records DROP CONSTRAINT IF EXISTS ' || quote_ident(r.constraint_name);
            END LOOP;
            EXECUTE 'ALTER TABLE personal_records ADD CONSTRAINT personal_records_activity_id_fkey
                     FOREIGN KEY (activity_id) REFERENCES activities(id)';
        END IF;

        -- weekly_plans.goal_id revert
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_name = 'weekly_plans'
        ) INTO table_exists;
        
        IF table_exists THEN
            FOR r IN (
                SELECT tc.constraint_name
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu
                  ON tc.constraint_name = kcu.constraint_name
                 AND tc.table_name = kcu.table_name
                WHERE tc.table_name = 'weekly_plans'
                  AND tc.constraint_type = 'FOREIGN KEY'
                  AND kcu.column_name = 'goal_id'
            ) LOOP
                EXECUTE 'ALTER TABLE weekly_plans DROP CONSTRAINT IF EXISTS ' || quote_ident(r.constraint_name);
            END LOOP;
            EXECUTE 'ALTER TABLE weekly_plans ADD CONSTRAINT weekly_plans_goal_id_fkey
                     FOREIGN KEY (goal_id) REFERENCES goals(id)';
        END IF;
    END $$;
    """)
