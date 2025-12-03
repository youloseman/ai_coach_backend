"""
Smart Fatigue Detection
Автоматическое определение усталости на основе HR данных и performance metrics.
"""

import datetime as dt
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from utils import normalize_sport, parse_activity_date


@dataclass
class FatigueIndicator:
    """Индикатор усталости"""
    type: str  # "hr_drift", "elevated_resting_hr", "pace_decline", "chronic_high_hr"
    severity: str  # "low", "medium", "high"
    description: str
    recommendation: str
    detected_date: dt.date
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "severity": self.severity,
            "description": self.description,
            "recommendation": self.recommendation,
            "detected_date": str(self.detected_date)
        }


@dataclass
class FatigueReport:
    """Отчёт по усталости"""
    overall_fatigue_level: str  # "low", "moderate", "high", "severe"
    fatigue_score: float  # 0-100 (0 = fresh, 100 = exhausted)
    indicators: List[FatigueIndicator]
    needs_recovery_week: bool
    days_since_rest: int
    consecutive_high_hr_days: int
    recommendations: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall_fatigue_level": self.overall_fatigue_level,
            "fatigue_score": round(self.fatigue_score, 1),
            "indicators": [ind.to_dict() for ind in self.indicators],
            "needs_recovery_week": self.needs_recovery_week,
            "days_since_rest": self.days_since_rest,
            "consecutive_high_hr_days": self.consecutive_high_hr_days,
            "recommendations": self.recommendations
        }


# ===== HR ANALYSIS =====

def calculate_baseline_hr(activities: List[dict], sport: str = "run", days: int = 28) -> Optional[float]:
    """
    Рассчитывает baseline среднего пульса для конкретного вида спорта.
    Берёт активности за последние N дней (по умолчанию 28).
    
    Returns:
        Средний HR для этого спорта за период
    """
    from utils import normalize_sport
    
    cutoff_date = dt.date.today() - dt.timedelta(days=days)
    
    hr_values = []
    for activity in activities:
        activity_date = parse_activity_date(activity)
        if not activity_date or activity_date < cutoff_date:
            continue
        
        activity_sport = normalize_sport(activity.get("sport_type"))
        if activity_sport != sport:
            continue
        
        avg_hr = activity.get("average_heartrate")
        if avg_hr:
            hr_values.append(avg_hr)
    
    if not hr_values:
        return None
    
    return sum(hr_values) / len(hr_values)


def detect_hr_drift(activities: List[dict], days_to_analyze: int = 7) -> List[FatigueIndicator]:
    """
    Детектирует HR drift - повышение пульса при той же интенсивности.
    
    Признаки:
    - Средний HR на easy runs выше на 5+ ударов чем baseline
    - Средний HR на tempo runs выше на 8+ ударов
    """
    indicators = []
    
    # Рассчитываем baseline за последние 28 дней
    baseline_run_hr = calculate_baseline_hr(activities, sport="run", days=28)
    baseline_bike_hr = calculate_baseline_hr(activities, sport="bike", days=28)
    
    if not baseline_run_hr and not baseline_bike_hr:
        return indicators
    
    # Анализируем последние N дней
    cutoff_date = dt.date.today() - dt.timedelta(days=days_to_analyze)
    
    elevated_count = 0
    latest_date = None
    
    for activity in activities:
        activity_date = parse_activity_date(activity)
        if not activity_date or activity_date < cutoff_date:
            continue
        
        sport = normalize_sport(activity.get("sport_type"))
        avg_hr = activity.get("average_heartrate")
        
        if not avg_hr:
            continue
        
        baseline = None
        if sport == "run" and baseline_run_hr:
            baseline = baseline_run_hr
        elif sport == "bike" and baseline_bike_hr:
            baseline = baseline_bike_hr
        
        if not baseline:
            continue
        
        # Проверяем elevation
        hr_diff = avg_hr - baseline
        
        if hr_diff > 5:  # HR повышен на 5+ ударов
            elevated_count += 1
            if not latest_date or activity_date > latest_date:
                latest_date = activity_date
    
    if elevated_count >= 2:  # 2+ тренировки с повышенным HR
        severity = "medium" if elevated_count < 4 else "high"
        indicators.append(FatigueIndicator(
            type="hr_drift",
            severity=severity,
            description=f"Heart rate elevated in {elevated_count} recent workouts (5+ bpm above baseline). Classic sign of accumulating fatigue.",
            recommendation="Consider reducing training intensity or adding an extra rest day.",
            detected_date=latest_date or dt.date.today()
        ))
    
    return indicators


def detect_chronic_high_hr(activities: List[dict], days: int = 7) -> Optional[FatigueIndicator]:
    """
    Детектирует хронически повышенный HR на протяжении нескольких дней подряд.
    
    Признак перетренированности: 3+ дня подряд высокий HR.
    """
    from athlete_profile import load_athlete_profile
    
    profile = load_athlete_profile()
    
    # Группируем активности по дням
    activities_by_day = {}
    for activity in activities:
        activity_date = parse_activity_date(activity)
        if not activity_date:
            continue
        
        if activity_date not in activities_by_day:
            activities_by_day[activity_date] = []
        activities_by_day[activity_date].append(activity)
    
    # Последние N дней
    cutoff_date = dt.date.today() - dt.timedelta(days=days)
    sorted_dates = sorted([d for d in activities_by_day.keys() if d >= cutoff_date], reverse=True)
    
    consecutive_high_days = 0
    
    for date in sorted_dates:
        day_activities = activities_by_day[date]
        
        # Проверяем есть ли активности с высоким HR
        has_high_hr = False
        for activity in day_activities:
            avg_hr = activity.get("average_heartrate")
            sport = normalize_sport(activity.get("sport_type"))
            
            if not avg_hr:
                continue
            
            # Получаем зоны для этого спорта
            max_hr = None
            if sport == "run" and profile.training_zones_run:
                max_hr = profile.training_zones_run.get("max_hr")
            elif sport == "bike" and profile.training_zones_bike:
                max_hr = profile.training_zones_bike.get("max_hr")
            
            if max_hr:
                hr_percent = (avg_hr / max_hr) * 100
                # Если средний HR > 75% max - считаем высоким
                if hr_percent > 75:
                    has_high_hr = True
                    break
        
        if has_high_hr:
            consecutive_high_days += 1
        else:
            break  # Прервали streak
    
    if consecutive_high_days >= 3:
        return FatigueIndicator(
            type="chronic_high_hr",
            severity="high",
            description=f"High heart rate detected for {consecutive_high_days} consecutive days. Your body needs recovery.",
            recommendation="Take 2-3 easy days or full rest. This is critical to prevent overtraining.",
            detected_date=dt.date.today()
        )
    
    return None


def detect_pace_decline(activities: List[dict], sport: str = "run") -> List[FatigueIndicator]:
    """
    Детектирует снижение темпа при том же пульсе (признак усталости).
    
    Сравнивает interval workouts или tempo runs:
    - Если темп падает на 5+ сек/км при том же HR - усталость
    """
    indicators = []
    
    # Находим interval/tempo тренировки за последние 14 дней
    cutoff_date = dt.date.today() - dt.timedelta(days=14)
    
    tempo_workouts = []
    for activity in activities:
        activity_date = parse_activity_date(activity)
        if not activity_date or activity_date < cutoff_date:
            continue
        
        activity_sport = normalize_sport(activity.get("sport_type"))
        if activity_sport != sport:
            continue
        
        name = (activity.get("name") or "").lower()
        # Ищем interval/tempo тренировки
        if any(keyword in name for keyword in ["interval", "tempo", "threshold", "z4", "z3"]):
            avg_hr = activity.get("average_heartrate")
            distance = activity.get("distance")
            time = activity.get("moving_time")
            
            if avg_hr and distance and time and distance > 1000:  # Минимум 1km
                pace_per_km = (time / 60) / (distance / 1000)  # минуты на км
                tempo_workouts.append({
                    "date": activity_date,
                    "avg_hr": avg_hr,
                    "pace_per_km": pace_per_km
                })
    
    if len(tempo_workouts) < 2:
        return indicators
    
    # Сортируем по дате
    tempo_workouts.sort(key=lambda x: x["date"])
    
    # Сравниваем последнюю тренировку с предыдущими
    latest = tempo_workouts[-1]
    previous = tempo_workouts[-2]
    
    # Если HR примерно одинаковый (+/- 5 bpm), но pace упал
    hr_diff = abs(latest["avg_hr"] - previous["avg_hr"])
    pace_diff = latest["pace_per_km"] - previous["pace_per_km"]  # секунды
    
    if hr_diff < 5 and pace_diff > 0.15:  # Pace упал на 9+ секунд/км (0.15 мин = 9 сек)
        indicators.append(FatigueIndicator(
            type="pace_decline",
            severity="medium",
            description=f"Pace declined by {int(pace_diff * 60)} sec/km at similar heart rate in recent tempo workout. This suggests muscular fatigue.",
            recommendation="Focus on easy training for 3-5 days to allow muscular recovery.",
            detected_date=latest["date"]
        ))
    
    return indicators


def calculate_days_since_rest(activities: List[dict]) -> int:
    """
    Рассчитывает сколько дней прошло с последнего дня полного отдыха.
    """
    # Группируем по дням
    activity_dates = set()
    for activity in activities:
        activity_date = parse_activity_date(activity)
        if activity_date:
            activity_dates.add(activity_date)
    
    if not activity_dates:
        return 0
    
    # Проверяем последовательно дни назад
    days_since_rest = 0
    current_date = dt.date.today()
    
    while days_since_rest < 14:  # Максимум 14 дней проверяем
        if current_date not in activity_dates:
            break
        days_since_rest += 1
        current_date -= dt.timedelta(days=1)
    
    return days_since_rest


# ===== MAIN FATIGUE DETECTION =====

def detect_fatigue(activities: List[dict]) -> FatigueReport:
    """
    Комплексный анализ усталости на основе всех индикаторов.
    
    Args:
        activities: Список активностей из Strava
    
    Returns:
        FatigueReport с результатами анализа
    """
    indicators: List[FatigueIndicator] = []
    
    # 1. HR drift detection
    hr_drift_indicators = detect_hr_drift(activities, days_to_analyze=7)
    indicators.extend(hr_drift_indicators)
    
    # 2. Chronic high HR detection
    chronic_hr_indicator = detect_chronic_high_hr(activities, days=7)
    if chronic_hr_indicator:
        indicators.append(chronic_hr_indicator)
    
    # 3. Pace decline detection
    pace_decline_indicators = detect_pace_decline(activities, sport="run")
    indicators.extend(pace_decline_indicators)
    
    # 4. Days since rest
    days_since_rest = calculate_days_since_rest(activities)
    if days_since_rest >= 7:
        indicators.append(FatigueIndicator(
            type="no_rest",
            severity="medium" if days_since_rest < 10 else "high",
            description=f"No full rest day for {days_since_rest} consecutive days. Body needs recovery.",
            recommendation="Take a full rest day within the next 24-48 hours.",
            detected_date=dt.date.today()
        ))
    
    # 5. Consecutive high HR days (для отчёта)
    consecutive_high_hr_days = 0
    if chronic_hr_indicator:
        # Извлекаем число из description
        desc = chronic_hr_indicator.description
        try:
            consecutive_high_hr_days = int(desc.split()[5])  # "High heart rate detected for X consecutive days"
        except:
            consecutive_high_hr_days = 3
    
    # Рассчитываем fatigue score (0-100)
    fatigue_score = 0.0
    
    for ind in indicators:
        if ind.severity == "low":
            fatigue_score += 15
        elif ind.severity == "medium":
            fatigue_score += 30
        elif ind.severity == "high":
            fatigue_score += 50
    
    # Cap at 100
    fatigue_score = min(fatigue_score, 100)
    
    # Определяем overall fatigue level
    if fatigue_score < 20:
        overall_level = "low"
    elif fatigue_score < 50:
        overall_level = "moderate"
    elif fatigue_score < 75:
        overall_level = "high"
    else:
        overall_level = "severe"
    
    # Нужна ли recovery week?
    needs_recovery = (
        fatigue_score >= 50 or
        any(ind.severity == "high" for ind in indicators) or
        days_since_rest >= 10
    )
    
    # Генерируем рекомендации
    recommendations = []
    
    if needs_recovery:
        recommendations.append("🚨 RECOVERY WEEK RECOMMENDED: Reduce training volume by 40-50% for the next 7 days.")
    
    if days_since_rest >= 7:
        recommendations.append("Take a full rest day within 24-48 hours.")
    
    if any(ind.type == "hr_drift" for ind in indicators):
        recommendations.append("Reduce training intensity - focus on Z1-Z2 only for 3-5 days.")
    
    if any(ind.type == "chronic_high_hr" for ind in indicators):
        recommendations.append("⚠️ CRITICAL: Your body is showing signs of overtraining. Take 2-3 days completely off.")
    
    if any(ind.type == "pace_decline" for ind in indicators):
        recommendations.append("Your muscles need recovery. Avoid hard workouts for 5-7 days.")
    
    if not recommendations:
        recommendations.append("Fatigue levels are manageable. Continue with planned training.")
    
    return FatigueReport(
        overall_fatigue_level=overall_level,
        fatigue_score=fatigue_score,
        indicators=indicators,
        needs_recovery_week=needs_recovery,
        days_since_rest=days_since_rest,
        consecutive_high_hr_days=consecutive_high_hr_days,
        recommendations=recommendations
    )


def get_fatigue_status_color(level: str) -> str:
    """Возвращает цвет для уровня усталости"""
    colors = {
        "low": "green",
        "moderate": "yellow",
        "high": "orange",
        "severe": "red"
    }
    return colors.get(level, "gray")


def get_fatigue_emoji(level: str) -> str:
    """Возвращает эмодзи для уровня усталости"""
    emojis = {
        "low": "💪",
        "moderate": "😐",
        "high": "😓",
        "severe": "🚨"
    }
    return emojis.get(level, "❓")