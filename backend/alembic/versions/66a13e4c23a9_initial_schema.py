"""initial schema

Revision ID: 66a13e4c23a9
Revises: 
Create Date: 2025-12-03 00:12:47.820865
"""

from alembic import op
import sqlalchemy as sa
from database import Base  # type: ignore
import models  # noqa: F401


# revision identifiers, used by Alembic.
revision = '66a13e4c23a9'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Create all tables defined on SQLAlchemy Base metadata.

    This uses the same models as the application (`models.py`) so that the
    initial schema matches the current code, both for SQLite and PostgreSQL.
    """
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    """
    Drop all tables defined on SQLAlchemy Base metadata.
    """
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)


