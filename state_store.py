"""
Simple helper around the AppState table for persisting small JSON blobs.
Used to keep critical settings (Strava tokens, coach profile, etc.) across deploys.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from database import SessionLocal
import models


logger = logging.getLogger(__name__)


def _get_state_record(db: Session, key: str) -> Optional[models.AppState]:
    return db.query(models.AppState).filter(models.AppState.key == key).first()


def save_state(key: str, value: Any) -> None:
    """
    Persist arbitrary JSON-serializable structure under the provided key.
    """
    db = SessionLocal()
    try:
        record = _get_state_record(db, key)
        if record is None:
            record = models.AppState(key=key, value=value)
            db.add(record)
        else:
            record.value = value
        db.commit()
    except SQLAlchemyError as exc:
        logger.warning("Failed to persist state '%s': %s", key, exc)
        db.rollback()
    finally:
        db.close()


def load_state(key: str) -> Optional[Any]:
    """
    Load previously persisted value. Returns None if key is not present.
    """
    db = SessionLocal()
    try:
        record = _get_state_record(db, key)
        return record.value if record else None
    except SQLAlchemyError as exc:
        logger.warning("Failed to load state '%s': %s", key, exc)
        return None
    finally:
        db.close()