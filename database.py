from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker
from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv()

# Base path (same folder as main backend modules)
BASE_DIR = Path(__file__).resolve().parent
DATABASE_FILE = BASE_DIR / "triathlon_coach.db"

# DATABASE_URL supports both SQLite (dev) and PostgreSQL (prod)
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DATABASE_FILE}")

# Heroku/old style URLs compatibility: postgres:// → postgresql://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Engine config
connect_args = {"check_same_thread": False} if "sqlite" in DATABASE_URL else {}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    echo=False,  # Set to True to see SQL queries
)

# Session maker
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


def get_db():
    """
    Database session dependency for FastAPI endpoints.
    Usage: db: Session = Depends(get_db)
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Initialize database - create all tables.
    For production with PostgreSQL you should use Alembic migrations instead.
    This function is safe to call multiple times - it won't recreate existing tables.
    """
    try:
        import models  # Import to register models
        
        # Only create tables if they don't exist (idempotent)
        # In production, Alembic migrations handle this
        Base.metadata.create_all(bind=engine, checkfirst=True)
    except Exception as e:
        # Log error but don't raise - let migrations handle it in production
        import logging
        logging.warning(f"Database initialization warning (this is OK if using migrations): {e}")