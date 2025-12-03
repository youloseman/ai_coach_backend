"""
Общие утилиты для работы с активностями Strava
"""
from typing import Optional
import datetime as dt


def normalize_sport(sport_type: Optional[str]) -> str:
    """
    Нормализует название вида спорта из Strava.
    
    Примеры:
        "Run" -> "run"
        "VirtualRide" -> "bike"
        "Swim" -> "swim"
    """
    if not sport_type:
        return "other"
    
    s = sport_type.lower()
    
    # Бег
    if any(word in s for word in ["run", "jog", "trail"]):
        return "run"
    
    # Велосипед
    if any(word in s for word in ["ride", "bike", "cycl", "virtual"]):
        return "bike"
    
    # Плавание
    if "swim" in s:
        return "swim"
    
    # Силовая
    if any(word in s for word in ["strength", "gym", "workout", "weight"]):
        return "strength"
    
    return "other"


def parse_activity_date(activity: dict) -> Optional[dt.date]:
    """
    Извлекает дату из Strava активности.
    
    Возвращает:
        date или None если не удалось распарсить
    """
    raw_start = activity.get("start_date")
    if not raw_start:
        return None
    
    try:
        dt_start = dt.datetime.fromisoformat(raw_start.replace("Z", "+00:00"))
        return dt_start.date()
    except (ValueError, AttributeError):
        return None


def activity_duration_hours(activity: dict) -> float:
    """
    Возвращает длительность активности в часах.
    """
    seconds = activity.get("moving_time_s") or activity.get("moving_time") or 0
    return float(seconds) / 3600.0


def activity_duration_minutes(activity: dict) -> int:
    """
    Возвращает длительность активности в минутах.
    """
    seconds = activity.get("moving_time_s") or activity.get("moving_time") or 0
    return int(round(seconds / 60))


def get_week_start(date: dt.date) -> dt.date:
    """
    Возвращает понедельник для данной даты.
    """
    return date - dt.timedelta(days=date.weekday())


def format_duration(minutes: Optional[float]) -> str:
    """
    Форматирует длительность в читаемый вид.
    
    Примеры:
        45 -> "45 min"
        90 -> "1 h 30 min"
        120 -> "2 h"
    """
    if not minutes:
        return "-"
    
    minutes = int(minutes)
    h = minutes // 60
    m = minutes % 60
    
    if h == 0:
        return f"{m} min"
    if m == 0:
        return f"{h} h"
    return f"{h} h {m} min"