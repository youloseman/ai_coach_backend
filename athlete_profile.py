# athlete_profile.py
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Literal

from pydantic import BaseModel, Field

from state_store import load_state, save_state


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

PROFILE_PATH = DATA_DIR / "athlete_profile.json"
PROFILE_STATE_KEY = "coach_profile"

logger = logging.getLogger(__name__)


class AthleteProfile(BaseModel):
    """
    Профиль атлета.
    Часть полей задаётся руками, часть — автоматически из истории тренировок.
    """

    # --- Ручные поля ---
    level: Literal["beginner", "intermediate", "advanced", "high_performance"] = "intermediate"
    max_hours_per_week: float = 8.0      # комфортный максимум в пике

    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    age: Optional[int] = None

    # Какие дни под какие виды спорта обычно доступны
    preferred_sport_days: Dict[str, List[str]] = Field(
        default_factory=lambda: {
            "swim": ["Tue", "Thu"],
            "bike": ["Mon", "Wed", "Sat"],
            "run": ["Tue", "Thu", "Sun"],
            "strength": [],
        }
    )

    # Ограничения и важные нюансы
    injuries: Optional[str] = None           # травмы, слабые места
    constraints: Optional[str] = None        # нет бассейна, только станок и т.п.
    equipment: Optional[str] = None          # шоссе/TT, трейдмилл, роллеры
    notes: Optional[str] = None              # любые ручные комментарии

    # --- Авто-поля (из истории тренировок) ---
    auto_weeks_analyzed: Optional[int] = None
    auto_current_weekly_streak_weeks: Optional[int] = None
    auto_longest_weekly_streak_weeks: Optional[int] = None
    auto_avg_hours_last_12_weeks: Optional[float] = None
    auto_avg_hours_last_52_weeks: Optional[float] = None
    auto_discipline_hours_per_week: Optional[Dict[str, float]] = None  # {"run": X, "bike": Y, ...}
    
    # --- Training zones (auto-calculated) ---
    training_zones_run: Optional[Dict[str, Any]] = None
    training_zones_bike: Optional[Dict[str, Any]] = None
    training_zones_swim: Optional[Dict[str, Any]] = None
    zones_last_updated: Optional[str] = None  # ISO date when zones were last calculated


def _write_profile_file(profile: AthleteProfile) -> None:
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with PROFILE_PATH.open("w", encoding="utf-8") as f:
            json.dump(profile.model_dump(), f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning("Failed to persist athlete profile to disk: %s", e)


def load_athlete_profile() -> AthleteProfile:
    """
    Загружаем профиль из data/athlete_profile.json.
    Если файла нет или он битый — возвращаем профиль по умолчанию.
    """
    if not PROFILE_PATH.exists():
        persisted = None
        try:
            persisted = load_state(PROFILE_STATE_KEY)
        except Exception as e:
            logger.warning("Failed to load athlete profile from DB: %s", e)

        if persisted:
            try:
                profile = AthleteProfile(**persisted)
                _write_profile_file(profile)
                return profile
            except Exception as e:
                logger.warning("Failed to restore athlete profile snapshot: %s", e)
        return AthleteProfile()

    try:
        with PROFILE_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return AthleteProfile(**data)
    except Exception as e:
        logger.warning("Failed to load athlete profile: %s", e)
        return AthleteProfile()


def save_athlete_profile(profile: AthleteProfile) -> None:
    """
    Сохраняем профиль в JSON.
    """
    _write_profile_file(profile)
    try:
        save_state(PROFILE_STATE_KEY, profile.model_dump())
    except Exception as e:
        logger.warning("Failed to persist athlete profile snapshot: %s", e)