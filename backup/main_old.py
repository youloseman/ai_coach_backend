from typing import Optional

import datetime as dt
import json

from fastapi import FastAPI, HTTPException, Request

from fastapi.responses import RedirectResponse, JSONResponse, HTMLResponse
from pydantic import BaseModel

from config import (
    STRAVA_CLIENT_ID,
    STRAVA_REDIRECT_URI,
    EMAIL_TO,
    logger,
)
from training_zones import (
    calculate_running_zones_from_race,
    calculate_cycling_zones_from_ftp,
    calculate_swimming_zones_from_css,
    find_best_race_efforts
)
from analytics import (
    analyze_training_load,
    calculate_training_metrics,
    get_form_interpretation
)
from strava_client import (
    exchange_code_for_token,
    fetch_activities,
    fetch_recent_activities_for_coach,
    fetch_activities_last_n_weeks,
)
from progress import ProgressRequest, run_progress_tracker
from email_client import send_html_email
from coach import GoalInput, WeeklyPlanRequest, run_initial_assessment, run_weekly_plan
from plan_storage import save_weekly_plan, load_weekly_plan
from plan_vs_fact import compare_plan_with_strava, analyze_week_with_coach
from report_storage import save_weekly_report
from athlete_profile import AthleteProfile, load_athlete_profile, save_athlete_profile
from utils import normalize_sport, parse_activity_date, activity_duration_hours, get_week_start, format_duration


class WeeklyPlanEmailRequest(BaseModel):
    goal: GoalInput
    week_start_date: str
    available_hours_per_week: float
    notes: Optional[str] = None
    subject: Optional[str] = None


class WeeklyReportEmailRequest(BaseModel):
    goal: GoalInput
    week_start_date: str                 # с какой даты строим план
    available_hours_per_week: float
    notes: Optional[str] = None          # пожелания по неделе (плавание вт/чт и т.п.)
    progress_weeks: int = 8              # за сколько недель считать прогресс
    subject: Optional[str] = None
    
class ManualZonesInput(BaseModel):
    """Ручной ввод данных для расчёта зон"""
    # Running
    run_race_distance_km: Optional[float] = None
    run_race_time_seconds: Optional[float] = None
    run_race_type: Optional[str] = None  # "5K", "10K", "HM", "Marathon"
    
    # Cycling
    bike_ftp_watts: Optional[float] = None
    
    # Swimming
    swim_css_pace_per_100m: Optional[float] = None


app = FastAPI()

# ===== ATHLETE PROFILE =====

@app.get("/coach/profile", response_model=AthleteProfile)
async def get_athlete_profile():
    """
    Вернуть текущий профиль атлета (если не задан — дефолтный).
    """
    return load_athlete_profile()


@app.post("/coach/profile", response_model=AthleteProfile)
async def update_athlete_profile(profile: AthleteProfile):
    """
    Обновить и сохранить профиль атлета (ручные поля).
    Авто-поля (auto_*) этим эндпоинтом не считаются.
    """
    save_athlete_profile(profile)
    return profile

@app.post("/coach/profile/auto_from_history", response_model=AthleteProfile)
async def auto_update_profile_from_history(weeks: int = 200):
    """
    Автоматически обновляет профиль атлета на основе истории тренировок в Strava.

    Делает:
    - тянет активности за N недель (по умолчанию 200);
    - считает недельные стрики, средние часы, расклад по видам спорта;
    - заполняет auto_* поля профиля;
    - при необходимости корректирует level и max_hours_per_week,
      если они ещё дефолтные.
    """
    profile = load_athlete_profile()

    activities = await fetch_activities_last_n_weeks(weeks=weeks)
    stats = analyze_activities_for_profile(activities)

    profile.auto_weeks_analyzed = stats["weeks_analyzed"]
    profile.auto_current_weekly_streak_weeks = stats["current_streak"]
    profile.auto_longest_weekly_streak_weeks = stats["longest_streak"]
    profile.auto_avg_hours_last_12_weeks = round(stats["avg_hours_12w"], 2)
    profile.auto_avg_hours_last_52_weeks = round(stats["avg_hours_52w"], 2)
    profile.auto_discipline_hours_per_week = {
        k: round(v, 2) for k, v in stats["discipline_avg_hours"].items()
    }

    # Простая эвристика по level, если ещё дефолтный
    avg_12 = stats["avg_hours_12w"]
    if profile.level == "intermediate":
        if avg_12 < 3:
            inferred_level = "beginner"
        elif avg_12 < 7:
            inferred_level = "intermediate"
        elif avg_12 < 12:
            inferred_level = "advanced"
        else:
            inferred_level = "high_performance"
        profile.level = inferred_level

    # max_hours_per_week — типичный объём * 1.3, если стоит дефолт 8.0
    if profile.max_hours_per_week == 8.0 and avg_12 > 0:
        profile.max_hours_per_week = round(avg_12 * 1.3, 1)

    save_athlete_profile(profile)
    return profile

@app.post("/coach/zones/auto_from_activities")
async def calculate_zones_from_activities(weeks: int = 260):
    """
    Автоматически рассчитывает тренировочные зоны на основе лучших результатов
    из истории тренировок в Strava.
    
    Ищет лучшие результаты на дистанциях:
    - Run: 5K, 10K, Half Marathon, Marathon
    - Bike: 40K, 90K (70.3)
    - Swim: 1500m
    
    И рассчитывает зоны из самого свежего/лучшего результата.
    """
    # Получаем историю тренировок
    activities = await fetch_activities_last_n_weeks(weeks=weeks)
    
    # Находим лучшие результаты
    best_efforts = find_best_race_efforts(activities)
    
    if not best_efforts:
        return {
            "status": "no_race_efforts_found",
            "message": "No race efforts found in activity history. Try manual input.",
            "best_efforts": {},
            "zones_calculated": False
        }
    
    # Загружаем профиль
    profile = load_athlete_profile()
    
    # Рассчитываем зоны для бега (приоритет: 10K > HM > 5K > Marathon)
    if "run_10k" in best_efforts:
        effort = best_efforts["run_10k"]
        zones_run = calculate_running_zones_from_race(
            distance_km=effort["distance_km"],
            time_seconds=effort["time_seconds"],
            race_type="10K"
        )
        profile.training_zones_run = zones_run.to_dict()
        profile.training_zones_run["source"] = f"10K race on {effort['date']}"
    elif "run_hm" in best_efforts:
        effort = best_efforts["run_hm"]
        zones_run = calculate_running_zones_from_race(
            distance_km=effort["distance_km"],
            time_seconds=effort["time_seconds"],
            race_type="HM"
        )
        profile.training_zones_run = zones_run.to_dict()
        profile.training_zones_run["source"] = f"Half Marathon on {effort['date']}"
    elif "run_5k" in best_efforts:
        effort = best_efforts["run_5k"]
        zones_run = calculate_running_zones_from_race(
            distance_km=effort["distance_km"],
            time_seconds=effort["time_seconds"],
            race_type="5K"
        )
        profile.training_zones_run = zones_run.to_dict()
        profile.training_zones_run["source"] = f"5K race on {effort['date']}"
    
    # Рассчитываем зоны для велосипеда (если есть FTP или можем оценить)
    # Пока оставляем None - в будущем добавим оценку FTP из power meter данных
    
    # Рассчитываем зоны для плавания
    if "swim_1500m" in best_efforts:
        effort = best_efforts["swim_1500m"]
        from training_zones import estimate_css_from_swim
        css = estimate_css_from_swim(
            distance_m=effort["distance_m"],
            time_seconds=effort["time_seconds"]
        )
        zones_swim = calculate_swimming_zones_from_css(css)
        profile.training_zones_swim = zones_swim.to_dict()
        profile.training_zones_swim["source"] = f"1500m swim on {effort['date']}"
    
    # Обновляем дату
    import datetime as dt
    profile.zones_last_updated = str(dt.date.today())
    
    # Сохраняем профиль
    save_athlete_profile(profile)
    
    return {
        "status": "success",
        "message": "Training zones calculated and saved to profile",
        "best_efforts": best_efforts,
        "zones_calculated": {
            "run": profile.training_zones_run is not None,
            "bike": profile.training_zones_bike is not None,
            "swim": profile.training_zones_swim is not None
        },
        "profile": profile
    }


@app.post("/coach/zones/manual")
async def calculate_zones_manual(input_data: ManualZonesInput):
    """
    Рассчитывает тренировочные зоны на основе ручного ввода данных.
    
    Примеры:
    - 10K за 40 минут: run_race_distance_km=10, run_race_time_seconds=2400, run_race_type="10K"
    - FTP 250W: bike_ftp_watts=250
    - CSS 1:40/100m: swim_css_pace_per_100m=100
    """
    profile = load_athlete_profile()
    
    # Running zones
    if input_data.run_race_distance_km and input_data.run_race_time_seconds and input_data.run_race_type:
        zones_run = calculate_running_zones_from_race(
            distance_km=input_data.run_race_distance_km,
            time_seconds=input_data.run_race_time_seconds,
            race_type=input_data.run_race_type
        )
        profile.training_zones_run = zones_run.to_dict()
        profile.training_zones_run["source"] = f"Manual input: {input_data.run_race_type}"
    
    # Cycling zones
    if input_data.bike_ftp_watts:
        zones_bike = calculate_cycling_zones_from_ftp(input_data.bike_ftp_watts)
        profile.training_zones_bike = zones_bike.to_dict()
        profile.training_zones_bike["source"] = "Manual FTP input"
    
    # Swimming zones
    if input_data.swim_css_pace_per_100m:
        zones_swim = calculate_swimming_zones_from_css(input_data.swim_css_pace_per_100m)
        profile.training_zones_swim = zones_swim.to_dict()
        profile.training_zones_swim["source"] = "Manual CSS input"
    
    # Обновляем дату
    import datetime as dt
    profile.zones_last_updated = str(dt.date.today())
    
    # Сохраняем
    save_athlete_profile(profile)
    
    return {
        "status": "success",
        "message": "Training zones calculated from manual input and saved",
        "zones_calculated": {
            "run": profile.training_zones_run is not None,
            "bike": profile.training_zones_bike is not None,
            "swim": profile.training_zones_swim is not None
        },
        "profile": profile
    }


@app.get("/coach/zones")
async def get_training_zones():
    """
    Получить текущие тренировочные зоны из профиля.
    """
    profile = load_athlete_profile()
    
    return {
        "zones_last_updated": profile.zones_last_updated,
        "run": profile.training_zones_run,
        "bike": profile.training_zones_bike,
        "swim": profile.training_zones_swim
    }

@app.get("/analytics/training_load")
async def get_training_load_analytics(weeks: int = 12):
    """
    Получить комплексный анализ тренировочной нагрузки.
    
    Возвращает:
    - CTL (Chronic Training Load) - fitness
    - ATL (Acute Training Load) - fatigue
    - TSB (Training Stress Balance) - form
    - Ramp Rate - скорость набора формы
    - Weekly TSS - средний TSS за неделю
    - Timeline метрик за последние 4 недели
    
    Args:
        weeks: Количество недель для анализа (по умолчанию 12)
    """
    try:
        # Получаем активности
        activities = await fetch_activities_last_n_weeks(weeks=weeks)
        
        if not activities:
            return {
                "error": "No activities found",
                "current_ctl": 0,
                "current_atl": 0,
                "current_tsb": 0
            }
        
        # Анализируем нагрузку
        analysis = analyze_training_load(activities, weeks_to_analyze=weeks)
        
        return {
            "status": "success",
            "analysis": analysis
        }
        
    except Exception as e:
        logger.error("analytics_error", error=str(e))
        return {
            "error": str(e),
            "current_ctl": 0,
            "current_atl": 0,
            "current_tsb": 0
        }


@app.get("/analytics/fitness_timeline")
async def get_fitness_timeline(days: int = 90):
    """
    Получить timeline метрик (CTL, ATL, TSB) за период.
    
    Полезно для построения графиков Performance Management Chart (PMC).
    
    Args:
        days: Количество дней (по умолчанию 90)
    """
    import datetime as dt
    
    try:
        # Получаем активности за этот период
        weeks = (days // 7) + 1
        activities = await fetch_activities_last_n_weeks(weeks=weeks)
        
        if not activities:
            return {
                "error": "No activities found",
                "timeline": []
            }
        
        # Рассчитываем метрики
        today = dt.date.today()
        metrics = calculate_training_metrics(activities, today, days=days)
        
        return {
            "status": "success",
            "days": days,
            "timeline": [m.to_dict() for m in metrics]
        }
        
    except Exception as e:
        logger.error("timeline_error", error=str(e))
        return {
            "error": str(e),
            "timeline": []
        }


@app.get("/analytics/form_status")
async def get_current_form_status():
    """
    Получить текущий статус формы (TSB интерпретация).
    
    Быстрый endpoint для проверки - готов ли к гонке или нужен отдых.
    """
    try:
        # Получаем последние 12 недель
        activities = await fetch_activities_last_n_weeks(weeks=12)
        
        if not activities:
            return {
                "error": "No activities found",
                "status": "unknown"
            }
        
        # Рассчитываем метрики
        import datetime as dt
        today = dt.date.today()
        metrics = calculate_training_metrics(activities, today, days=90)
        
        if not metrics:
            return {
                "error": "Unable to calculate metrics",
                "status": "unknown"
            }
        
        # Текущие значения
        current = metrics[-1]
        form_interpretation = get_form_interpretation(current.tsb)
        
        return {
            "status": "success",
            "date": str(current.date),
            "ctl": round(current.ctl, 1),
            "atl": round(current.atl, 1),
            "tsb": round(current.tsb, 1),
            "form": form_interpretation
        }
        
    except Exception as e:
        logger.error("form_status_error", error=str(e))
        return {
            "error": str(e),
            "status": "unknown"
        }

# ===== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ =====

def analyze_activities_for_profile(activities: list[dict]) -> dict:
    """
    Анализирует историю тренировок для автозаполнения профиля:
    - недельный стрик (текущий и максимальный),
    - средние часы за последние 12/52 недель,
    - средние часы по видам спорта.
    """
    if not activities:
        return {
            "weeks_analyzed": 0,
            "current_streak": 0,
            "longest_streak": 0,
            "avg_hours_12w": 0.0,
            "avg_hours_52w": 0.0,
            "discipline_avg_hours": {},
        }

    # Нормализация вида спорта
    def normalize_sport_local(name: Optional[str]) -> str:
        if not name:
            return "other"
        s = name.lower()
        if "run" in s:
            return "run"
        if "ride" in s or "bike" in s or "cycl" in s:
            return "bike"
        if "swim" in s:
            return "swim"
        if "strength" in s or "gym" in s or "workout" in s:
            return "strength"
        return "other"

    # Парсим дату
    def parse_activity_date_local(a: dict) -> Optional[dt.date]:
        raw = a.get("start_date")
        if not raw:
            return None
        try:
            dtt = dt.datetime.fromisoformat(raw.replace("Z", "+00:00"))
            return dtt.date()
        except ValueError:
            return None

    # Длительность в часах
    def activity_duration_hours_local(a: dict) -> float:
        seconds = a.get("moving_time_s") or a.get("moving_time") or 0
        return float(seconds) / 3600.0

    # Группируем по неделям (week_start = понедельник)
    week_stats: dict[dt.date, dict] = {}
    for a in activities:
        d = parse_activity_date_local(a)
        if not d:
            continue
        week_start = d - dt.timedelta(days=d.weekday())
        sport = normalize_sport_local(a.get("sport_type"))
        hours = activity_duration_hours_local(a)
        if week_start not in week_stats:
            week_stats[week_start] = {
                "total_hours": 0.0,
                "by_sport": {"run": 0.0, "bike": 0.0, "swim": 0.0, "strength": 0.0, "other": 0.0},
            }
        week_stats[week_start]["total_hours"] += hours
        week_stats[week_start]["by_sport"][sport] = week_stats[week_start]["by_sport"].get(sport, 0.0) + hours

    if not week_stats:
        return {
            "weeks_analyzed": 0,
            "current_streak": 0,
            "longest_streak": 0,
            "avg_hours_12w": 0.0,
            "avg_hours_52w": 0.0,
            "discipline_avg_hours": {},
        }

    weeks_sorted = sorted(week_stats.keys())
    n_weeks = len(weeks_sorted)

    # Longest streak
    longest_streak = 0
    current_run = 0
    prev_week: Optional[dt.date] = None

    for w in weeks_sorted:
        has_training = week_stats[w]["total_hours"] > 0
        if not has_training:
            current_run = 0
            prev_week = w
            continue

        if prev_week is None:
            current_run = 1
        else:
            if (w - prev_week).days <= 7:
                current_run += 1
            else:
                current_run = 1

        if current_run > longest_streak:
            longest_streak = current_run

        prev_week = w

    # Current streak — от последней недели назад, без дыр
    current_streak = 0
    if weeks_sorted:
        last_idx = len(weeks_sorted) - 1
        last_week = weeks_sorted[last_idx]
        idx = last_idx
        while idx >= 0:
            w = weeks_sorted[idx]
            has_training = week_stats[w]["total_hours"] > 0
            if not has_training:
                break
            expected_delta = 7 * (last_idx - idx)
            if (last_week - w).days != expected_delta:
                break
            current_streak += 1
            idx -= 1

    # Средние часы за последние 12/52 недель
    def avg_last_k_weeks(k: int) -> float:
        if n_weeks == 0:
            return 0.0
        k = min(k, n_weeks)
        last_weeks = weeks_sorted[-k:]
        total = sum(week_stats[w]["total_hours"] for w in last_weeks)
        return total / k

    avg_12 = avg_last_k_weeks(12)
    avg_52 = avg_last_k_weeks(52)

    # Средние часы по дисциплинам
    discipline_totals = {"run": 0.0, "bike": 0.0, "swim": 0.0, "strength": 0.0, "other": 0.0}
    for w in weeks_sorted:
        for sport_key in discipline_totals.keys():
            discipline_totals[sport_key] += week_stats[w]["by_sport"].get(sport_key, 0.0)

    discipline_avg = {}
    if n_weeks > 0:
        for sport_key in discipline_totals.keys():
            discipline_avg[sport_key] = discipline_totals[sport_key] / n_weeks

    return {
        "weeks_analyzed": n_weeks,
        "current_streak": current_streak,
        "longest_streak": longest_streak,
        "avg_hours_12w": avg_12,
        "avg_hours_52w": avg_52,
        "discipline_avg_hours": discipline_avg,
    }


# ===== ENDPOINTS =====

@app.post("/coach/initial_assessment")
async def coach_initial_assessment(goal: GoalInput):
    """
    Первичная оценка текущей подготовки атлета на основе истории тренировок.
    """
    activities = await fetch_recent_activities_for_coach()
    result = run_initial_assessment(goal, activities)
    return result


@app.post("/coach/plan")
async def coach_plan(req: WeeklyPlanRequest):
    """
    Генерация плана тренировок на неделю.
    """
    activities = await fetch_recent_activities_for_coach(limit=req.limit)
    plan = run_weekly_plan(req.week_start_date, req.goal, activities)
    
    # Сохраняем план
    save_weekly_plan(req.week_start_date, plan)
    
    return plan


@app.post("/coach/weekly_plan_email")
async def coach_weekly_plan_email(req: WeeklyPlanEmailRequest):
    """
    Генерирует план тренировок на неделю и отправляет на email.
    """
    activities_for_plan = await fetch_recent_activities_for_coach(limit=80)
    
    plan_data = run_weekly_plan(
      req.week_start_date,  # позиционный аргумент
      req.goal,             # позиционный аргумент
      activities_for_plan, # позиционный аргумент
    )
    
    # Сохраняем план
    save_weekly_plan(req.week_start_date, plan_data)
    
    # Формируем HTML письмо
    week_start_str = plan_data.get("week_start_date", req.week_start_date)
    total_hours = plan_data.get("total_planned_hours", 0)
    days = plan_data.get("days", [])
    plan_notes = plan_data.get("notes", {})
    
    plan_rows_html = ""
    for day in days:
        plan_rows_html += f"""
        <tr>
          <td>{day.get("date", "")}</td>
          <td>{day.get("sport", "")}</td>
          <td>{day.get("session_type", "")}</td>
          <td>{day.get("duration_min", 0)} min</td>
          <td>{day.get("intensity", "")}</td>
          <td>{day.get("primary_goal", "")}</td>
          <td>{day.get("priority", "")}</td>
          <td>{day.get("description", "")}</td>
        </tr>
        """
    
    html_body = f"""
    <html>
      <head>
        <style>
          body {{
            font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            max-width: 1000px;
            margin: 40px auto;
            line-height: 1.6;
          }}
          h1, h2, h3 {{
            margin-bottom: 0.3em;
          }}
          .section {{
            margin-bottom: 32px;
            padding: 16px 20px;
            border-radius: 12px;
            background: #f5f5f5;
          }}
          table {{
            border-collapse: collapse;
            width: 100%;
            margin-top: 16px;
          }}
          th, td {{
            border: 1px solid #ddd;
            padding: 8px;
            vertical-align: top;
            font-size: 14px;
          }}
          th {{
            background-color: #f5f5f5;
            text-align: left;
          }}
        </style>
      </head>
      <body>
        <h1>Weekly Training Plan</h1>
        
        <div class="section">
          <h2>Plan for week starting {week_start_str}</h2>
          <div><span style="font-weight: 600;">Planned volume:</span> {total_hours:.1f} h</div>

          <table>
            <thead>
              <tr>
                <th>Date</th>
                <th>Sport</th>
                <th>Type</th>
                <th>Duration</th>
                <th>Intensity</th>
                <th>Goal</th>
                <th>Priority</th>
                <th>Description</th>
              </tr>
            </thead>
            <tbody>
              {plan_rows_html}
            </tbody>
          </table>

          <h3>Week notes</h3>
          <p>{plan_notes.get("overall_focus", "")}</p>
          <p>{plan_notes.get("recovery_guidelines", "")}</p>
          <p>{plan_notes.get("nutrition_tips", "")}</p>
        </div>
      </body>
    </html>
    """
    
    subject = req.subject or f"AI Coach – Weekly plan (week starting {week_start_str})"
    send_html_email(EMAIL_TO, subject, html_body)
    
    return {
        "status": "ok",
        "message": f"Weekly plan sent to {EMAIL_TO}",
        "week_start_date": week_start_str,
        "planned_hours": total_hours,
    }


@app.post("/coach/weekly_report_email")
async def coach_weekly_report_email(req: WeeklyReportEmailRequest):
    """
    Формирует единый еженедельный отчёт:
    - прогресс за последние N недель (нагрузка + реалистичность цели),
    - план тренировок на следующую неделю,
    - блок "Plan vs fact" по прошлой неделе,
    - GPT анализ выполнения прошлой недели (Coach Feedback),
    и отправляет всё одним HTML-письмом.
    """
    # 1) Прогресс: последние N недель
    progress_activities = await fetch_activities_last_n_weeks(weeks=req.progress_weeks)
    progress_result = await run_progress_tracker(
        ProgressRequest(goal=req.goal, weeks=req.progress_weeks),
        progress_activities,
    )

    goal = progress_result["goal"]
    summary = progress_result["summary"]
    evaluation = progress_result["evaluation"]
    
    # 1.5) Training Load Analytics (NEW!)
    try:
        logger.info("calculating_training_load_analytics")
        training_load_analysis = analyze_training_load(
            activities=progress_activities,
            weeks_to_analyze=12  # Анализируем последние 12 недель
        )
    except Exception as e:
        logger.error("training_load_analytics_error", error=str(e))
        training_load_analysis = {
            "current_ctl": 0,
            "current_atl": 0,
            "current_tsb": 0,
            "form_status": "unknown"
        }
    
    # 2) План на следующую неделю
    activities_for_plan = await fetch_recent_activities_for_coach(limit=80)

    profile = load_athlete_profile()

    # Создаём объект WeeklyPlanRequest
    plan_request = WeeklyPlanRequest(
        goal=req.goal,
        week_start_date=req.week_start_date,
        available_hours_per_week=req.available_hours_per_week,
        notes=req.notes
    )

    # Вызываем функцию (она async!)
    plan_data = await run_weekly_plan(plan_request, activities_for_plan)
    
    # Сохраняем план
    save_weekly_plan(req.week_start_date, plan_data)
    
    # 3) План vs факт (прошлая неделя) + Coach Feedback
    last_week_start = dt.date.fromisoformat(req.week_start_date) - dt.timedelta(days=7)
    
    plan_vs_fact_summary = None
    coach_feedback = None
    
    try:
      last_week_plan = load_weekly_plan(str(last_week_start))
      
      # ПРОВЕРКА: если плана нет - пропускаем анализ
      if last_week_plan is None:
          logger.warning("no_plan_for_last_week", week=str(last_week_start))
          plan_vs_fact_summary = None
          coach_feedback = None
      else:
          # Получаем активности за прошлую неделю
          last_week_end = last_week_start + dt.timedelta(days=7)
          last_week_activities = [
              act for act in progress_activities
              if last_week_start <= parse_activity_date(act) < last_week_end
          ] if progress_activities else []
          
          # Сравнение план vs факт
          plan_vs_fact_summary = compare_plan_with_strava(last_week_plan, last_week_activities)
          
          # GPT анализ выполнения недели
          logger.info("generating_coach_feedback", week=str(last_week_start))
          coach_feedback = analyze_week_with_coach(
              plan=last_week_plan,
              actual_activities=last_week_activities,
              comparison_stats=plan_vs_fact_summary,
              athlete_goal={
                  "main_goal_type": req.goal.main_goal_type,
                  "main_goal_target_time": req.goal.main_goal_target_time,
                  "main_goal_race_date": str(req.goal.main_goal_race_date)
              }
          )
    
    except FileNotFoundError:
        logger.warning("no_plan_for_last_week_file_not_found", week=str(last_week_start))
        plan_vs_fact_summary = None
        coach_feedback = None
    except Exception as e:
        logger.error("coach_feedback_error", error=str(e), week=str(last_week_start))
        plan_vs_fact_summary = None
        coach_feedback = {
            "overall_assessment": "Unable to generate coach feedback due to technical error",
            "execution_quality": "unknown",
            "error": str(e)
        }

    # ===== HTML ФОРМИРОВАНИЕ =====
    
    week_start_str = plan_data.get("week_start_date", req.week_start_date)
    total_hours = plan_data.get("total_planned_hours", 0)
    days = plan_data.get("days", [])
    plan_notes = plan_data.get("notes", {})
    
    # Athlete profile HTML
    athlete_profile_html = f"""
    <div class="section">
      <h2>Athlete Profile</h2>
      <div><span class="label">Level:</span> {profile.level}</div>
      <div><span class="label">Available hours per week:</span> {req.available_hours_per_week:.1f} h</div>
      <div><span class="label">Current weekly streak:</span> {profile.auto_current_weekly_streak_weeks} weeks</div>
      <div><span class="label">Longest weekly streak:</span> {profile.auto_longest_weekly_streak_weeks} weeks</div>
      <div><span class="label">Avg hours (last 12 weeks):</span> {profile.auto_avg_hours_last_12_weeks:.1f} h</div>
      <div><span class="label">Avg hours (last 52 weeks):</span> {profile.auto_avg_hours_last_52_weeks:.1f} h</div>
    </div>
    """
    
    
    # Plan vs Fact HTML
    plan_vs_fact_html = ""
    if plan_vs_fact_summary:
        sessions_by_sport = plan_vs_fact_summary.get("sessions_by_sport", {})
        sport_rows = ""
        for sport_name, sport_data in sessions_by_sport.items():
            sport_rows += f"""
            <tr>
              <td>{sport_name}</td>
              <td>{sport_data.get("completed", 0)}</td>
              <td>{sport_data.get("missed", 0)}</td>
              <td>{sport_data.get("shortened", 0)}</td>
              <td>{sport_data.get("planned_total_min", 0)} min</td>
              <td>{sport_data.get("actual_total_min", 0)} min</td>
            </tr>
            """
        
        plan_vs_fact_html = f"""
        <div class="section">
          <h2>Plan vs Fact (last week: {last_week_start})</h2>
          <div><span class="label">Completed sessions:</span> {plan_vs_fact_summary.get("completed", 0)}</div>
          <div><span class="label">Missed sessions:</span> {plan_vs_fact_summary.get("missed", 0)}</div>
          <div><span class="label">Shortened sessions:</span> {plan_vs_fact_summary.get("shortened", 0)}</div>
          
          <h3>By sport</h3>
          <table>
            <thead>
              <tr>
                <th>Sport</th>
                <th>Completed</th>
                <th>Missed</th>
                <th>Shortened</th>
                <th>Planned (min)</th>
                <th>Actual (min)</th>
              </tr>
            </thead>
            <tbody>
              {sport_rows}
            </tbody>
          </table>
        </div>
        """
    
    # Coach Feedback HTML
    coach_feedback_html = ""
    if coach_feedback and not coach_feedback.get("error"):
        key_wins_html = ""
        if coach_feedback.get("key_wins"):
            key_wins_html = "<h3>✅ Key Wins</h3><ul>"
            for win in coach_feedback.get("key_wins", []):
                key_wins_html += f"<li>{win}</li>"
            key_wins_html += "</ul>"
        
        concerns_html = ""
        if coach_feedback.get("concerns"):
            concerns_html = "<h3>⚠️ Concerns</h3><ul style='color: #d32f2f;'>"
            for concern in coach_feedback.get("concerns", []):
                concerns_html += f"<li>{concern}</li>"
            concerns_html += "</ul>"
        
        patterns_html = ""
        if coach_feedback.get("patterns_detected"):
            patterns_html = "<h3>🔍 Patterns Detected</h3><ul>"
            for pattern in coach_feedback.get("patterns_detected", []):
                patterns_html += f"<li>{pattern}</li>"
            patterns_html += "</ul>"
        
        recommendations_html = ""
        if coach_feedback.get("recommendations_next_week"):
            recommendations_html = "<h3>🎯 Recommendations for Next Week</h3><ul>"
            for rec in coach_feedback.get("recommendations_next_week", []):
                recommendations_html += f"<li>{rec}</li>"
            recommendations_html += "</ul>"
        
        exec_quality = coach_feedback.get("execution_quality", "unknown")
        quality_color = "#4caf50" if exec_quality in ["excellent", "good"] else ("#ff9800" if exec_quality == "fair" else "#f44336")
        
        coach_feedback_html = f"""
        <div class="section" style="background: #f0f8ff; border-left: 4px solid #4a90e2;">
          <h2 style="color: #4a90e2;">📊 Weekly Coach Feedback</h2>
          
          <div style="margin: 15px 0;">
            <span class="label">Overall Assessment:</span>
            <p>{coach_feedback.get("overall_assessment", "N/A")}</p>
          </div>
          
          <div style="margin: 15px 0;">
            <span class="label">Execution Quality:</span> 
            <span style="display: inline-block; padding: 5px 10px; background: {quality_color}; color: white; border-radius: 3px; font-weight: 600;">
              {exec_quality.upper()}
            </span>
            ({coach_feedback.get("execution_percentage", 0):.1f}%)
          </div>
          
          <div style="margin: 15px 0;">
            <span class="label">Impact on Goal:</span>
            <p>{coach_feedback.get("impact_on_goal", "N/A")}</p>
          </div>
          
          {key_wins_html}
          {concerns_html}
          {patterns_html}
          {recommendations_html}
          
          <div style="margin: 20px 0; padding: 15px; background: white; border-radius: 5px; border-left: 3px solid #4a90e2;">
            <span class="label">💪 Coach's Message:</span>
            <p style="font-style: italic; margin-top: 10px;">{coach_feedback.get("motivation_message", "Keep up the great work!")}</p>
          </div>
        </div>
        """
    
    # Progress rows HTML
    weekly_data = summary.get("weekly_data", [])
    progress_rows_html = ""
    for week in weekly_data:
        progress_rows_html += f"""
        <tr>
          <td>{week.get("week_start", "")}</td>
          <td>{week.get("total_hours", 0):.1f}</td>
          <td>{week.get("run_hours", 0):.1f}</td>
          <td>{week.get("bike_hours", 0):.1f}</td>
          <td>{week.get("swim_hours", 0):.1f}</td>
          <td>{week.get("other_hours", 0):.1f}</td>
          <td>{week.get("session_count", 0)}</td>
        </tr>
        """
    
    # Plan rows HTML
    plan_rows_html = ""
    for day in days:
        plan_rows_html += f"""
        <tr>
          <td>{day.get("date", "")}</td>
          <td>{day.get("sport", "")}</td>
          <td>{day.get("session_type", "")}</td>
          <td>{day.get("duration_min", 0)} min</td>
          <td>{day.get("intensity", "")}</td>
          <td>{day.get("primary_goal", "")}</td>
          <td>{day.get("priority", "")}</td>
          <td>{day.get("description", "")}</td>
        </tr>
        """
    
    # Полный HTML
    html_body = f"""
    <html>
      <head>
        <style>
          body {{
            font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            max-width: 1000px;
            margin: 40px auto;
            line-height: 1.6;
          }}
          h1, h2, h3 {{
            margin-bottom: 0.3em;
          }}
          .section {{
            margin-bottom: 32px;
            padding: 16px 20px;
            border-radius: 12px;
            background: #f5f5f5;
          }}
          .label {{
            font-weight: 600;
          }}
          table {{
            border-collapse: collapse;
            width: 100%;
            margin-top: 16px;
          }}
          th, td {{
            border: 1px solid #ddd;
            padding: 8px;
            vertical-align: top;
            font-size: 14px;
          }}
          th {{
            background-color: #f5f5f5;
            text-align: left;
          }}
          tr:nth-child(even) {{
            background-color: #fafafa;
          }}
          .pill {{
            display: inline-block;
            padding: 4px 8px;
            border-radius: 999px;
            font-size: 13px;
            font-weight: 600;
          }}
          .pill-low {{
            background: #ffe5e5;
            color: #a10000;
          }}
          .pill-medium {{
            background: #fff7e5;
            color: #8a5a00;
          }}
          .pill-high {{
            background: #e5ffe7;
            color: #067d18;
          }}
        </style>
      </head>
      <body>
        <h1>Weekly Report</h1>

        <div class="section">
          <h2>Goal</h2>
          <div><span class="label">Main goal:</span>
            {goal.get("main_goal_type")} – {goal.get("main_goal_target_time")} on {goal.get("main_goal_race_date")}
          </div>
          <div><span class="label">Secondary goals:</span>
            {", ".join(goal.get("secondary_goals") or []) or "none"}
          </div>
        </div>

        {athlete_profile_html}

        {plan_vs_fact_html}
        
        {coach_feedback_html}


        <div class="section">
          <h2>Progress (last {summary.get("weeks_analyzed", 0)} weeks)</h2>
          <div><span class="label">Total hours:</span> {summary.get("total_hours", 0):.1f}</div>
          <div><span class="label">Average per week:</span> {summary.get("avg_hours_per_week", 0):.1f} h</div>
          <div><span class="label">Avg RUN / BIKE / SWIM per week:</span>
            {summary.get("avg_run_hours_per_week", 0):.1f} /
            {summary.get("avg_bike_hours_per_week", 0):.1f} /
            {summary.get("avg_swim_hours_per_week", 0):.1f} h
          </div>
          <div><span class="label">Consistency (weeks ≥ 6h):</span>
            {summary.get("consistency_ratio_weeks_over_6h", 0)*100:.0f}%
          </div>

          <h3>Goal readiness</h3>
          <div>
            <span class="label">Readiness score:</span>
            <span class="pill pill-{evaluation.get("score_label", "low")}">
              {evaluation.get("readiness_score", 0):.1f} / 100 ({evaluation.get("score_label", "").upper()})
            </span>
          </div>
          <p>{evaluation.get("comment", "")}</p>

          <h3>Main risks</h3>
          <ul>
            {"".join(f"<li>{r}</li>" for r in evaluation.get("main_risks", []))}
          </ul>

          <h3>Recommendations</h3>
          <ul>
            {"".join(f"<li>{r}</li>" for r in evaluation.get("recommendations", []))}
          </ul>

          <h3>Weekly breakdown</h3>
          <table>
            <thead>
              <tr>
                <th>Week start</th>
                <th>Total h</th>
                <th>Run h</th>
                <th>Bike h</th>
                <th>Swim h</th>
                <th>Other h</th>
                <th>Sessions</th>
              </tr>
            </thead>
            <tbody>
              {progress_rows_html}
            </tbody>
          </table>
        </div>

        <div class="section">
          <h2>Plan for week starting {week_start_str}</h2>
          <div><span class="label">Planned volume:</span> {total_hours:.1f} h</div>

          <table>
            <thead>
              <tr>
                <th>Date</th>
                <th>Sport</th>
                <th>Type</th>
                <th>Duration</th>
                <th>Intensity</th>
                <th>Goal</th>
                <th>Priority</th>
                <th>Description</th>
              </tr>
            </thead>
            <tbody>
              {plan_rows_html}
            </tbody>
          </table>

          <h3>Week notes</h3>
          <p>{plan_notes.get("overall_focus", "")}</p>
          <p>{plan_notes.get("recovery_guidelines", "")}</p>
          <p>{plan_notes.get("nutrition_tips", "")}</p>
        </div>
      </body>
    </html>
    """

    subject = req.subject or f"AI Coach – Weekly report (week starting {week_start_str})"
    send_html_email(EMAIL_TO, subject, html_body)

    # Сохраняем отчёт с coach feedback
    save_weekly_report(
        week_start_str,
        {
            "goal": goal,
            "summary": summary,
            "evaluation": evaluation,
            "plan": plan_data,
            "plan_vs_fact": plan_vs_fact_summary,
            "coach_feedback": coach_feedback,
            "training_load_analytics": training_load_analysis,
        },
    )

    return {
        "status": "ok",
        "message": f"Weekly report sent to {EMAIL_TO}",
        "week_start_date": week_start_str,
        "planned_hours": total_hours,
        "progress_weeks": summary.get("weeks_analyzed", 0),
        "readiness_score": evaluation.get("readiness_score", 0),
        "readiness_label": evaluation.get("score_label", ""),
        "coach_feedback": coach_feedback,
        "plan_vs_fact": plan_vs_fact_summary,
        "training_load_analytics": training_load_analysis,
    }


# ===== STRAVA AUTH =====

@app.get("/auth/strava/login-debug")
async def strava_login_debug():
    """
    Показываем URL авторизации Strava (для проверки).
    """
    authorize_url = (
        "https://www.strava.com/oauth/authorize"
        f"?client_id={STRAVA_CLIENT_ID}"
        f"&redirect_uri={STRAVA_REDIRECT_URI}"
        "&response_type=code"
        "&scope=activity:read_all,profile:read_all"
        "&approval_prompt=auto"
    )
    return {"authorize_url": authorize_url}


@app.get("/auth/strava/login")
async def strava_login():
    """
    Редиректим пользователя на Strava OAuth.
    """
    authorize_url = (
        "https://www.strava.com/oauth/authorize"
        f"?client_id={STRAVA_CLIENT_ID}"
        f"&redirect_uri={STRAVA_REDIRECT_URI}"
        "&response_type=code"
        "&scope=activity:read_all,profile:read_all"
        "&approval_prompt=auto"
    )
    return RedirectResponse(url=authorize_url, status_code=302)


@app.get("/auth/strava/callback")
async def strava_callback(
    request: Request,
    code: Optional[str] = None,
    error: Optional[str] = None,
):
    """
    Принимаем code от Strava, обмениваем на токены и сохраняем.
    """
    if error:
        raise HTTPException(status_code=400, detail=f"Strava returned error: {error}")

    if not code:
        raise HTTPException(status_code=400, detail="Missing 'code' parameter from Strava")

    token_data = await exchange_code_for_token(code)

    return JSONResponse(
        {
            "message": "Successfully authorized with Strava",
            "token_data": token_data,
        }
    )


# ===== STRAVA ACTIVITIES =====

@app.get("/strava/activities")
async def get_strava_activities(page: int = 1, per_page: int = 50):
    activities = await fetch_activities(page=page, per_page=per_page)
    return {"count": len(activities), "activities": activities}