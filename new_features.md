# Идеи новых фич для AI Триатлон Тренера

## 1. АВТОМАТИЧЕСКИЙ РАСЧЁТ ЗОН ТРЕНИРОВКИ

### Концепция
Вместо ручного ввода зон, система автоматически вычисляет персональные зоны на основе:
- Race efforts (гонки и time trials)
- Testing workouts (20-min FTP test, 5K time trial)
- HR data анализ

### Реализация

```python
# zones.py

from typing import Dict, Optional
from pydantic import BaseModel
import statistics


class TrainingZones(BaseModel):
    """Персональные зоны тренировки"""
    
    # Running zones (pace in seconds per km)
    run_z1_pace_max: Optional[float] = None  # recovery
    run_z2_pace_min: Optional[float] = None  # aerobic
    run_z2_pace_max: Optional[float] = None
    run_z3_pace_min: Optional[float] = None  # tempo
    run_z3_pace_max: Optional[float] = None
    run_z4_pace_min: Optional[float] = None  # threshold
    run_z4_pace_max: Optional[float] = None
    run_z5_pace_max: Optional[float] = None  # VO2max
    
    # Cycling zones (watts)
    bike_ftp: Optional[float] = None
    bike_z1_watts_max: Optional[float] = None
    bike_z2_watts_min: Optional[float] = None
    bike_z2_watts_max: Optional[float] = None
    # ... etc
    
    # HR zones (bpm)
    max_hr: Optional[int] = None
    hr_z1_max: Optional[int] = None
    hr_z2_min: Optional[int] = None
    hr_z2_max: Optional[int] = None
    # ... etc


def estimate_threshold_pace_from_race(
    distance_km: float,
    time_seconds: int
) -> float:
    """
    Оценка threshold pace на основе race effort.
    
    Args:
        distance_km: дистанция гонки (5, 10, 21.1, 42.2)
        time_seconds: время финиша
    
    Returns:
        threshold pace в сек/км (примерно 10K-HM race pace)
    """
    pace_sec_per_km = time_seconds / distance_km
    
    # Корректировка на дистанцию
    # Чем короче дистанция, тем быстрее относительно threshold
    if distance_km <= 5:
        # 5K обычно на ~105% threshold pace
        threshold_pace = pace_sec_per_km * 1.05
    elif distance_km <= 10:
        # 10K примерно равен threshold
        threshold_pace = pace_sec_per_km
    elif distance_km <= 21.1:
        # HM обычно на ~95% threshold
        threshold_pace = pace_sec_per_km * 0.95
    else:
        # Marathon на ~90% threshold
        threshold_pace = pace_sec_per_km * 0.90
    
    return threshold_pace


def calculate_running_zones(threshold_pace_sec_per_km: float) -> Dict[str, tuple]:
    """
    Рассчитывает зоны бега на основе threshold pace.
    
    Returns:
        dict с зонами: {"Z1": (min, max), "Z2": (min, max), ...}
    """
    z1 = (threshold_pace_sec_per_km * 1.30, float('inf'))  # slower than 130%
    z2 = (threshold_pace_sec_per_km * 1.15, threshold_pace_sec_per_km * 1.30)
    z3 = (threshold_pace_sec_per_km * 1.05, threshold_pace_sec_per_km * 1.15)
    z4 = (threshold_pace_sec_per_km * 0.98, threshold_pace_sec_per_km * 1.04)
    z5 = (0, threshold_pace_sec_per_km * 0.98)
    
    return {"Z1": z1, "Z2": z2, "Z3": z3, "Z4": z4, "Z5": z5}


async def auto_calculate_zones(user_id: int, db: Session) -> TrainingZones:
    """
    Автоматически вычисляет зоны на основе истории тренировок.
    
    1. Ищет race efforts или hard workouts
    2. Оценивает threshold pace
    3. Вычисляет все зоны
    """
    # Получаем последние race efforts
    # (активности с высокой интенсивностью и дистанциями 5K, 10K, HM)
    activities = db.query(Activity)\
        .filter(Activity.user_id == user_id)\
        .filter(Activity.sport_type.in_(["Run", "Race"]))\
        .filter(Activity.distance_m.between(4000, 25000))\
        .order_by(Activity.start_date.desc())\
        .limit(10)\
        .all()
    
    if not activities:
        # Нет данных — возвращаем дефолтные зоны
        return TrainingZones()
    
    # Находим лучшие efforts
    threshold_estimates = []
    for act in activities:
        if act.distance_m and act.moving_time_s:
            distance_km = act.distance_m / 1000
            threshold = estimate_threshold_pace_from_race(
                distance_km,
                act.moving_time_s
            )
            threshold_estimates.append(threshold)
    
    if not threshold_estimates:
        return TrainingZones()
    
    # Берём медиану (устойчивее к outliers)
    threshold_pace = statistics.median(threshold_estimates)
    
    # Вычисляем зоны
    zones_dict = calculate_running_zones(threshold_pace)
    
    # Заполняем модель
    return TrainingZones(
        run_z2_pace_min=zones_dict["Z2"][0],
        run_z2_pace_max=zones_dict["Z2"][1],
        run_z3_pace_min=zones_dict["Z3"][0],
        run_z3_pace_max=zones_dict["Z3"][1],
        run_z4_pace_min=zones_dict["Z4"][0],
        run_z4_pace_max=zones_dict["Z4"][1],
        # ... и т.д.
    )


# API endpoint
@app.post("/coach/zones/auto_calculate")
async def calculate_training_zones(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Автоматически вычисляет персональные зоны тренировки.
    """
    zones = await auto_calculate_zones(current_user.id, db)
    
    # Сохраняем в профиль пользователя
    current_user.training_zones_json = zones.model_dump()
    db.commit()
    
    return {
        "message": "Training zones calculated successfully",
        "zones": zones,
        "recommendations": [
            f"Your estimated threshold pace: {format_pace(zones.run_z4_pace_min)}",
            f"Easy runs should be slower than {format_pace(zones.run_z2_pace_max)}",
            f"Tempo runs: {format_pace(zones.run_z3_pace_min)} - {format_pace(zones.run_z3_pace_max)}"
        ]
    }


def format_pace(seconds_per_km: float) -> str:
    """Format pace as MM:SS/km"""
    minutes = int(seconds_per_km // 60)
    seconds = int(seconds_per_km % 60)
    return f"{minutes}:{seconds:02d}/km"
```

---

## 2. RACE DAY STRATEGY GENERATOR

### Концепция
За 1-2 недели до гонки, система генерирует детальную стратегию:
- Pacing plan (каждые 5-10 км)
- Nutrition timeline (когда пить/есть)
- Mental cues (что думать на каждом этапе)
- Transition checklist

### Пример промпта для GPT

```python
# race_strategy.py

RACE_STRATEGY_PROMPT = """You are RACE STRATEGY SPECIALIST for triathlon.

Based on the athlete's profile and training history, create a DETAILED race-day 
execution plan for their upcoming race.

## INPUTS
- Goal time: {goal_time}
- Race type: {race_type} (e.g., Half Ironman 70.3)
- Race date: {race_date}
- Course profile: {course_profile} (flat, hilly, hot conditions, etc.)
- Athlete's current fitness: {fitness_summary}
- Recent training paces/power: {recent_efforts}

## YOUR TASK

Generate a JSON object with this structure:

{{
  "swim_plan": {{
    "target_time": "30-32 minutes",
    "strategy": [
      "Start in the back-middle to avoid chaos",
      "First 400m: settle into rhythm, don't go out too hard",
      "Focus on long, smooth strokes",
      "Exit strategy: stay calm, don't rush"
    ],
    "nutrition": "No nutrition needed, but take a few sips of water before start"
  }},
  
  "t1_plan": {{
    "target_time": "3 minutes",
    "checklist": [
      "Remove wetsuit quickly but calmly",
      "Put on cycling shoes (already clipped to pedals)",
      "Grab helmet, sunglasses, nutrition",
      "Run to bike (don't mount until after mount line)"
    ]
  }},
  
  "bike_plan": {{
    "target_time": "2:20-2:25 (38-39 km/h avg)",
    "power_strategy": [
      {{
        "segment": "0-20 km",
        "power_watts": "200-220W (70-75% FTP)",
        "hr_target": "135-145 bpm",
        "notes": "Start conservative, find your rhythm, practice aero position"
      }},
      {{
        "segment": "20-60 km",
        "power_watts": "220-240W (75-80% FTP)",
        "hr_target": "145-155 bpm",
        "notes": "Main work segment. Stay steady, don't chase people"
      }},
      {{
        "segment": "60-80 km",
        "power_watts": "210-230W (70-75% FTP)",
        "hr_target": "140-150 bpm",
        "notes": "Prepare for run. Slightly back off if feeling fatigued"
      }},
      {{
        "segment": "80-90 km (final)",
        "power_watts": "190-210W (65-70% FTP)",
        "hr_target": "135-145 bpm",
        "notes": "Final 10K: soft-pedal, open up legs for run"
      }}
    ],
    "nutrition": [
      "Bottle 1 (750ml): electrolytes, start sipping immediately",
      "0:30 - First gel + water",
      "1:00 - Banana or bar + electrolytes",
      "1:30 - Gel + water",
      "2:00 - Last gel + water",
      "Target: 60-80g carbs per hour, 500-750ml fluids per hour"
    ],
    "mental_cues": [
      "First 20K: 'Stay patient, trust the plan'",
      "Middle 40K: 'I'm strong, steady wins'",
      "Last 30K: 'Save the legs for the run'"
    ]
  }},
  
  "t2_plan": {{
    "target_time": "2 minutes",
    "checklist": [
      "Rack bike carefully",
      "Remove helmet, cycling shoes",
      "Put on running shoes (elastic laces)",
      "Grab race belt with number, visor/hat",
      "Take a gel or two for run course"
    ]
  }},
  
  "run_plan": {{
    "target_time": "1:28-1:32 (4:10-4:20/km)",
    "pace_strategy": [
      {{
        "segment": "0-5 km",
        "pace": "4:35-4:45/km (EASY)",
        "hr_target": "150-160 bpm",
        "notes": "Legs will feel heavy off bike - that's normal. Find your run rhythm."
      }},
      {{
        "segment": "5-10 km",
        "pace": "4:20-4:30/km",
        "hr_target": "155-165 bpm",
        "notes": "Settle into race pace. If feeling good, move to target pace."
      }},
      {{
        "segment": "10-15 km",
        "pace": "4:15-4:25/km",
        "hr_target": "160-168 bpm",
        "notes": "Main work segment. Stay focused, don't drift."
      }},
      {{
        "segment": "15-20 km",
        "pace": "4:15-4:30/km",
        "hr_target": "158-170 bpm",
        "notes": "Pain cave starts. Mental toughness time. 'One step at a time.'"
      }},
      {{
        "segment": "20-21.1 km (final)",
        "pace": "4:00-4:20/km (whatever you have left)",
        "hr_target": "165-MAX",
        "notes": "Leave it all out there. You trained for this!"
      }}
    ],
    "nutrition": [
      "Water at every aid station (small sips)",
      "Gel at 7K, 14K, 18K (if needed)",
      "Electrolytes if hot conditions",
      "Coke in last 5K for caffeine boost"
    ],
    "mental_strategy": [
      "Break run into 5K segments",
      "Focus on form: tall posture, quick cadence",
      "When it hurts: 'I trained for this. I'm ready.'",
      "Count down km markers",
      "Final km: 'This is my race. Finish strong.'"
    ]
  }},
  
  "overall_tips": [
    "Nothing new on race day - stick to what worked in training",
    "Weather check night before - adjust clothing/nutrition plan",
    "Visualize the race the night before and morning of",
    "Warm up: 5min easy jog, dynamic stretches, practice transitions",
    "Start conservatively - you can always speed up, hard to slow down",
    "Trust your training - you've done the work"
  ],
  
  "contingency_plans": {{
    "if_too_hot": "Slow down bike by 5-10W, take extra water, pour water on head",
    "if_feeling_bad_on_bike": "Soft-pedal for 10min, take gel+water, reassess. Don't panic.",
    "if_cramping_on_run": "Walk through aid station, stretch, electrolytes, slow pace 30s",
    "if_ahead_of_pace": "Don't celebrate early. Stay disciplined. Save push for final 5K."
  }}
}}

Remember:
- Pacing is CRITICAL in triathlon - going out too hard ruins the run
- Nutrition can make or break the race - practice it
- Mental strength matters as much as physical fitness
- The run is where races are won or lost - save something for it

Return ONLY valid JSON, no other text.
"""


async def generate_race_strategy(
    goal: GoalInput,
    athlete_profile: AthleteProfile,
    recent_training: dict
) -> dict:
    """
    Генерирует детальную стратегию на день гонки.
    """
    
    prompt = RACE_STRATEGY_PROMPT.format(
        goal_time=goal.main_goal_target_time,
        race_type=goal.main_goal_type,
        race_date=goal.main_goal_race_date,
        course_profile="Assume flat course",  # TODO: добавить ввод курса
        fitness_summary=recent_training.get("summary"),
        recent_efforts=recent_training.get("best_efforts")
    )
    
    completion = openai_client.chat.completions.create(
        model=GPT_MODEL,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": prompt},
            {
                "role": "user",
                "content": f"Generate race strategy based on: {json.dumps(athlete_profile.model_dump())}"
            }
        ],
        temperature=0.2
    )
    
    strategy = json.loads(completion.choices[0].message.content)
    return strategy


# API endpoint
@app.post("/coach/race_strategy")
async def create_race_strategy(
    goal: GoalInput,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Генерирует детальную стратегию на день гонки.
    Должен вызываться за 1-2 недели до гонки.
    """
    profile = load_athlete_profile()
    activities = await fetch_activities_last_n_weeks(weeks=12)
    
    # Собираем статистику по лучшим efforts
    recent_training = {
        "summary": f"Last 12 weeks avg: {calculate_avg_hours(activities)} h/week",
        "best_efforts": get_best_efforts(activities)
    }
    
    strategy = await generate_race_strategy(goal, profile, recent_training)
    
    # Сохраняем стратегию в БД
    # ... save to RaceStrategy table ...
    
    return strategy
```

---

## 3. SMART FATIGUE DETECTION

### Концепция
Анализирует признаки перетренированности и автоматически корректирует план:
- HR drift (HR растёт на том же пейсе)
- Pace decline (пейс падает при той же мощности)
- Missed workouts pattern
- Self-reported fatigue scores

### Реализация

```python
# fatigue_detection.py

from typing import List, Optional
from pydantic import BaseModel


class FatigueIndicators(BaseModel):
    hr_drift_score: float  # 0-100, где 100 = сильный drift
    pace_decline_score: float
    missed_workouts_score: float
    subjective_fatigue_score: Optional[float] = None  # из ручного ввода
    overall_fatigue: float  # 0-100


class FatigueRecommendation(BaseModel):
    severity: str  # "low" | "moderate" | "high" | "critical"
    action: str  # "continue" | "easy_week" | "rest_3days" | "see_doctor"
    explanation: str
    plan_adjustments: List[str]


def calculate_hr_drift(activities: List[dict]) -> float:
    """
    Анализирует HR drift: если HR растёт на одном и том же пейсе,
    это признак усталости.
    
    Returns:
        score 0-100 (0 = нет drift, 100 = сильный drift)
    """
    # Фильтруем только "easy" тренировки (Z2)
    easy_runs = [
        act for act in activities
        if act.get("sport_type") == "Run"
        and act.get("average_heartrate")
        and act.get("average_speed_m_s")
        and act.get("moving_time_s", 0) > 1800  # минимум 30 минут
    ]
    
    if len(easy_runs) < 5:
        return 0.0  # Недостаточно данных
    
    # Сортируем по дате
    easy_runs.sort(key=lambda x: x["start_date"])
    
    # Берём последние 10
    recent = easy_runs[-10:]
    
    # Вычисляем среднюю скорость и средний HR для каждой
    pace_hr_pairs = []
    for run in recent:
        pace_sec_per_km = 1000 / run["average_speed_m_s"]  # sec/km
        hr = run["average_heartrate"]
        pace_hr_pairs.append((pace_sec_per_km, hr))
    
    # Если последние 3 тренировки показывают HR выше среднего
    # при том же пейсе — это drift
    avg_pace = sum(p[0] for p in pace_hr_pairs) / len(pace_hr_pairs)
    avg_hr = sum(p[1] for p in pace_hr_pairs) / len(pace_hr_pairs)
    
    last_3 = pace_hr_pairs[-3:]
    last_3_hr = sum(p[1] for p in last_3) / 3
    
    hr_increase = last_3_hr - avg_hr
    
    # Скор: если HR вырос на 10+ bpm — это проблема
    score = min(100, max(0, (hr_increase / 10.0) * 100))
    
    return score


def calculate_pace_decline(activities: List[dict]) -> float:
    """
    Анализирует падение пейса на одной и той же мощности/HR.
    """
    # Похожая логика как для HR drift
    # ... implementation ...
    return 0.0  # placeholder


def calculate_missed_workouts_score(
    planned_sessions: int,
    completed_sessions: int
) -> float:
    """
    Процент пропущенных тренировок за последние 2 недели.
    """
    if planned_sessions == 0:
        return 0.0
    
    missed = planned_sessions - completed_sessions
    missed_pct = (missed / planned_sessions) * 100
    
    # Если пропущено >30% — это проблема
    score = min(100, missed_pct * 3)
    return score


async def detect_fatigue(
    user_id: int,
    db: Session
) -> tuple[FatigueIndicators, FatigueRecommendation]:
    """
    Анализирует все признаки усталости и даёт рекомендации.
    """
    # Получаем последние 20 тренировок
    activities = db.query(Activity)\
        .filter(Activity.user_id == user_id)\
        .order_by(Activity.start_date.desc())\
        .limit(20)\
        .all()
    
    activities_dict = [act.__dict__ for act in activities]
    
    # Вычисляем индикаторы
    hr_drift = calculate_hr_drift(activities_dict)
    pace_decline = calculate_pace_decline(activities_dict)
    
    # Получаем план vs факт за последние 2 недели
    # ... query planned vs actual ...
    missed_score = calculate_missed_workouts_score(14, 10)  # example
    
    # Субъективная оценка (если есть)
    subjective = None  # TODO: добавить ручной ввод в мобильном приложении
    
    # Общий скор (взвешенная сумма)
    overall = (
        hr_drift * 0.4 +
        pace_decline * 0.3 +
        missed_score * 0.2 +
        (subjective or 0) * 0.1
    )
    
    indicators = FatigueIndicators(
        hr_drift_score=hr_drift,
        pace_decline_score=pace_decline,
        missed_workouts_score=missed_score,
        subjective_fatigue_score=subjective,
        overall_fatigue=overall
    )
    
    # Определяем рекомендацию
    if overall < 20:
        severity = "low"
        action = "continue"
        explanation = "Your training is going well. Continue as planned."
        adjustments = []
    elif overall < 40:
        severity = "moderate"
        action = "easy_week"
        explanation = "Showing early signs of fatigue. Let's take an easy week."
        adjustments = [
            "Reduce volume by 30% this week",
            "Cancel 1 hard session",
            "Focus on sleep and recovery"
        ]
    elif overall < 70:
        severity = "high"
        action = "rest_3days"
        explanation = "Significant fatigue detected. Take 3 days complete rest."
        adjustments = [
            "No training for 3 days",
            "Easy week after rest (50% volume)",
            "Monitor HR on first run back"
        ]
    else:
        severity = "critical"
        action = "see_doctor"
        explanation = "Critical fatigue or possible overtraining. Consult a doctor."
        adjustments = [
            "Stop training immediately",
            "See sports medicine doctor",
            "Check for illness, anemia, etc."
        ]
    
    recommendation = FatigueRecommendation(
        severity=severity,
        action=action,
        explanation=explanation,
        plan_adjustments=adjustments
    )
    
    return indicators, recommendation


# API endpoint
@app.get("/coach/fatigue_check")
async def check_fatigue(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Проверяет признаки перетренированности и даёт рекомендации.
    """
    indicators, recommendation = await detect_fatigue(current_user.id, db)
    
    return {
        "indicators": indicators,
        "recommendation": recommendation,
        "message": recommendation.explanation
    }
```

---

## 4. WORKOUT LIBRARY С ФИЛЬТРАЦИЕЙ

### Концепция
База данных готовых тренировок с тегами, которые можно:
- Фильтровать по виду спорта, сложности, целям
- Добавлять в план одним кликом
- Редактировать под себя

### Реализация

```python
# workout_library.py

WORKOUT_LIBRARY = [
    {
        "id": "run_threshold_1",
        "name": "Classic Threshold Intervals",
        "sport": "run",
        "type": "threshold",
        "duration_min": 75,
        "difficulty": "hard",
        "description": "Warm-up 15min easy, 3x10min @ threshold pace (Z4) with 3min jog recovery, cool-down 10min",
        "primary_goal": "Improve lactate threshold for race pace",
        "intensity": "Z4 (4:15-4:25/km for 4:30 70.3 athlete)",
        "equipment": ["GPS watch"],
        "tags": ["intervals", "speed", "advanced", "70.3_specific"],
        "notes": "Target HR 165-172 bpm during intervals. If HR >175, slow down.",
        "variations": [
            "Beginner: 3x8min @ Z4",
            "Advanced: 4x10min @ Z4",
            "Elite: 5x10min @ Z4"
        ]
    },
    {
        "id": "bike_sweet_spot_1",
        "name": "Sweet Spot Intervals",
        "sport": "bike",
        "type": "sweet_spot",
        "duration_min": 90,
        "difficulty": "medium_hard",
        "description": "Warm-up 20min easy, 3x20min @ 88-93% FTP with 5min easy spin between, cool-down 10min",
        "primary_goal": "Build sustainable power at race intensity",
        "intensity": "Z3 (88-93% FTP)",
        "equipment": ["Power meter or smart trainer"],
        "tags": ["intervals", "endurance", "70.3_specific", "indoor_friendly"],
        "notes": "Focus on staying aero. Practice race nutrition.",
        "variations": [
            "Beginner: 3x15min @ 85-90% FTP",
            "Advanced: 4x20min @ 88-93% FTP",
            "Elite: 3x30min @ 90-95% FTP"
        ]
    },
    {
        "id": "brick_race_sim_1",
        "name": "Race Simulation Brick",
        "sport": "brick",
        "type": "race_specific",
        "duration_min": 180,
        "difficulty": "very_hard",
        "description": "Bike: 2h @ 70-75% FTP (race effort), immediately followed by Run: 45min @ 70.3 race pace (Z3)",
        "primary_goal": "Practice running off the bike at race effort",
        "intensity": "Bike Z2-Z3, Run Z3",
        "equipment": ["Bike with power meter", "GPS watch", "race nutrition"],
        "tags": ["brick", "race_specific", "advanced", "key_workout"],
        "notes": "THIS IS A KEY SESSION. Practice everything: nutrition, pacing, mental focus. Simulate race conditions.",
        "variations": [
            "Beginner: 90min bike + 30min run",
            "Advanced: 2.5h bike + 60min run",
            "Elite: 3h bike + 75min run"
        ]
    },
    {
        "id": "swim_technique_1",
        "name": "Technique Focus Session",
        "sport": "swim",
        "type": "technique",
        "duration_min": 60,
        "difficulty": "easy",
        "description": """
        Warm-up: 400m easy
        Drills (200m): 4x50m (catch-up drill, fingertip drag)
        Main set: 8x100m @ Z2 with 15s rest (focus on high elbow catch)
        Cool-down: 200m easy
        Total: 2000m
        """,
        "primary_goal": "Improve swim efficiency and technique",
        "intensity": "Z1-Z2 (easy to moderate)",
        "equipment": ["Pull buoy optional"],
        "tags": ["technique", "drills", "beginner_friendly", "efficiency"],
        "notes": "Quality over quantity. Focus on feeling the water.",
        "variations": [
            "Beginner: 1500m total",
            "Advanced: 2500m total",
            "Elite: 3000m with band pulls"
        ]
    }
]


@app.get("/workouts")
async def get_workouts(
    sport: Optional[str] = None,
    difficulty: Optional[str] = None,
    tags: Optional[str] = None,  # comma-separated
    duration_min_min: Optional[int] = None,
    duration_min_max: Optional[int] = None
):
    """
    Фильтрация тренировок из библиотеки.
    
    Example:
        GET /workouts?sport=run&difficulty=hard&tags=intervals,70.3_specific
    """
    workouts = WORKOUT_LIBRARY
    
    # Фильтрация по спорту
    if sport:
        workouts = [w for w in workouts if w["sport"] == sport]
    
    # Фильтрация по сложности
    if difficulty:
        workouts = [w for w in workouts if w["difficulty"] == difficulty]
    
    # Фильтрация по тегам
    if tags:
        tag_list = tags.split(",")
        workouts = [
            w for w in workouts
            if any(tag in w["tags"] for tag in tag_list)
        ]
    
    # Фильтрация по длительности
    if duration_min_min:
        workouts = [w for w in workouts if w["duration_min"] >= duration_min_min]
    if duration_min_max:
        workouts = [w for w in workouts if w["duration_min"] <= duration_min_max]
    
    return {
        "count": len(workouts),
        "workouts": workouts
    }


@app.post("/coach/plan/add_workout")
async def add_workout_to_plan(
    week_start_date: str,
    date: str,
    workout_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Добавляет готовую тренировку из библиотеки в план.
    """
    # Находим тренировку
    workout = next((w for w in WORKOUT_LIBRARY if w["id"] == workout_id), None)
    if not workout:
        raise HTTPException(status_code=404, detail="Workout not found")
    
    # Загружаем план недели
    plan = db.query(WeeklyPlan)\
        .filter(WeeklyPlan.user_id == current_user.id)\
        .filter(WeeklyPlan.week_start_date == week_start_date)\
        .first()
    
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    # Добавляем тренировку в нужный день
    plan_data = plan.plan_json
    days = plan_data.get("days", [])
    
    # Находим день или создаём новый
    day_entry = next((d for d in days if d["date"] == date), None)
    if day_entry:
        # Заменяем тренировку
        day_entry.update({
            "sport": workout["sport"],
            "session_type": workout["type"],
            "duration_min": workout["duration_min"],
            "intensity": workout["intensity"],
            "description": workout["description"],
            "primary_goal": workout["primary_goal"],
            "priority": "high" if "key_workout" in workout["tags"] else "medium"
        })
    else:
        # Добавляем новый день
        days.append({
            "date": date,
            "sport": workout["sport"],
            "session_type": workout["type"],
            "duration_min": workout["duration_min"],
            "intensity": workout["intensity"],
            "description": workout["description"],
            "primary_goal": workout["primary_goal"],
            "priority": "high" if "key_workout" in workout["tags"] else "medium"
        })
    
    plan_data["days"] = days
    plan.plan_json = plan_data
    
    db.commit()
    
    return {
        "message": "Workout added to plan",
        "workout": workout
    }
```

---

## 5. ВИЗУАЛИЗАЦИЯ ПРОГРЕССА

### Концепция
Красивые графики и дашборды:
- Training load по неделям (stacked bar chart)
- Fitness vs Fatigue vs Form (PMC chart)
- Pace/Power progression
- Race readiness meter

### Пример endpoint для данных графика

```python
# analytics.py

@app.get("/analytics/weekly_volume")
async def get_weekly_volume_chart(
    weeks: int = 12,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Возвращает данные для графика недельного объёма.
    
    Response format для Recharts (React):
    [
      {
        "week": "2025-W10",
        "run_hours": 3.5,
        "bike_hours": 4.2,
        "swim_hours": 1.8,
        "total_hours": 9.5
      },
      ...
    ]
    """
    # Группируем активности по неделям
    activities = db.query(Activity)\
        .filter(Activity.user_id == current_user.id)\
        .order_by(Activity.start_date.desc())\
        .limit(weeks * 10)  # примерно 10 активностей в неделю
        .all()
    
    # ... агрегация по неделям ...
    
    return weekly_data


@app.get("/analytics/pmc")
async def get_performance_management_chart(
    weeks: int = 12,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Performance Management Chart (TrainingPeaks style):
    - CTL (Chronic Training Load) — fitness
    - ATL (Acute Training Load) — fatigue
    - TSB (Training Stress Balance) — form
    
    Response:
    [
      {
        "date": "2025-03-01",
        "ctl": 45.2,  # fitness (rolling 42-day avg of TSS)
        "atl": 52.1,  # fatigue (rolling 7-day avg of TSS)
        "tsb": -6.9   # form (CTL - ATL)
      },
      ...
    ]
    
    Interpretation:
    - TSB < -10: fatigued, need rest
    - TSB -5 to +5: race-ready zone
    - TSB > +10: well-rested, losing fitness
    """
    # ... calculate TSS for each workout ...
    # ... rolling averages ...
    
    return pmc_data
```

---

## ЗАКЛЮЧЕНИЕ

Эти 5 фич дадут огромное конкурентное преимущество:

1. **Auto Training Zones** — персонализация без ручного ввода
2. **Race Strategy** — готовность к дню гонки (unique!)
3. **Fatigue Detection** — предотвращение перетренированности
4. **Workout Library** — гибкость и удобство
5. **Visualization** — пользователи любят графики

Приоритет реализации:
1️⃣ Workout Library (быстро, полезно сразу)
2️⃣ Fatigue Detection (критично для безопасности)
3️⃣ Auto Zones (убирает трение)
4️⃣ Visualization (wow-фактор)
5️⃣ Race Strategy (за 2-4 недели до гонки)

Каждая фича добавляет ценность и снижает churn rate! 🚀
