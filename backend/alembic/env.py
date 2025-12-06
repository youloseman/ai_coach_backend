from pathlib import Path
import os
import sys
from logging.config import fileConfig
from sqlalchemy import pool
from alembic import context
from sqlalchemy import engine_from_config

# Ensure project root is on sys.path
ROOT_DIR = Path(__file__).resolve().parents[2]
root_str = str(ROOT_DIR)
if root_str not in sys.path:
    sys.path.insert(0, root_str)

# Import Base and all models
import models  # noqa: E402, F401

config = context.config

# Use the Base.metadata from all imported models
target_metadata = models.Base.metadata


def get_url() -> str:
    """Get database URL from environment or use SQLite fallback"""
    from dotenv import load_dotenv
    
    load_dotenv()
    db_url = os.getenv("DATABASE_URL")
    
    if not db_url:
        # Fallback to SQLite in current directory for local/dev
        return "sqlite:///./triathlon_coach.db"
    
    # Fix postgres:// to postgresql:// for SQLAlchemy
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    
    return db_url


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    configuration = config.get_section(config.config_ini_section, {}) or {}
    configuration["sqlalchemy.url"] = get_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()