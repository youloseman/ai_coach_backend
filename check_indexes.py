"""Script to check indexes in PostgreSQL database"""
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

# Get DATABASE_URL from environment
database_url = os.getenv("DATABASE_URL")

# Fix Heroku-style URLs: postgres:// → postgresql://
if database_url and database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

if not database_url:
    print("ERROR: DATABASE_URL not found in environment")
    exit(1)

engine = create_engine(database_url)

# Query to get all indexes
query = text("""
    SELECT 
        schemaname,
        tablename,
        indexname,
        indexdef
    FROM pg_indexes
    WHERE schemaname = 'public'
    AND (
        indexname LIKE 'idx_activities%' OR
        indexname LIKE 'idx_goals%' OR
        indexname LIKE 'idx_weekly_plans%' OR
        indexname LIKE 'idx_training_load%'
    )
    ORDER BY tablename, indexname;
""")

print("Checking composite indexes...")
print("=" * 80)

with engine.connect() as conn:
    result = conn.execute(query)
    rows = result.fetchall()
    
    if not rows:
        print("No composite indexes found!")
    else:
        print(f"Found {len(rows)} composite indexes:\n")
        for row in rows:
            print(f"Table: {row[1]}")
            print(f"Index: {row[2]}")
            print(f"Definition: {row[3]}")
            print("-" * 80)

print("\n" + "=" * 80)
print("Checking for expected indexes...")

expected_indexes = {
    'activities': [
        'idx_activities_user_date',
        'idx_activities_user_sport',
        'idx_activities_strava'
    ],
    'goals': [
        'idx_goals_user_date',
        'idx_goals_user_type'
    ],
    'weekly_plans': [
        'idx_weekly_plans_user_date'
    ],
    'training_load': [
        'idx_training_load_user_date'
    ]
}

with engine.connect() as conn:
    for table, indexes in expected_indexes.items():
        print(f"\n{table}:")
        for idx_name in indexes:
            check_query = text("""
                SELECT EXISTS (
                    SELECT 1 FROM pg_indexes 
                    WHERE schemaname = 'public'
                    AND tablename = :table
                    AND indexname = :idx_name
                );
            """)
            result = conn.execute(check_query, {"table": table, "idx_name": idx_name})
            exists = result.scalar()
            status = "[OK]" if exists else "[MISSING]"
            print(f"  {status} {idx_name}")
