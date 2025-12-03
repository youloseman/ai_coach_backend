"""
Advanced Training Analytics
Рассчитывает TSS, CTL, ATL, TSB и другие метрики для оценки нагрузки и готовности.
"""

import datetime as dt
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from utils import normalize_sport, parse_activity_date, activity_duration_hours


@dataclass
class TrainingMetrics:
    """Метрики тренировочной нагрузки для конкретного дня"""
    date: dt.date
    tss: float  # Training Stress Score
    ctl: float  # Chronic Training Load (fitness)
    atl: float  # Acute Training Load (fatigue)
    tsb: float  # Training Stress Balance (form)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "date": str(self.date),
            "tss": round(self.tss, 1),
            "ctl": round(self.ctl, 1),
            "atl": round(self.atl, 1),
            "tsb": round(self.tsb, 1),
            "form_status": self.get_form_status()
        }
    
    def get_form_status(self) -> str:
        """Интерпретация TSB (форма)"""
        if self.tsb > 20:
            return "fresh_peaked"  # Свежий, пик формы
        elif self.tsb > 5:
            return "optimal_race"  # Оптимально для гонки
        elif self.tsb > -10:
            return "neutral"  # Нейтральный баланс
        elif self.tsb > -30:
            return "productive_training"  # Продуктивная тренировка
        else:
            return "overreaching"  # Риск перетренированности


# ===== TSS CALCULATION =====

def calculate_tss_run(duration_hours: float, intensity_level: str = "moderate") -> float:
    """
    Рассчитывает TSS для бега.
    
    Упрощённая формула без power meter:
    TSS = duration_hours * 100 * intensity_factor
    
    Args:
        duration_hours: Длительность в часах
        intensity_level: "recovery", "easy", "moderate", "hard", "very_hard"
    
    Returns:
        TSS для тренировки
    """
    intensity_factors = {
        "recovery": 0.3,     # Z1 (очень легко)
        "easy": 0.5,         # Z2 (легко)
        "moderate": 0.7,     # Z2-Z3 (умеренно)
        "tempo": 0.85,       # Z3 (темп)
        "hard": 1.0,         # Z4 (порог)
        "very_hard": 1.2     # Z5 (VO2max)
    }
    
    if_value = intensity_factors.get(intensity_level, 0.7)
    tss = duration_hours * 100 * if_value
    
    return tss


def calculate_tss_bike(duration_hours: float, intensity_level: str = "moderate") -> float:
    """
    Рассчитывает TSS для велосипеда.
    
    Для велосипеда коэффициенты немного другие.
    """
    intensity_factors = {
        "recovery": 0.25,    # Z1
        "easy": 0.5,         # Z2
        "moderate": 0.65,    # Z2-Z3
        "tempo": 0.8,        # Z3 (sweet spot)
        "hard": 1.0,         # Z4 (threshold)
        "very_hard": 1.15    # Z5
    }
    
    if_value = intensity_factors.get(intensity_level, 0.65)
    tss = duration_hours * 100 * if_value
    
    return tss


def calculate_tss_swim(duration_hours: float, intensity_level: str = "moderate") -> float:
    """
    Рассчитывает TSS для плавания.
    
    Плавание обычно даёт меньше TSS чем бег/вело.
    """
    intensity_factors = {
        "recovery": 0.2,
        "easy": 0.4,
        "moderate": 0.6,
        "tempo": 0.75,
        "hard": 0.9,
        "very_hard": 1.1
    }
    
    if_value = intensity_factors.get(intensity_level, 0.6)
    tss = duration_hours * 100 * if_value
    
    return tss


def estimate_intensity_from_activity(activity: dict) -> str:
    """
    Оценивает интенсивность активности на основе доступных данных.
    
    Использует:
    - average_heartrate (если есть)
    - название тренировки
    - тип тренировки
    
    Returns:
        "recovery", "easy", "moderate", "tempo", "hard", "very_hard"
    """
    sport = normalize_sport(activity.get("sport_type"))
    name = (activity.get("name") or "").lower()
    avg_hr = activity.get("average_heartrate")
    max_hr = activity.get("max_heartrate")
    
    # Загружаем профиль для получения HR зон
    from athlete_profile import load_athlete_profile
    profile = load_athlete_profile()
    
    # Определяем интенсивность по HR (если есть)
    if avg_hr and profile:
        zones = None
        if sport == "run" and profile.training_zones_run:
            zones = profile.training_zones_run
            max_hr_profile = zones.get("max_hr", 192)
        elif sport == "bike" and profile.training_zones_bike:
            zones = profile.training_zones_bike
            max_hr_profile = zones.get("max_hr", 187)
        elif sport == "swim" and profile.training_zones_swim:
            zones = profile.training_zones_swim
            max_hr_profile = zones.get("max_hr", 189)
        
        if zones:
            hr_percent = (avg_hr / max_hr_profile) * 100
            
            if hr_percent < 60:
                return "recovery"
            elif hr_percent < 70:
                return "easy"
            elif hr_percent < 80:
                return "moderate"
            elif hr_percent < 85:
                return "tempo"
            elif hr_percent < 90:
                return "hard"
            else:
                return "very_hard"
    
    # Определяем по названию тренировки
    if any(word in name for word in ["recovery", "easy", "z1", "z2"]):
        return "easy"
    elif any(word in name for word in ["tempo", "sweet spot", "z3"]):
        return "tempo"
    elif any(word in name for word in ["threshold", "z4", "interval"]):
        return "hard"
    elif any(word in name for word in ["vo2", "z5", "sprint", "race"]):
        return "very_hard"
    elif any(word in name for word in ["long", "endurance"]):
        return "moderate"
    
    # По умолчанию - умеренная интенсивность
    return "moderate"


def calculate_tss_for_activity(activity: dict) -> float:
    """
    Рассчитывает TSS для конкретной активности.
    
    Args:
        activity: Активность из Strava
    
    Returns:
        TSS для этой тренировки
    """
    sport = normalize_sport(activity.get("sport_type"))
    duration_hours = activity_duration_hours(activity)
    
    if duration_hours == 0:
        return 0.0
    
    # Оценка интенсивности
    intensity = estimate_intensity_from_activity(activity)
    
    # Расчёт TSS в зависимости от вида спорта
    if sport == "run":
        return calculate_tss_run(duration_hours, intensity)
    elif sport == "bike":
        return calculate_tss_bike(duration_hours, intensity)
    elif sport == "swim":
        return calculate_tss_swim(duration_hours, intensity)
    else:
        # Для других видов (strength, etc) - базовый расчёт
        return duration_hours * 50  # Примерно половина от умеренной тренировки


# ===== CTL, ATL, TSB CALCULATION =====

def calculate_training_metrics(activities: List[dict], start_date: dt.date, days: int = 90) -> List[TrainingMetrics]:
    """
    Рассчитывает CTL, ATL, TSB для периода.
    
    Args:
        activities: Список активностей из Strava
        start_date: Начальная дата расчёта
        days: Количество дней для расчёта (по умолчанию 90)
    
    Returns:
        Список TrainingMetrics для каждого дня
    """
    # Сортируем активности по дате
    activities_sorted = sorted(activities, key=lambda x: parse_activity_date(x))
    
    # Группируем активности по дням и рассчитываем TSS
    daily_tss: Dict[dt.date, float] = {}
    
    for activity in activities_sorted:
        activity_date = parse_activity_date(activity)
        tss = calculate_tss_for_activity(activity)
        
        if activity_date in daily_tss:
            daily_tss[activity_date] += tss
        else:
            daily_tss[activity_date] = tss
    
    # Инициализируем CTL и ATL
    ctl = 0.0
    atl = 0.0
    
    # Константы экспоненциального сглаживания
    CTL_TIME_CONSTANT = 42  # дней (6 недель)
    ATL_TIME_CONSTANT = 7   # дней (1 неделя)
    
    ctl_exp = 2.0 / (CTL_TIME_CONSTANT + 1)
    atl_exp = 2.0 / (ATL_TIME_CONSTANT + 1)
    
    # Рассчитываем метрики для каждого дня
    metrics: List[TrainingMetrics] = []
    
    for day_offset in range(days):
        current_date = start_date - dt.timedelta(days=days - day_offset - 1)
        
        # TSS за этот день
        tss_today = daily_tss.get(current_date, 0.0)
        
        # Обновляем CTL (Chronic Training Load) - скользящая средняя за 42 дня
        ctl = ctl + ctl_exp * (tss_today - ctl)
        
        # Обновляем ATL (Acute Training Load) - скользящая средняя за 7 дней
        atl = atl + atl_exp * (tss_today - atl)
        
        # Рассчитываем TSB (Training Stress Balance)
        tsb = ctl - atl
        
        metrics.append(TrainingMetrics(
            date=current_date,
            tss=tss_today,
            ctl=ctl,
            atl=atl,
            tsb=tsb
        ))
    
    return metrics


def calculate_ramp_rate(metrics: List[TrainingMetrics], weeks: int = 4) -> float:
    """
    Рассчитывает скорость набора формы (CTL ramp rate).
    
    Безопасная скорость: 5-8 TSS/week
    Агрессивная: 8-12 TSS/week
    Опасная: >12 TSS/week
    
    Args:
        metrics: Список TrainingMetrics
        weeks: За сколько недель считать (по умолчанию 4)
    
    Returns:
        CTL изменение за неделю (TSS/week)
    """
    if len(metrics) < weeks * 7:
        return 0.0
    
    # CTL сейчас vs CTL N недель назад
    ctl_now = metrics[-1].ctl
    ctl_then = metrics[-(weeks * 7)].ctl
    
    # Изменение за неделю
    ramp_rate = (ctl_now - ctl_then) / weeks
    
    return ramp_rate


def get_form_interpretation(tsb: float) -> Dict[str, str]:
    """
    Интерпретирует TSB (форму).
    
    Returns:
        Словарь с описанием формы и рекомендациями
    """
    if tsb > 20:
        return {
            "status": "fresh_peaked",
            "label": "Fresh / Peaked",
            "description": "You are very fresh and may be losing fitness. Good for race day or after taper.",
            "recommendation": "Time to race or increase training load.",
            "color": "green"
        }
    elif tsb > 5:
        return {
            "status": "optimal_race",
            "label": "Race Ready",
            "description": "Optimal balance for racing. You are fresh but fitness is high.",
            "recommendation": "Perfect time for A-race or key workout.",
            "color": "lightgreen"
        }
    elif tsb > -10:
        return {
            "status": "neutral",
            "label": "Neutral / Maintaining",
            "description": "Good balance between fitness and fatigue. Sustainable training.",
            "recommendation": "Continue current training load.",
            "color": "yellow"
        }
    elif tsb > -30:
        return {
            "status": "productive_training",
            "label": "Productive Training",
            "description": "Building fitness through productive training. Some fatigue is normal.",
            "recommendation": "Keep training but watch for overtraining signs.",
            "color": "orange"
        }
    else:
        return {
            "status": "overreaching",
            "label": "High Fatigue / Overreaching",
            "description": "High fatigue levels. Risk of overtraining or injury.",
            "recommendation": "Consider a recovery week to reduce ATL.",
            "color": "red"
        }


def analyze_training_load(activities: List[dict], weeks_to_analyze: int = 12) -> Dict[str, Any]:
    """
    Комплексный анализ тренировочной нагрузки.
    
    Args:
        activities: Список активностей
        weeks_to_analyze: Количество недель для анализа
    
    Returns:
        Словарь с аналитикой
    """
    today = dt.date.today()
    days_to_analyze = weeks_to_analyze * 7
    
    # Рассчитываем метрики
    metrics = calculate_training_metrics(activities, today, days=days_to_analyze)
    
    if not metrics:
        return {
            "error": "No metrics calculated",
            "current_ctl": 0,
            "current_atl": 0,
            "current_tsb": 0
        }
    
    # Текущие значения
    current = metrics[-1]
    
    # Ramp rate (скорость набора формы)
    ramp_rate = calculate_ramp_rate(metrics, weeks=4)
    
    # Интерпретация формы
    form_interpretation = get_form_interpretation(current.tsb)
    
    # Средний TSS за неделю (последние 4 недели)
    last_28_days = metrics[-28:]
    avg_weekly_tss = sum(m.tss for m in last_28_days) / 4
    
    return {
        "current_date": str(today),
        "weeks_analyzed": weeks_to_analyze,
        "current_ctl": round(current.ctl, 1),
        "current_atl": round(current.atl, 1),
        "current_tsb": round(current.tsb, 1),
        "form_status": current.get_form_status(),
        "form_interpretation": form_interpretation,
        "ramp_rate": round(ramp_rate, 1),
        "ramp_rate_status": get_ramp_rate_status(ramp_rate),
        "avg_weekly_tss": round(avg_weekly_tss, 1),
        "metrics_timeline": [m.to_dict() for m in metrics[-28:]],  # Последние 4 недели
    }


def get_ramp_rate_status(ramp_rate: float) -> Dict[str, str]:
    """Оценка безопасности скорости набора формы"""
    if ramp_rate < 0:
        return {
            "status": "declining",
            "label": "Fitness Declining",
            "description": f"CTL decreasing by {abs(ramp_rate):.1f} TSS/week",
            "color": "gray"
        }
    elif ramp_rate < 5:
        return {
            "status": "safe",
            "label": "Safe / Maintaining",
            "description": f"CTL increasing slowly (+{ramp_rate:.1f} TSS/week)",
            "color": "green"
        }
    elif ramp_rate < 8:
        return {
            "status": "optimal",
            "label": "Optimal Build",
            "description": f"CTL increasing at healthy rate (+{ramp_rate:.1f} TSS/week)",
            "color": "lightgreen"
        }
    elif ramp_rate < 12:
        return {
            "status": "aggressive",
            "label": "Aggressive Build",
            "description": f"CTL increasing quickly (+{ramp_rate:.1f} TSS/week). Monitor fatigue.",
            "color": "orange"
        }
    else:
        return {
            "status": "risky",
            "label": "Too Fast",
            "description": f"CTL increasing too quickly (+{ramp_rate:.1f} TSS/week). High injury risk!",
            "color": "red"
        }