"""
Calendar Export
Экспорт тренировочных планов в .ics формат для Google Calendar, Outlook, iCal.
"""

import datetime as dt
from typing import List, Dict, Any
from pathlib import Path
from ics import Calendar, Event
from ics.alarm import DisplayAlarm


BASE_DIR = Path(__file__).resolve().parent
EXPORTS_DIR = BASE_DIR / "data" / "calendar_exports"
EXPORTS_DIR.mkdir(parents=True, exist_ok=True)


def create_workout_event(
    day_plan: Dict[str, Any],
    date: dt.date,
    start_time: dt.time = dt.time(6, 0)  # Default: 6:00 AM
) -> Event:
    """
    Создаёт календарное событие из одной тренировки.
    
    Args:
        day_plan: План тренировки на день (из weekly plan)
        date: Дата тренировки
        start_time: Время начала (по умолчанию 6:00)
    
    Returns:
        Event объект для календаря
    """
    event = Event()
    
    # Название
    sport = day_plan.get("sport", "Training")
    session_type = day_plan.get("session_type", "")
    intensity = day_plan.get("intensity", "")
    
    event.name = f"🏃 {sport.title()} - {session_type}" if session_type else f"🏃 {sport.title()}"
    
    # Время
    duration_min = day_plan.get("duration_min", 60)
    start_datetime = dt.datetime.combine(date, start_time)
    end_datetime = start_datetime + dt.timedelta(minutes=duration_min)
    
    event.begin = start_datetime
    event.end = end_datetime
    
    # Описание
    description_parts = []
    
    description_parts.append(f"🎯 Primary Goal: {day_plan.get('primary_goal', 'N/A')}")
    description_parts.append(f"⚡ Intensity: {intensity}")
    description_parts.append(f"⏱️ Duration: {duration_min} min")
    description_parts.append(f"🔥 Priority: {day_plan.get('priority', 'Medium')}")
    
    workout_description = day_plan.get("description", "")
    if workout_description:
        description_parts.append(f"\n📝 Details:\n{workout_description}")
    
    event.description = "\n".join(description_parts)
    
    # Локация (опционально)
    if sport == "swim":
        event.location = "Pool"
    elif sport == "bike":
        event.location = "Indoor Trainer / Outdoor"
    elif sport == "run":
        event.location = "Outdoor / Treadmill"
    
    # Напоминание за 30 минут
    alarm = DisplayAlarm(trigger=dt.timedelta(minutes=-30))
    event.alarms.append(alarm)
    
    # Категория
    event.categories = [sport.title(), intensity]
    
    return event


def export_weekly_plan_to_ics(
    plan_data: Dict[str, Any],
    filename: str = None,
    default_start_time: dt.time = dt.time(6, 0)
) -> str:
    """
    Экспортирует недельный план тренировок в .ics файл.
    
    Args:
        plan_data: Данные плана (из run_weekly_plan)
        filename: Имя файла (если None, генерируется автоматически)
        default_start_time: Время начала тренировок по умолчанию
    
    Returns:
        Путь к созданному .ics файлу
    """
    calendar = Calendar()
    calendar.creator = "AI Triathlon Coach"
    
    # Название календаря
    week_start = plan_data.get("week_start_date", "unknown")
    calendar.name = f"Training Plan - Week {week_start}"
    
    # Добавляем тренировки
    days = plan_data.get("days", [])
    
    for day in days:
        date_str = day.get("date")
        if not date_str:
            continue
        
        try:
            date = dt.date.fromisoformat(date_str)
        except ValueError:
            continue
        
        # Определяем время начала на основе вида спорта
        sport = day.get("sport", "").lower()
        if sport == "swim":
            start_time = dt.time(6, 0)  # Swimming early morning
        elif sport == "bike":
            start_time = dt.time(8, 0)  # Cycling morning
        elif sport == "run":
            start_time = dt.time(7, 0)  # Running morning
        else:
            start_time = default_start_time
        
        event = create_workout_event(day, date, start_time)
        calendar.events.add(event)
    
    # Сохраняем файл
    if filename is None:
        filename = f"training_plan_{week_start}.ics"
    
    filepath = EXPORTS_DIR / filename
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.writelines(calendar.serialize_iter())
    
    return str(filepath)


def export_multi_week_plan_to_ics(
    multi_week_plan: Dict[str, Any],
    filename: str = None
) -> str:
    """
    Экспортирует многонедельный план в .ics файл.
    
    Args:
        multi_week_plan: Данные плана на несколько недель
        filename: Имя файла
    
    Returns:
        Путь к созданному .ics файлу
    """
    calendar = Calendar()
    calendar.creator = "AI Triathlon Coach"
    
    # Название
    start_date = multi_week_plan.get("start_date", "unknown")
    num_weeks = multi_week_plan.get("num_weeks", 0)
    calendar.name = f"Training Plan - {num_weeks} weeks starting {start_date}"
    
    # Добавляем тренировки по неделям
    weeks = multi_week_plan.get("weeks", [])
    
    for week in weeks:
        days = week.get("days", [])
        
        for day in days:
            date_str = day.get("date")
            if not date_str:
                continue
            
            try:
                date = dt.date.fromisoformat(date_str)
            except ValueError:
                continue
            
            sport = day.get("sport", "").lower()
            if sport == "swim":
                start_time = dt.time(6, 0)
            elif sport == "bike":
                start_time = dt.time(8, 0)
            elif sport == "run":
                start_time = dt.time(7, 0)
            else:
                start_time = dt.time(7, 0)
            
            event = create_workout_event(day, date, start_time)
            calendar.events.add(event)
    
    # Сохраняем
    if filename is None:
        filename = f"training_plan_{num_weeks}_weeks_{start_date}.ics"
    
    filepath = EXPORTS_DIR / filename
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.writelines(calendar.serialize_iter())
    
    return str(filepath)


def get_calendar_download_url(filepath: str) -> str:
    """
    Возвращает URL для скачивания .ics файла.
    
    В production это будет полный URL.
    Для локальной разработки - относительный путь.
    """
    filename = Path(filepath).name
    return f"/downloads/calendar/{filename}"


def cleanup_old_exports(days_old: int = 30):
    """
    Удаляет старые .ics файлы (старше N дней).
    """
    cutoff_date = dt.datetime.now() - dt.timedelta(days=days_old)
    
    for filepath in EXPORTS_DIR.glob("*.ics"):
        file_mtime = dt.datetime.fromtimestamp(filepath.stat().st_mtime)
        if file_mtime < cutoff_date:
            filepath.unlink()