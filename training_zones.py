"""
Автоматический расчёт тренировочных зон для бега, велосипеда и плавания.
Основано на лучших результатах (race efforts) из истории тренировок.
"""

import datetime as dt
from typing import Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class RunningZones:
    """Зоны для бега на основе threshold pace"""
    threshold_pace_per_km: float  # секунды на км (например, 260 для 4:20/km)
    
    z1_min: float  # Recovery - 130% threshold
    z1_max: float  # Recovery - 150% threshold
    
    z2_min: float  # Aerobic - 115% threshold
    z2_max: float  # Aerobic - 130% threshold
    
    z3_min: float  # Tempo - 105% threshold
    z3_max: float  # Tempo - 114% threshold
    
    z4_min: float  # Threshold - 98% threshold
    z4_max: float  # Threshold - 104% threshold
    
    z5_min: float  # VO2max - 90% threshold
    z5_max: float  # VO2max - 97% threshold
    
    def to_dict(self) -> Dict[str, Any]:
        """Конвертация в словарь для сохранения"""
        return {
            "threshold_pace_per_km_seconds": self.threshold_pace_per_km,
            "threshold_pace_per_km_formatted": format_pace(self.threshold_pace_per_km),
            "z1": {
                "min_pace": format_pace(self.z1_min),
                "max_pace": format_pace(self.z1_max),
                "description": "Recovery (very easy, conversational)"
            },
            "z2": {
                "min_pace": format_pace(self.z2_min),
                "max_pace": format_pace(self.z2_max),
                "description": "Aerobic base (easy, comfortable)"
            },
            "z3": {
                "min_pace": format_pace(self.z3_min),
                "max_pace": format_pace(self.z3_max),
                "description": "Tempo (comfortably hard, sustainable)"
            },
            "z4": {
                "min_pace": format_pace(self.z4_min),
                "max_pace": format_pace(self.z4_max),
                "description": "Threshold (hard but controlled)"
            },
            "z5": {
                "min_pace": format_pace(self.z5_min),
                "max_pace": format_pace(self.z5_max),
                "description": "VO2max (very hard, short intervals)"
            }
        }


@dataclass
class CyclingZones:
    """Зоны для велосипеда на основе FTP"""
    ftp_watts: float  # Functional Threshold Power в ваттах
    
    z1_min: float  # Active Recovery - 0% FTP
    z1_max: float  # Active Recovery - 55% FTP
    
    z2_min: float  # Endurance - 56% FTP
    z2_max: float  # Endurance - 75% FTP
    
    z3_min: float  # Tempo - 76% FTP
    z3_max: float  # Tempo - 90% FTP
    
    z4_min: float  # Threshold - 91% FTP
    z4_max: float  # Threshold - 105% FTP
    
    z5_min: float  # VO2max - 106% FTP
    z5_max: float  # VO2max - 120% FTP
    
    def to_dict(self) -> Dict[str, Any]:
        """Конвертация в словарь для сохранения"""
        return {
            "ftp_watts": int(self.ftp_watts),
            "z1": {
                "min_watts": int(self.z1_min),
                "max_watts": int(self.z1_max),
                "description": "Active recovery (very light)"
            },
            "z2": {
                "min_watts": int(self.z2_min),
                "max_watts": int(self.z2_max),
                "description": "Endurance (aerobic base)"
            },
            "z3": {
                "min_watts": int(self.z3_min),
                "max_watts": int(self.z3_max),
                "description": "Tempo / Sweet Spot (race intensity)"
            },
            "z4": {
                "min_watts": int(self.z4_min),
                "max_watts": int(self.z4_max),
                "description": "Threshold (1-hour TT effort)"
            },
            "z5": {
                "min_watts": int(self.z5_min),
                "max_watts": int(self.z5_max),
                "description": "VO2max (hard intervals)"
            }
        }


@dataclass
class SwimmingZones:
    """Зоны для плавания на основе CSS (Critical Swim Speed)"""
    css_pace_per_100m: float  # секунды на 100м
    
    z1_pace: float  # Easy technique
    z2_pace: float  # Aerobic endurance
    z3_pace: float  # CSS pace (race pace for 70.3)
    z4_pace: float  # Threshold (faster than CSS)
    z5_pace: float  # Sprint pace
    
    def to_dict(self) -> Dict[str, Any]:
        """Конвертация в словарь для сохранения"""
        return {
            "css_pace_per_100m_seconds": self.css_pace_per_100m,
            "css_pace_formatted": format_swim_pace(self.css_pace_per_100m),
            "z1": {
                "pace": format_swim_pace(self.z1_pace),
                "description": "Easy technique work"
            },
            "z2": {
                "pace": format_swim_pace(self.z2_pace),
                "description": "Aerobic endurance"
            },
            "z3": {
                "pace": format_swim_pace(self.z3_pace),
                "description": "CSS / Race pace"
            },
            "z4": {
                "pace": format_swim_pace(self.z4_pace),
                "description": "Threshold intervals"
            },
            "z5": {
                "pace": format_swim_pace(self.z5_pace),
                "description": "Sprint pace"
            }
        }


# ===== UTILITY FUNCTIONS =====

def format_pace(seconds_per_km: float) -> str:
    """Форматирует темп в мин:сек/км"""
    minutes = int(seconds_per_km // 60)
    seconds = int(seconds_per_km % 60)
    return f"{minutes}:{seconds:02d}/km"


def format_swim_pace(seconds_per_100m: float) -> str:
    """Форматирует темп плавания в мин:сек/100м"""
    minutes = int(seconds_per_100m // 60)
    seconds = int(seconds_per_100m % 60)
    return f"{minutes}:{seconds:02d}/100m"


def parse_pace(pace_str: str) -> float:
    """Парсит темп из строки '4:20/km' в секунды на км"""
    try:
        parts = pace_str.replace("/km", "").strip().split(":")
        minutes = int(parts[0])
        seconds = int(parts[1])
        return minutes * 60 + seconds
    except:
        return 0.0


# ===== ZONE CALCULATION FUNCTIONS =====

def calculate_running_zones_from_race(
    distance_km: float,
    time_seconds: float,
    race_type: str = "10K"
) -> RunningZones:
    """
    Рассчитывает зоны бега на основе результата гонки.
    
    Args:
        distance_km: Дистанция гонки в км (например, 10.0 для 10K)
        time_seconds: Время в секундах
        race_type: Тип гонки ("5K", "10K", "HM", "Marathon")
    
    Returns:
        RunningZones с рассчитанными зонами
    """
    # Рассчитываем темп гонки (секунды на км)
    race_pace = time_seconds / distance_km
    
    # Определяем threshold pace в зависимости от дистанции
    if race_type == "5K":
        # 5K ~ VO2max (Z5), threshold примерно на 5-7% медленнее
        threshold_pace = race_pace * 1.06
    elif race_type == "10K":
        # 10K ~ threshold pace (Z4)
        threshold_pace = race_pace
    elif race_type == "HM":
        # Half Marathon ~ 95% threshold
        threshold_pace = race_pace / 0.95
    elif race_type == "Marathon":
        # Marathon ~ 90% threshold
        threshold_pace = race_pace / 0.90
    else:
        # По умолчанию считаем что это 10K
        threshold_pace = race_pace
    
    # Рассчитываем зоны
    return RunningZones(
        threshold_pace_per_km=threshold_pace,
        z1_min=threshold_pace * 1.30,
        z1_max=threshold_pace * 1.50,
        z2_min=threshold_pace * 1.15,
        z2_max=threshold_pace * 1.30,
        z3_min=threshold_pace * 1.05,
        z3_max=threshold_pace * 1.14,
        z4_min=threshold_pace * 0.98,
        z4_max=threshold_pace * 1.04,
        z5_min=threshold_pace * 0.90,
        z5_max=threshold_pace * 0.97
    )


def calculate_cycling_zones_from_ftp(ftp_watts: float) -> CyclingZones:
    """
    Рассчитывает зоны велосипеда на основе FTP.
    
    Args:
        ftp_watts: FTP в ваттах (1-hour max power)
    
    Returns:
        CyclingZones с рассчитанными зонами
    """
    return CyclingZones(
        ftp_watts=ftp_watts,
        z1_min=0,
        z1_max=ftp_watts * 0.55,
        z2_min=ftp_watts * 0.56,
        z2_max=ftp_watts * 0.75,
        z3_min=ftp_watts * 0.76,
        z3_max=ftp_watts * 0.90,
        z4_min=ftp_watts * 0.91,
        z4_max=ftp_watts * 1.05,
        z5_min=ftp_watts * 1.06,
        z5_max=ftp_watts * 1.20
    )


def estimate_ftp_from_race(
    distance_km: float,
    time_seconds: float,
    race_type: str = "40K_TT"
) -> float:
    """
    Оценивает FTP на основе результата гонки на велосипеде.
    
    Args:
        distance_km: Дистанция в км
        time_seconds: Время в секундах
        race_type: Тип гонки ("20K_TT", "40K_TT", "70.3_bike", "IM_bike")
    
    Returns:
        Оценка FTP в ваттах
    """
    # Рассчитываем среднюю скорость (км/ч)
    speed_kmh = (distance_km / time_seconds) * 3600
    
    # Очень грубая оценка мощности из скорости
    # Для 70-75kg райдера на шоссейном велосипеде на ровной дороге
    # Примерно: 30 km/h ~ 150W, 35 km/h ~ 200W, 40 km/h ~ 270W
    # Формула: W ≈ 0.5 * v^2 + 50 (очень грубо!)
    estimated_avg_power = 0.5 * (speed_kmh ** 2) + 50
    
    # Корректируем на тип гонки
    if race_type == "20K_TT":
        # 20K TT ~ 105% FTP
        ftp = estimated_avg_power / 1.05
    elif race_type == "40K_TT":
        # 40K TT ~ 100% FTP (1 hour effort)
        ftp = estimated_avg_power
    elif race_type == "70.3_bike":
        # 70.3 bike (90km) ~ 75% FTP
        ftp = estimated_avg_power / 0.75
    elif race_type == "IM_bike":
        # IM bike (180km) ~ 70% FTP
        ftp = estimated_avg_power / 0.70
    else:
        ftp = estimated_avg_power
    
    return ftp


def calculate_swimming_zones_from_css(css_pace_per_100m: float) -> SwimmingZones:
    """
    Рассчитывает зоны плавания на основе CSS (Critical Swim Speed).
    
    Args:
        css_pace_per_100m: CSS pace в секундах на 100м
    
    Returns:
        SwimmingZones с рассчитанными зонами
    """
    return SwimmingZones(
        css_pace_per_100m=css_pace_per_100m,
        z1_pace=css_pace_per_100m * 1.20,  # Easy - на 20% медленнее CSS
        z2_pace=css_pace_per_100m * 1.10,  # Aerobic - на 10% медленнее CSS
        z3_pace=css_pace_per_100m,         # CSS - race pace
        z4_pace=css_pace_per_100m * 0.95,  # Threshold - на 5% быстрее CSS
        z5_pace=css_pace_per_100m * 0.85   # Sprint - на 15% быстрее CSS
    )


def estimate_css_from_swim(distance_m: float, time_seconds: float) -> float:
    """
    Оценивает CSS на основе результата заплыва.
    
    Args:
        distance_m: Дистанция в метрах
        time_seconds: Время в секундах
    
    Returns:
        CSS pace в секундах на 100м
    """
    # Рассчитываем темп на 100м
    pace_per_100m = (time_seconds / distance_m) * 100
    
    # Корректируем в зависимости от дистанции
    # CSS обычно близок к темпу 1500-2000м
    if distance_m < 800:
        # Короткая дистанция - быстрее CSS
        css = pace_per_100m * 1.05
    elif distance_m > 3000:
        # Длинная дистанция - медленнее CSS
        css = pace_per_100m * 0.98
    else:
        # Средняя дистанция ~ CSS
        css = pace_per_100m
    
    return css


# ===== AUTO-DETECTION FROM ACTIVITIES =====

def find_best_race_efforts(activities: list[dict]) -> Dict[str, Any]:
    """
    Ищет лучшие результаты (race efforts) в истории тренировок.
    
    Args:
        activities: Список активностей из Strava
    
    Returns:
        Словарь с лучшими результатами:
        {
            "run_5k": {"distance_km": 5.0, "time_seconds": 1200, "date": "2025-10-15"},
            "run_10k": {...},
            "bike_40k": {...},
            "swim_1500m": {...}
        }
    """
    from utils import normalize_sport
    
    best_efforts = {}
    
    for activity in activities:
        sport = normalize_sport(activity.get("sport_type"))
        distance = activity.get("distance", 0)  # в метрах
        time = activity.get("moving_time") or activity.get("moving_time_s") or 0
        date = activity.get("start_date", "")[:10]
        
        if not distance or not time:
            continue
        
        distance_km = distance / 1000
        
        # Бег
        if sport == "run":
            # 5K
            if 4.5 <= distance_km <= 5.5:
                key = "run_5k"
                if key not in best_efforts or time < best_efforts[key]["time_seconds"]:
                    best_efforts[key] = {
                        "distance_km": distance_km,
                        "time_seconds": time,
                        "date": date,
                        "pace_per_km": format_pace(time / distance_km)
                    }
            
            # 10K
            if 9.5 <= distance_km <= 10.5:
                key = "run_10k"
                if key not in best_efforts or time < best_efforts[key]["time_seconds"]:
                    best_efforts[key] = {
                        "distance_km": distance_km,
                        "time_seconds": time,
                        "date": date,
                        "pace_per_km": format_pace(time / distance_km)
                    }
            
            # Half Marathon
            if 20 <= distance_km <= 22:
                key = "run_hm"
                if key not in best_efforts or time < best_efforts[key]["time_seconds"]:
                    best_efforts[key] = {
                        "distance_km": distance_km,
                        "time_seconds": time,
                        "date": date,
                        "pace_per_km": format_pace(time / distance_km)
                    }
            
            # Marathon
            if 41 <= distance_km <= 43:
                key = "run_marathon"
                if key not in best_efforts or time < best_efforts[key]["time_seconds"]:
                    best_efforts[key] = {
                        "distance_km": distance_km,
                        "time_seconds": time,
                        "date": date,
                        "pace_per_km": format_pace(time / distance_km)
                    }
        
        # Велосипед
        elif sport == "bike":
            # 40K TT
            if 35 <= distance_km <= 45:
                key = "bike_40k"
                if key not in best_efforts or time < best_efforts[key]["time_seconds"]:
                    best_efforts[key] = {
                        "distance_km": distance_km,
                        "time_seconds": time,
                        "date": date,
                        "avg_speed_kmh": round((distance_km / time) * 3600, 1)
                    }
            
            # 70.3 bike (90km)
            if 85 <= distance_km <= 95:
                key = "bike_70_3"
                if key not in best_efforts or time < best_efforts[key]["time_seconds"]:
                    best_efforts[key] = {
                        "distance_km": distance_km,
                        "time_seconds": time,
                        "date": date,
                        "avg_speed_kmh": round((distance_km / time) * 3600, 1)
                    }
        
        # Плавание
        elif sport == "swim":
            distance_m = distance  # уже в метрах
            
            # 1500m
            if 1400 <= distance_m <= 1600:
                key = "swim_1500m"
                if key not in best_efforts or time < best_efforts[key]["time_seconds"]:
                    best_efforts[key] = {
                        "distance_m": distance_m,
                        "time_seconds": time,
                        "date": date,
                        "pace_per_100m": format_swim_pace((time / distance_m) * 100)
                    }
    
    return best_efforts