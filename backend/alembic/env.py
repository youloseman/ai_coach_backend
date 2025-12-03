from pathlib import Path
import os
import sys

from alembic import context
from sqlalchemy import engine_from_config, pool

# Ensure project root is on sys.path so we can import database and models
ROOT_DIR = Path(__file__).resolve().parents[2]
root_str = str(ROOT_DIR)
if root_str not in sys.path:
  sys.path.insert(0, root_str)

import models  # noqa: F401,E402

config = context.config
target_metadata = models.Base.metadata


def get_url() -> str:
  from dotenv import load_dotenv  # type: ignore

  load_dotenv()
  db_url = os.getenv("DATABASE_URL")
  if not db_url:
    # Fallback to SQLite in current directory for local/dev
    return "sqlite:///./triathlon_coach.db"
  if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)
  return db_url


def run_migrations_offline() -> None:
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
  configuration = config.get_section(config.config_ini_section, {}) or {}
  configuration["sqlalchemy.url"] = get_url()

  connectable = engine_from_config(
    configuration,
    prefix="sqlalchemy.",
    poolclass=pool.NullPool,
  )

  with connectable.connect() as connection:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
      context.run_migrations()


if context.is_offline_mode():
  run_migrations_offline()
else:
  run_migrations_online()


