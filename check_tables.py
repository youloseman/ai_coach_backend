"""Script to check tables and migration status"""
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

database_url = os.getenv("DATABASE_URL")
if database_url and database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

if not database_url:
    print("ERROR: DATABASE_URL not found")
    exit(1)

engine = create_engine(database_url)

print("Checking tables...")
print("=" * 80)

with engine.connect() as conn:
    # Check if tables exist
    tables_query = text("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public'
        AND table_type = 'BASE TABLE'
        ORDER BY table_name;
    """)
    result = conn.execute(tables_query)
    tables = [row[0] for row in result.fetchall()]
    
    if tables:
        print(f"Found {len(tables)} tables:")
        for table in tables:
            print(f"  - {table}")
    else:
        print("No tables found in database!")
    
    print("\n" + "=" * 80)
    print("Checking alembic version...")
    
    # Check alembic version
    try:
        version_query = text("SELECT version_num FROM alembic_version;")
        result = conn.execute(version_query)
        version = result.scalar()
        print(f"Current migration version: {version}")
    except Exception as e:
        print(f"Error checking alembic version: {e}")
        print("Alembic version table might not exist")
