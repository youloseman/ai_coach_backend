"""
Performance Predictions
Прогнозирование результатов на гонку на основе тренировочных данных.
"""

import datetime as dt
import math
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from utils import normalize_sport, parse_activity_date


@dataclass
class RaceEffort:
    """Лучший результат на конкретной дистанции"""
    distance_km: float
    time_seconds: float
    date: dt.date
    pace_per_km: float
    source: str  # "race" или "training"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "distance_km": round(self.distance_km, 2),
            "time_seconds": int(self.time_seconds),
            "time_formatted": format_time(self.time_seconds),
            "date": str(self.date),
            "pace_per_km": format_pace(self.pace_per_km),
            "source": self.source
        }


@dataclass
class RacePrediction:
    """Прогноз на конкретную гонку"""
    race_type: str  # "5K", "10K", "HM", "Marathon", "Olympic", "Half_Ironman", "Ironman"
    distance_km: float
    predicted_time_seconds: float
    predicted_time_formatted: str
    confidence: float  # 0-100%
    based_on: str  # На основе какой дистанции
    target_time_seconds: Optional[float] = None
    target_time_formatted: Optional[str] = None
    probability_of_success: Optional[float] = None  # 0-100%
    time_gap_seconds: Optional[float] = None  # Разница с целью
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            "race_type": self.race_type,
            "distance_km": self.distance_km,
            "predicted_time": self.predicted_time_formatted,
            "confidence": round(self.confidence, 1),
            "based_on": self.based_on
        }
        
        if self.target_time_seconds:
            result["target_time"] = self.target_time_formatted
            result["probability_of_success"] = round(self.probability_of_success, 1)
            result["time_gap"] = format_time(abs(self.time_gap_seconds))
            result["faster_or_slower"] = "faster" if self.time_gap_seconds < 0 else "slower"
        
        return result


# ===== UTILITY FUNCTIONS =====

def format_time(seconds: float) -> str:
    """Форматирует секунды в H:MM:SS"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    
    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes}:{secs:02d}"


def format_pace(seconds_per_km: float) -> str:
    """Форматирует темп в MM:SS/km"""
    minutes = int(seconds_per_km // 60)
    seconds = int(seconds_per_km % 60)
    return f"{minutes}:{seconds:02d}/km"


def parse_target_time(time_str: str) -> float:
    """
    Парсит целевое время из строки в секунды.
    
    Форматы: "1:30:00", "90:00", "45:30"
    """
    parts = time_str.strip().split(":")
    
    if len(parts) == 3:  # H:MM:SS
        hours, minutes, seconds = map(int, parts)
        return hours * 3600 + minutes * 60 + seconds
    elif len(parts) == 2:  # MM:SS
        minutes, seconds = map(int, parts)
        return minutes * 60 + seconds
    else:
        raise ValueError(f"Invalid time format: {time_str}")


# ===== RIEGEL FORMULA =====

def riegel_predict(known_distance_km: float, known_time_seconds: float, target_distance_km: float, fatigue_factor: float = 1.06) -> float:
    """
    Riegel formula для прогноза времени на другую дистанцию.
    
    Formula: T2 = T1 * (D2/D1)^fatigue_factor
    
    Args:
        known_distance_km: Известная дистанция
        known_time_seconds: Время на известной дистанции
        target_distance_km: Целевая дистанция
        fatigue_factor: Фактор усталости (обычно 1.06)
    
    Returns:
        Прогноз времени в секундах
    """
    distance_ratio = target_distance_km / known_distance_km
    predicted_time = known_time_seconds * (distance_ratio ** fatigue_factor)
    return predicted_time


def adjust_for_form(predicted_time_seconds: float, tsb: float) -> float:
    """
    Корректирует прогноз на основе формы (TSB).
    
    Args:
        predicted_time_seconds: Базовый прогноз
        tsb: Training Stress Balance
    
    Returns:
        Скорректированное время
    """
    # TSB adjustment:
    # TSB > +20: свежий, но теряешь форму (-1-2%)
    # TSB +5 to +20: optimal для гонки (0%)
    # TSB -10 to +5: neutral (-0.5%)
    # TSB -30 to -10: усталый (-2-5%)
    # TSB < -30: перетренирован (-5-10%)
    
    if tsb > 20:
        # Слишком свежий - потеря формы
        adjustment_percent = -1.0 - (tsb - 20) * 0.05  # -1% до -2%
    elif tsb >= 5:
        # Optimal
        adjustment_percent = 0.0
    elif tsb >= -10:
        # Neutral
        adjustment_percent = -0.5
    elif tsb >= -30:
        # Усталый
        adjustment_percent = -2.0 - abs(tsb + 10) * 0.15
    else:
        # Перетренирован
        adjustment_percent = -5.0 - abs(tsb + 30) * 0.2
        adjustment_percent = max(adjustment_percent, -10.0)  # Cap at -10%
    
    adjusted_time = predicted_time_seconds * (1 + adjustment_percent / 100)
    return adjusted_time


# ===== FIND BEST EFFORTS =====

def find_best_efforts(activities: List[dict], sport: str = "run") -> Dict[str, RaceEffort]:
    """
    Находит лучшие результаты на разных дистанциях.
    
    Returns:
        Dict с ключами: "5K", "10K", "HM", "Marathon"
    """
    best_efforts = {}
    
    # Целевые дистанции (в метрах) с более широкими диапазонами,
    # чтобы учитывать длинные тренировки, близкие к целевой дистанции.
    target_distances = {
        "5K": (4000, 6000),         # 4-6 km
        "10K": (8000, 12000),       # 8-12 km
        "HM": (18000, 25000),       # ~18-25 km (half marathon)
        "Marathon": (35000, 45000)  # ~35-45 km
    }
    
    for activity in activities:
        activity_sport = normalize_sport(activity.get("sport_type"))
        if activity_sport != sport:
            continue
        
        distance = activity.get("distance")
        moving_time = activity.get("moving_time")
        
        if not distance or not moving_time or distance < 1000:
            continue
        
        distance_km = distance / 1000
        
        # Определяем к какой дистанции относится
        for race_type, (min_dist, max_dist) in target_distances.items():
            if min_dist <= distance <= max_dist:
                # Проверяем - лучший ли это результат
                if race_type not in best_efforts or moving_time < best_efforts[race_type].time_seconds:
                    activity_date = parse_activity_date(activity)
                    pace_per_km = moving_time / distance_km
                    
                    best_efforts[race_type] = RaceEffort(
                        distance_km=distance_km,
                        time_seconds=moving_time,
                        date=activity_date or dt.date.today(),
                        pace_per_km=pace_per_km,
                        source="training"
                    )
                break
    
    return best_efforts


# ===== PREDICT RACE TIMES =====

def predict_race_times(
    best_efforts: Dict[str, RaceEffort],
    race_types: List[str] = None,
    tsb: Optional[float] = None
):
    """
    Прогнозирует времена на разные дистанции на основе лучших результатов.
    
    Args:
        best_efforts: Лучшие результаты на дистанциях
        race_types: Какие дистанции прогнозировать (если None - все)
        tsb: Training Stress Balance для корректировки формы
    
    Returns:
        Список прогнозов
    """
    if race_types is None:
        race_types = ["5K", "10K", "HM", "Marathon"]
    
    # Дистанции в км
    race_distances = {
        "5K": 5.0,
        "10K": 10.0,
        "HM": 21.0975,
        "Marathon": 42.195
    }
    
    predictions = []
    
    for target_race in race_types:
        if target_race not in race_distances:
            continue
        
        target_distance = race_distances[target_race]
        
        # Если есть прямой результат на этой дистанции - используем его
        if target_race in best_efforts:
            effort = best_efforts[target_race]
            predicted_time = effort.time_seconds
            confidence = 95.0
            based_on = f"{target_race} PR"
        else:
            # Ищем ближайшую дистанцию для прогноза
            best_base = None
            best_distance_diff = float('inf')
            
            for race_type, effort in best_efforts.items():
                distance_diff = abs(effort.distance_km - target_distance)
                if distance_diff < best_distance_diff:
                    best_distance_diff = distance_diff
                    best_base = (race_type, effort)
            
            if not best_base:
                continue
            
            base_race_type, base_effort = best_base
            
            # Riegel prediction
            predicted_time = riegel_predict(
                known_distance_km=base_effort.distance_km,
                known_time_seconds=base_effort.time_seconds,
                target_distance_km=target_distance
            )
            
            # Confidence зависит от разницы дистанций
            distance_ratio = target_distance / base_effort.distance_km
            if 0.5 <= distance_ratio <= 2.0:
                confidence = 85.0
            elif 0.3 <= distance_ratio <= 3.0:
                confidence = 70.0
            else:
                confidence = 50.0
            
            based_on = f"{base_race_type} result"
        
        # Корректируем на форму (если TSB известен)
        if tsb is not None:
            predicted_time = adjust_for_form(predicted_time, tsb)
        
        predictions.append(RacePrediction(
            race_type=target_race,
            distance_km=target_distance,
            predicted_time_seconds=predicted_time,
            predicted_time_formatted=format_time(predicted_time),
            confidence=confidence,
            based_on=based_on
        ))
    
    return predictions


def calculate_success_probability(
    predicted_time_seconds: float,
    target_time_seconds: float,
    confidence: float
) -> float:
    """
    Рассчитывает вероятность достижения целевого времени.
    
    Args:
        predicted_time_seconds: Прогнозируемое время
        target_time_seconds: Целевое время
        confidence: Уверенность в прогнозе (0-100)
    
    Returns:
        Вероятность успеха (0-100%)
    """
    time_gap_percent = ((predicted_time_seconds - target_time_seconds) / target_time_seconds) * 100
    
    # Базовая вероятность на основе разницы времен
    if time_gap_percent <= -10:  # Прогноз на 10%+ быстрее цели
        base_probability = 95.0
    elif time_gap_percent <= -5:  # 5-10% быстрее
        base_probability = 85.0
    elif time_gap_percent <= 0:  # 0-5% быстрее
        base_probability = 70.0
    elif time_gap_percent <= 5:  # 0-5% медленнее
        base_probability = 45.0
    elif time_gap_percent <= 10:  # 5-10% медленнее
        base_probability = 25.0
    else:  # >10% медленнее
        base_probability = 10.0
    
    # Корректируем на уверенность в прогнозе
    adjusted_probability = base_probability * (confidence / 100)
    
    return min(adjusted_probability, 95.0)  # Cap at 95%


def normalize_goal_race_type(goal_race_type: str) -> str:
    """
    Нормализует тип цели гонки к одной из базовых дистанций для расчёта:
    5K, 10K, HM, Marathon.

    Это позволяет использовать одни и те же алгоритмы для беговых
    и триатлонных целей (SPRINT/OLYMPIC/HALF_IRONMAN/IRONMAN).
    """
    t = goal_race_type.upper()

    # Прямые соответствия
    if t in {"5K", "10K", "HM", "HALF_MARATHON", "MARATHON"}:
        if t == "HALF_MARATHON":
            return "HM"
        if t == "MARATHON":
            return "Marathon"
        return t

    # Триатлон-специфика: маппим по беговой части
    if t in {"SPRINT"}:
        return "5K"       # спринт → ~5K бег
    if t in {"OLYMPIC"}:
        return "10K"      # олимпийка → ~10K бег
    if t in {"HALF_IRONMAN", "HALF-IRONMAN", "70.3"}:
        return "HM"       # половинка → полу-марафон
    if t in {"IRONMAN", "FULL_IRONMAN", "140.6"}:
        return "Marathon" # полный → марафон

    # Fallback: если ничего не узнали, пусть будет набор базовых
    # (выше по коду будет обработано как prediction_failed,
    #  но хотя бы не рухнёт).
    return "10K"


def predict_for_goal(
    activities: List[dict],
    goal_race_type: str,
    goal_time: str,
    sport: str = "run",
    tsb: Optional[float] = None
) -> Dict[str, Any]:
    """
    Комплексный прогноз для конкретной цели.
    
    Args:
        activities: Активности из Strava
        goal_race_type: Тип гонки ("10K", "HM", "Marathon", etc.)
        goal_time: Целевое время (строка "H:MM:SS")
        sport: Вид спорта
        tsb: Training Stress Balance
    
    Returns:
        Полный отчёт с прогнозом и рекомендациями
    """
    # Парсим целевое время
    try:
        target_time_seconds = parse_target_time(goal_time)
    except ValueError as e:
        return {
            "error": str(e),
            "status": "invalid_target_time"
        }
    
    # Находим лучшие результаты
    best_efforts = find_best_efforts(activities, sport=sport)
    
    if not best_efforts:
        return {
            "error": "No race efforts found in activity history",
            "status": "no_data",
            "recommendation": "Complete some benchmark workouts (5K, 10K) to get predictions"
        }
    
    # Нормализуем тип гонки к одной из базовых дистанций
    normalized_race_type = normalize_goal_race_type(goal_race_type)

    # Прогнозируем времена
    predictions = predict_race_times(best_efforts, race_types=[normalized_race_type], tsb=tsb)
    
    if not predictions:
        return {
            "error": f"Unable to predict {goal_race_type}",
            "status": "prediction_failed"
        }
    
    prediction = predictions[0]
    
    # Рассчитываем вероятность успеха
    probability = calculate_success_probability(
        predicted_time_seconds=prediction.predicted_time_seconds,
        target_time_seconds=target_time_seconds,
        confidence=prediction.confidence
    )
    
    time_gap = prediction.predicted_time_seconds - target_time_seconds
    
    # Обновляем prediction
    prediction.target_time_seconds = target_time_seconds
    prediction.target_time_formatted = format_time(target_time_seconds)
    prediction.probability_of_success = probability
    prediction.time_gap_seconds = time_gap
    
    # Генерируем рекомендации
    recommendations = []
    
    if probability >= 70:
        recommendations.append("✅ Your goal is realistic based on current fitness!")
        recommendations.append("Continue with current training plan and focus on race-specific workouts.")
    elif probability >= 45:
        recommendations.append("⚠️ Your goal is challenging but achievable with focused training.")
        recommendations.append("Increase volume by 10-15% and add more tempo/threshold work.")
        
        # Рассчитываем нужное улучшение
        improvement_needed_percent = abs(time_gap / target_time_seconds) * 100
        recommendations.append(f"You need to improve by {improvement_needed_percent:.1f}% to hit your goal.")
    else:
        recommendations.append("🚨 Your goal is very ambitious and may not be realistic.")
        recommendations.append("Consider adjusting your target time or extending your training period.")
        
        # Предлагаем более реалистичную цель
        realistic_time = prediction.predicted_time_seconds * 1.02  # +2% buffer
        recommendations.append(f"A more realistic goal would be: {format_time(realistic_time)}")
    
    # Что нужно улучшить
    if time_gap > 0:  # Цель быстрее прогноза
        time_gap_minutes = time_gap / 60
        recommendations.append(f"\nTo reach your goal, you need to get {time_gap_minutes:.1f} minutes faster.")
        
        # Конкретные рекомендации по тренировкам
        if "5K" in best_efforts and goal_race_type in ["HM", "Marathon"]:
            recommendations.append("Focus on building aerobic base with long runs at easy pace.")
        elif "Marathon" in goal_race_type:
            recommendations.append("Add weekly long runs, gradually building to 30-35km.")
            recommendations.append("Include 2-3 tempo runs per week at threshold pace.")
    
    return {
        "status": "success",
        "goal": {
            "race_type": goal_race_type,
            "target_time": format_time(target_time_seconds)
        },
        "prediction": prediction.to_dict(),
        "best_efforts": {k: v.to_dict() for k, v in best_efforts.items()},
        "current_form": {
            "tsb": tsb,
            "form_status": "fresh" if tsb and tsb > 5 else ("fatigued" if tsb and tsb < -10 else "neutral")
        } if tsb is not None else None,
        "recommendations": recommendations
    }