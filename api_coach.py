import datetime as dt
import json
from typing import Optional, List
from pathlib import Path

from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from pydantic import BaseModel
from slowapi import Limiter

from athlete_profile import AthleteProfile
from strava_client import (
    fetch_activities_last_n_weeks_for_user,
    fetch_recent_activities_for_coach,
)
from cache import (
    get_cached_training_zones,
    cache_training_zones,
    get_cached_user_profile,
    cache_user_profile,
    TTL_TRAINING_ZONES,
    TTL_USER_PROFILE,
)
from utils import (
    normalize_sport,
    parse_activity_date,
    activity_duration_hours,
    get_week_start,
)
from training_zones import (
    calculate_running_zones_from_race,
    calculate_cycling_zones_from_ftp,
    calculate_swimming_zones_from_css,
    find_best_race_efforts,
    estimate_css_from_swim,
)
from analytics import (
    analyze_training_load,
    calculate_training_metrics,
    get_form_interpretation,
)
from performance_predictions import (
    predict_for_goal,
    find_best_efforts,
    predict_race_times,
)
from fatigue_detection import detect_fatigue
from progress import ProgressRequest, run_progress_tracker
from email_client import send_html_email
from coach import GoalInput, WeeklyPlanRequest, run_initial_assessment, run_weekly_plan
from plan_storage import save_weekly_plan, load_weekly_plan
from plan_vs_fact import compare_plan_with_strava, analyze_week_with_coach
from report_storage import save_weekly_report
from calendar_export import (
    export_weekly_plan_to_ics,
    export_multi_week_plan_to_ics,
    get_calendar_download_url,
)
from multi_week_planner import generate_multi_week_plan, create_plan_summary_table
from config import EMAIL_TO, FRONTEND_BASE_URL, logger
from database import get_db
from sqlalchemy.orm import Session
import models
import crud
from auth import get_current_user, decode_access_token


router = APIRouter()

# Rate limiter for coach endpoints (per user)
def get_user_id_for_limiter(request: Request) -> str:
    """Extract user_id from JWT token for rate limiting"""
    try:
        # Get token from Authorization header
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return "anonymous"
        token = auth_header.replace("Bearer ", "")
        payload = decode_access_token(token)
        if payload and payload.get("sub"):
            return str(payload.get("sub"))
    except Exception:
        pass
    return "anonymous"

limiter = Limiter(key_func=get_user_id_for_limiter)

BASE_DIR = Path(__file__).resolve().parent
EXPORTS_DIR = BASE_DIR / "data" / "calendar_exports"


class WeeklyPlanEmailRequest(BaseModel):
    goal: GoalInput
    week_start_date: str
    available_hours_per_week: float
    notes: Optional[str] = None
    subject: Optional[str] = None


class WeeklyReportEmailRequest(BaseModel):
    goal: GoalInput
    week_start_date: str  # с какой даты строим план
    available_hours_per_week: float
    notes: Optional[str] = None  # пожелания по неделе (плавание вт/чт и т.п.)
    progress_weeks: int = 8  # за сколько недель считать прогресс
    subject: Optional[str] = None


class MultiWeekPlanRequest(BaseModel):
    goal: GoalInput
    start_date: str  # ISO format "YYYY-MM-DD"
    num_weeks: int  # 4-16 недель
    base_hours_per_week: float
    peak_hours_per_week: float
    notes: Optional[str] = None


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


def _analyze_activities_for_profile(activities: list[dict]) -> dict:
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

    # Группируем по неделям (week_start = понедельник)
    week_stats: dict[dt.date, dict] = {}
    for a in activities:
        d = parse_activity_date(a)
        if not d:
            continue
        week_start = get_week_start(d)
        sport = normalize_sport(a.get("sport_type"))
        hours = activity_duration_hours(a)
        if week_start not in week_stats:
            week_stats[week_start] = {
                "total_hours": 0.0,
                "by_sport": {
                    "run": 0.0,
                    "bike": 0.0,
                    "swim": 0.0,
                    "strength": 0.0,
                    "other": 0.0,
                },
            }
        week_stats[week_start]["total_hours"] += hours
        week_stats[week_start]["by_sport"][sport] = (
            week_stats[week_start]["by_sport"].get(sport, 0.0) + hours
        )

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

    # Current streak
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
    discipline_totals = {
        "run": 0.0,
        "bike": 0.0,
        "swim": 0.0,
        "strength": 0.0,
        "other": 0.0,
    }
    for w in weeks_sorted:
        for sport_key in discipline_totals.keys():
            discipline_totals[sport_key] += week_stats[w]["by_sport"].get(
                sport_key, 0.0
            )

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


@router.get("/coach/profile", response_model=AthleteProfile)
async def get_athlete_profile(
    current_user: models.User = Depends(get_current_user),
    db: "Session" = Depends(get_db),
):
    """
    Вернуть профиль атлета для текущего пользователя.
    Поддерживает кеширование для оптимизации производительности.
    """
    # Check cache first
    cached_profile = get_cached_user_profile(current_user.id)
    if cached_profile is not None:
        return AthleteProfile(**cached_profile)
    
    # Cache miss - load from DB
    db_profile = crud.get_user_profile(db, current_user.id)
    if not db_profile:
        # Create default profile if doesn't exist
        db_profile = models.AthleteProfileDB(user_id=current_user.id)
        db.add(db_profile)
        db.commit()
        db.refresh(db_profile)
    
    # Convert DB profile to AthleteProfile
    profile = AthleteProfile(
        id=db_profile.id,
        user_id=db_profile.user_id,
        age=db_profile.age,
        gender=db_profile.gender,
        weight_kg=db_profile.weight_kg,
        height_cm=db_profile.height_cm,
        years_of_experience=db_profile.years_of_experience or 0,
        primary_discipline=db_profile.primary_discipline,
        training_zones_run=db_profile.training_zones_run,
        training_zones_bike=db_profile.training_zones_bike,
        training_zones_swim=db_profile.training_zones_swim,
        available_hours_per_week=db_profile.available_hours_per_week or 8.0,
        auto_avg_hours_last_12_weeks=db_profile.auto_avg_hours_last_12_weeks or 0.0,
        auto_current_weekly_streak_weeks=db_profile.auto_current_weekly_streak_weeks or 0,
        preferred_training_days=db_profile.preferred_training_days,
        zones_last_updated=db_profile.zones_last_updated.isoformat() if db_profile.zones_last_updated else None,
        auto_weeks_analyzed=db_profile.auto_weeks_analyzed or 0,
        auto_longest_weekly_streak_weeks=db_profile.auto_longest_weekly_streak_weeks or 0,
        auto_discipline_hours_per_week=db_profile.auto_discipline_hours_per_week,
    )
    
    # Cache the result
    cache_user_profile(current_user.id, profile.model_dump())
    
    return profile


@router.post("/coach/profile", response_model=AthleteProfile)
async def update_athlete_profile(
    profile: AthleteProfile,
    current_user: models.User = Depends(get_current_user),
    db: "Session" = Depends(get_db),
):
    """
    Обновить и сохранить профиль атлета (ручные поля).
    Авто-поля (auto_*) этим эндпоинтом не считаются.
    """
    # Update DB profile
    from schemas import ProfileUpdate
    profile_update = ProfileUpdate(
        age=profile.age,
        gender=profile.gender,
        weight_kg=profile.weight_kg,
        height_cm=profile.height_cm,
        years_of_experience=profile.years_of_experience,
        primary_discipline=profile.primary_discipline,
        available_hours_per_week=profile.available_hours_per_week,
        preferred_training_days=profile.preferred_training_days,
    )
    updated_profile = crud.update_user_profile(db, current_user.id, profile_update)
    
    # Convert DB profile to AthleteProfile for response
    return AthleteProfile(
        id=updated_profile.id,
        user_id=updated_profile.user_id,
        age=updated_profile.age,
        gender=updated_profile.gender,
        weight_kg=updated_profile.weight_kg,
        height_cm=updated_profile.height_cm,
        years_of_experience=updated_profile.years_of_experience or 0,
        primary_discipline=updated_profile.primary_discipline,
        training_zones_run=updated_profile.training_zones_run,
        training_zones_bike=updated_profile.training_zones_bike,
        training_zones_swim=updated_profile.training_zones_swim,
        available_hours_per_week=updated_profile.available_hours_per_week or 8.0,
        auto_avg_hours_last_12_weeks=updated_profile.auto_avg_hours_last_12_weeks or 0.0,
        auto_current_weekly_streak_weeks=updated_profile.auto_current_weekly_streak_weeks or 0,
        preferred_training_days=updated_profile.preferred_training_days,
        zones_last_updated=updated_profile.zones_last_updated.isoformat() if updated_profile.zones_last_updated else None,
        auto_weeks_analyzed=updated_profile.auto_weeks_analyzed or 0,
        auto_longest_weekly_streak_weeks=updated_profile.auto_longest_weekly_streak_weeks or 0,
        auto_discipline_hours_per_week=updated_profile.auto_discipline_hours_per_week,
    )


@router.post("/coach/profile/auto_from_history", response_model=AthleteProfile)
async def auto_update_profile_from_history(
    weeks: int = 200,
    current_user: models.User = Depends(get_current_user),
    db: "Session" = Depends(get_db),
):
    """
    Автоматически обновляет профиль атлета на основе истории тренировок в Strava.
    """
    from strava_client import fetch_activities_last_n_weeks_for_user
    activities = await fetch_activities_last_n_weeks_for_user(current_user.id, db, weeks=weeks)
    analysis = _analyze_activities_for_profile(activities)

    # Обновляем профиль в базе для текущего пользователя,
    # чтобы на дашборде корректно отображались Avg hours 12w и авто-метрики.
    db_profile = crud.get_user_profile(db, current_user.id)
    if not db_profile:
        db_profile = models.AthleteProfileDB(user_id=current_user.id)
        db.add(db_profile)

    db_profile.auto_weeks_analyzed = analysis["weeks_analyzed"]
    db_profile.auto_current_weekly_streak_weeks = analysis["current_streak"]
    db_profile.auto_longest_weekly_streak_weeks = analysis["longest_streak"]
    db_profile.auto_avg_hours_last_12_weeks = analysis["avg_hours_12w"]
    db_profile.auto_avg_hours_last_52_weeks = analysis["avg_hours_52w"]
    db_profile.auto_discipline_hours_per_week = analysis["discipline_avg_hours"]

    db.commit()
    db.refresh(db_profile)

    # Convert DB profile to AthleteProfile for response
    return AthleteProfile(
        id=db_profile.id,
        user_id=db_profile.user_id,
        age=db_profile.age,
        gender=db_profile.gender,
        weight_kg=db_profile.weight_kg,
        height_cm=db_profile.height_cm,
        years_of_experience=db_profile.years_of_experience or 0,
        primary_discipline=db_profile.primary_discipline,
        training_zones_run=db_profile.training_zones_run,
        training_zones_bike=db_profile.training_zones_bike,
        training_zones_swim=db_profile.training_zones_swim,
        available_hours_per_week=db_profile.available_hours_per_week or 8.0,
        auto_avg_hours_last_12_weeks=db_profile.auto_avg_hours_last_12_weeks or 0.0,
        auto_current_weekly_streak_weeks=db_profile.auto_current_weekly_streak_weeks or 0,
        preferred_training_days=db_profile.preferred_training_days,
        zones_last_updated=db_profile.zones_last_updated.isoformat() if db_profile.zones_last_updated else None,
        auto_weeks_analyzed=db_profile.auto_weeks_analyzed or 0,
        auto_longest_weekly_streak_weeks=db_profile.auto_longest_weekly_streak_weeks or 0,
        auto_discipline_hours_per_week=db_profile.auto_discipline_hours_per_week,
    )


@router.post("/coach/plan")
@limiter.limit("5/hour")  # Max 5 plan generations per hour
async def coach_plan(
    request: Request,
    req: WeeklyPlanRequest,
    current_user: models.User = Depends(get_current_user),
    db: "Session" = Depends(get_db),
):
    """
    Генерация плана тренировок на неделю.
    """
    activities = await fetch_recent_activities_for_coach(current_user.id, db, limit=80)
    plan = await run_weekly_plan(req, activities)

    # Сохраняем план
    save_weekly_plan(req.week_start_date, plan)

    return plan


@router.post("/coach/weekly_plan_email")
async def coach_weekly_plan_email(
    req: WeeklyPlanEmailRequest,
    current_user: models.User = Depends(get_current_user),
    db: "Session" = Depends(get_db),
):
    """
    Генерирует план тренировок на неделю и отправляет на email.
    """
    activities_for_plan = await fetch_recent_activities_for_coach(current_user.id, db, limit=80)

    plan_request = WeeklyPlanRequest(
        goal=req.goal,
        week_start_date=req.week_start_date,
        available_hours_per_week=req.available_hours_per_week,
        notes=req.notes,
    )

    plan_data = await run_weekly_plan(plan_request, activities_for_plan)

    # Сохраняем план
    save_weekly_plan(req.week_start_date, plan_data)

    # Экспортируем план в календарь
    try:
        ics_filepath = export_weekly_plan_to_ics(plan_data)
        calendar_download_url = get_calendar_download_url(ics_filepath)
        calendar_filename = Path(ics_filepath).name
        logger.info("calendar_exported", filename=calendar_filename)
    except Exception as e:
        logger.error("calendar_export_error", error=str(e))
        calendar_download_url = None
        calendar_filename = None

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

    dashboard_url = f"{FRONTEND_BASE_URL.rstrip('/')}/dashboard"

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


@router.post("/coach/plan/export_calendar")
async def export_plan_to_calendar(
    req: WeeklyPlanRequest,
    current_user: models.User = Depends(get_current_user),
    db: "Session" = Depends(get_db),
):
    """
    Генерирует план на неделю и экспортирует в .ics файл для календаря.
    """
    try:
        activities = await fetch_recent_activities_for_coach(current_user.id, db, limit=80)
        plan_data = await run_weekly_plan(req, activities)

        save_weekly_plan(req.week_start_date, plan_data)

        ics_filepath = export_weekly_plan_to_ics(plan_data)
        download_url = get_calendar_download_url(ics_filepath)

        return {
            "status": "success",
            "message": "Training plan exported to calendar",
            "download_url": download_url,
            "filename": Path(ics_filepath).name,
            "week_start_date": req.week_start_date,
            "total_workouts": len(plan_data.get("days", [])),
        }
    except Exception as e:
        logger.error("calendar_export_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


def _format_weekly_plan_for_preview(plan: dict, week_start: dt.date) -> dict:
    """
    Приводит полный weekly plan из GPT к упрощённому виду для дашборда:
    - day: короткое имя дня недели ("Mon", "Tue", ...)
    - title: короткое описание (sport + session_type)
    - duration_minutes: длительность в минутах
    - completed: флаг выполнения (по умолчанию False)
    """
    week_start_str = plan.get("week_start_date") or str(week_start)
    total_hours = plan.get("total_planned_hours", 0)
    raw_days = plan.get("days") or []

    preview_days = []
    for d in raw_days:
        date_str = d.get("date")
        day_label = d.get("day") or ""

        if date_str and not day_label:
            try:
                date_obj = dt.date.fromisoformat(date_str)
                # Mon, Tue, Wed...
                day_label = date_obj.strftime("%a")
            except Exception:
                day_label = ""

        # Строим короткий заголовок
        sport = d.get("sport") or ""
        session_type = d.get("session_type") or ""
        title = d.get("title") or " ".join([sport, session_type]).strip() or "Workout"

        duration = d.get("duration_minutes")
        if duration is None:
            duration = d.get("duration_min")

        preview_days.append(
            {
                "day": day_label,
                "title": title,
                "duration_minutes": duration,
                "completed": d.get("completed", False),
            }
        )

    return {
        "week_start_date": week_start_str,
        "total_planned_hours": float(total_hours) if isinstance(total_hours, (int, float)) else 0.0,
        "days": preview_days,
    }


@router.get("/coach/weekly_plan")
async def get_weekly_plan_preview(
    current_user: models.User = Depends(get_current_user),
    db: "Session" = Depends(get_db),
):
    """
    Returns the current week's plan if available, otherwise mock data.
    """
    try:
        today = dt.date.today()
        week_start = today - dt.timedelta(days=today.weekday())
        plan = load_weekly_plan(str(week_start))
        if plan is None:
            # Mock plan for first-time users
            return {
                "week_start_date": str(week_start),
                "total_planned_hours": 8.0,
                "days": [
                    {"day": "Mon", "title": "Easy Run", "duration_minutes": 45, "completed": True},
                    {"day": "Tue", "title": "Intervals", "duration_minutes": 60},
                    {"day": "Wed", "title": "Recovery", "duration_minutes": 30},
                    {"day": "Thu", "title": "Tempo Run", "duration_minutes": 50},
                    {"day": "Fri", "title": "Rest", "duration_minutes": 0, "completed": True},
                    {"day": "Sat", "title": "Long Run", "duration_minutes": 90},
                    {"day": "Sun", "title": "Easy Bike", "duration_minutes": 60},
                ],
            }

        # Приводим сохранённый план к формату, ожидаемому фронтендом
        return _format_weekly_plan_for_preview(plan, week_start)
    except Exception as e:
        logger.error("weekly_plan_preview_error", error=str(e))
        raise HTTPException(status_code=500, detail="Unable to load weekly plan")


@router.get("/coach/plans/history")
async def get_plan_history():
    """
    Returns a simple history of saved weekly plans from data/plans.
    """
    plans_dir = Path(__file__).parent / "data" / "plans"
    plans_dir.mkdir(parents=True, exist_ok=True)
    history = []
    for path in sorted(plans_dir.glob("*.json"), reverse=True):
        history.append(
            {
                "week_start_date": path.stem,
                "filename": path.name,
            }
        )
    return {"plans": history}


@router.post("/coach/generate_plan")
async def generate_plan_alias(
    req: WeeklyPlanRequest,
    current_user: models.User = Depends(get_current_user),
    db: "Session" = Depends(get_db),
):
    """
    Alias for /coach/plan to match frontend expectation.
    """
    return await coach_plan(req=req, current_user=current_user, db=db)


@router.put("/coach/plan/workout/{workout_id}/complete")
async def complete_workout(
    workout_id: str,
    week_start_date: Optional[str] = None,
):
    """
    Marks a workout as completed in the stored weekly plan.
    If the workout cannot be found, responds with ok to keep UX smooth.
    """
    plans_dir = Path(__file__).parent / "data" / "plans"
    plans_dir.mkdir(parents=True, exist_ok=True)

    # Choose plan file
    if week_start_date:
        target_path = plans_dir / f"{week_start_date}.json"
    else:
        # default to current week
        today = dt.date.today()
        week_start = today - dt.timedelta(days=today.weekday())
        target_path = plans_dir / f"{week_start}.json"

    if not target_path.exists():
        return {"status": "ok", "updated": False, "message": "Plan file not found"}

    try:
        data = json.loads(target_path.read_text(encoding="utf-8"))
    except Exception:
        data = {}

    days = data.get("days", [])
    updated = False
    for day in days:
        if str(day.get("id") or day.get("workout_id") or day.get("title")) == str(workout_id):
            day["completed"] = True
            updated = True
            break

    if updated:
        data["days"] = days
        target_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    return {"status": "ok", "updated": updated}


@router.post("/coach/multi_week_plan")
@limiter.limit("3/hour")  # Max 3 multi-week plans per hour
async def generate_multi_week_training_plan(
    request: Request,
    req: MultiWeekPlanRequest,
    current_user: models.User = Depends(get_current_user),
    db: "Session" = Depends(get_db),
):
    """
    Генерирует долгосрочный план тренировок на N недель с периодизацией.
    """
    try:
        # Проверяем количество недель
        if req.num_weeks < 4 or req.num_weeks > 24:
            raise HTTPException(
                status_code=400,
                detail="Number of weeks must be between 4 and 24",
            )

        # Проверяем объёмы
        if req.peak_hours_per_week < req.base_hours_per_week:
            raise HTTPException(
                status_code=400,
                detail="Peak hours must be greater than base hours",
            )

        # Получаем историю тренировок
        activities = await fetch_recent_activities_for_coach(current_user.id, db, limit=80)

        # Генерируем план
        logger.info("generating_multi_week_plan", weeks=req.num_weeks)

        start_date = dt.date.fromisoformat(req.start_date)

        multi_week_plan = await generate_multi_week_plan(
            goal=req.goal,
            start_date=start_date,
            num_weeks=req.num_weeks,
            base_hours_per_week=req.base_hours_per_week,
            peak_hours_per_week=req.peak_hours_per_week,
            activities=activities,
            notes=req.notes,
        )

        logger.info("multi_week_plan_generated", weeks=req.num_weeks)

        return {
            "status": "success",
            "message": f"Multi-week plan generated for {req.num_weeks} weeks",
            "plan": multi_week_plan.to_dict(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("multi_week_plan_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/coach/multi_week_plan_email")
async def send_multi_week_plan_email(
    req: MultiWeekPlanRequest,
    current_user: models.User = Depends(get_current_user),
    db: "Session" = Depends(get_db),
):
    """
    Генерирует многонедельный план и отправляет на email с красивой визуализацией.
    """
    try:
        # Генерируем план
        activities = await fetch_recent_activities_for_coach(current_user.id, db, limit=80)
        start_date = dt.date.fromisoformat(req.start_date)

        multi_week_plan = await generate_multi_week_plan(
            goal=req.goal,
            start_date=start_date,
            num_weeks=req.num_weeks,
            base_hours_per_week=req.base_hours_per_week,
            peak_hours_per_week=req.peak_hours_per_week,
            activities=activities,
            notes=req.notes,
        )

        # Экспортируем в календарь
        try:
            ics_filepath = export_multi_week_plan_to_ics(multi_week_plan.to_dict())
            calendar_download_url = get_calendar_download_url(ics_filepath)
            calendar_filename = Path(ics_filepath).name
        except Exception as e:
            logger.error("calendar_export_error", error=str(e))
            calendar_download_url = None
            calendar_filename = None

        # Summary table
        summary_table = create_plan_summary_table(multi_week_plan)

        # Phase breakdown
        phases_html = ""
        for phase in multi_week_plan.phases:
            phases_html += f"""
            <div style="margin: 15px 0; padding: 15px; background: #f5f5f5; border-radius: 8px; border-left: 4px solid #4caf50;">
                <div style="font-weight: bold; font-size: 16px; margin-bottom: 8px;">{phase.name} Phase ({phase.duration_weeks} weeks)</div>
                <div style="margin: 5px 0;"><strong>Focus:</strong> {phase.focus}</div>
                <div style="margin: 5px 0;"><strong>Volume:</strong> {phase.volume_multiplier * 100:.0f}% of peak</div>
                <div style="margin: 5px 0;"><strong>Intensity Distribution:</strong> {', '.join([f'{k}: {v}%' for k, v in phase.intensity_distribution.items()])}</div>
            </div>
            """

        html_body = f"""
        <html>
          <head>
            <style>
              body {{
                font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
                max-width: 1200px;
                margin: 40px auto;
                line-height: 1.6;
                color: #333;
              }}
              h1, h2, h3 {{
                margin-bottom: 0.5em;
                color: #2c3e50;
              }}
              .section {{
                margin-bottom: 32px;
                padding: 20px;
                border-radius: 12px;
                background: white;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
              }}
              .header {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 30px;
                border-radius: 12px;
                margin-bottom: 30px;
              }}
              .stats-grid {{
                display: grid;
                grid-template-columns: repeat(4, 1fr);
                gap: 15px;
                margin: 20px 0;
              }}
              .stat-card {{
                padding: 15px;
                background: #f8f9fa;
                border-radius: 8px;
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
            <div class="header">
              <h1>Multi-week Training Plan</h1>
              <p>{req.num_weeks} weeks from {req.start_date}</p>
            </div>

            <div class="section">
              <h2>Overview</h2>
              {summary_table}
            </div>

            <div class="section">
              <h2>Phases</h2>
              {phases_html}
            </div>

            {""
            if not calendar_download_url
            else f'''
            <div class="section">
              <h2>Calendar Export</h2>
              <p>You can import the entire plan into your calendar:</p>
              <a href="{calendar_download_url}" download="{calendar_filename}"
                 style="display:inline-block;padding:10px 20px;background:#2196f3;color:white;
                        text-decoration:none;border-radius:5px;font-weight:600;">
                Download .ics file
              </a>
            </div>
            '''}
          </body>
        </html>
        """

        subject = (
            f"AI Coach – {req.num_weeks}-week training plan "
            f"starting {req.start_date}"
        )
        send_html_email(EMAIL_TO, subject, html_body)

        return {
            "status": "ok",
            "message": f"Multi-week plan for {req.num_weeks} weeks sent to {EMAIL_TO}",
            "num_weeks": req.num_weeks,
            "start_date": req.start_date,
            "calendar_download_url": calendar_download_url,
            "calendar_filename": calendar_filename,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("multi_week_plan_email_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/coach/weekly_report_email")
@limiter.limit("3/hour")  # Max 3 email reports per hour
async def coach_weekly_report_email(
    request: Request,
    req: WeeklyReportEmailRequest,
    current_user: models.User = Depends(get_current_user),
    db: "Session" = Depends(get_db),
):
    """
    Формирует единый еженедельный отчёт с аналитикой и отправляет на email.
    """
    # 1) Прогресс: последние N недель
    from strava_client import fetch_activities_last_n_weeks_for_user
    progress_activities = await fetch_activities_last_n_weeks_for_user(current_user.id, db, weeks=req.progress_weeks)
    progress_result = await run_progress_tracker(
        ProgressRequest(goal=req.goal, weeks=req.progress_weeks),
        progress_activities,
    )

    goal = progress_result["goal"]
    summary = progress_result["summary"]
    evaluation = progress_result["evaluation"]

    # 1.5) Training Load Analytics
    try:
        logger.info("calculating_training_load_analytics")
        training_load_analysis = analyze_training_load(
            activities=progress_activities, weeks_to_analyze=12
        )
    except Exception as e:
        logger.error("training_load_analytics_error", error=str(e))
        training_load_analysis = {
            "current_ctl": 0,
            "current_atl": 0,
            "current_tsb": 0,
            "form_status": "unknown",
            "form_interpretation": {
                "label": "Unknown",
                "description": "Unable to calculate",
                "recommendation": "Please check data",
            },
            "ramp_rate": 0,
            "ramp_rate_status": {
                "label": "Unknown",
                "description": "Unable to calculate",
            },
            "avg_weekly_tss": 0,
        }

    # 1.6) Fatigue Detection
    try:
        logger.info("detecting_fatigue")
        fatigue_report = detect_fatigue(progress_activities)
        fatigue_analysis = fatigue_report.to_dict()
    except Exception as e:
        logger.error("fatigue_detection_error", error=str(e))
        fatigue_analysis = {
            "overall_fatigue_level": "unknown",
            "fatigue_score": 0,
            "indicators": [],
            "needs_recovery_week": False,
            "days_since_rest": 0,
            "consecutive_high_hr_days": 0,
            "recommendations": [
                "Unable to analyze fatigue due to technical error"
            ],
        }

    # 1.7) Performance Predictions
    try:
        logger.info("calculating_performance_predictions")

        current_tsb = training_load_analysis.get("current_tsb", None)

        goal_race_type = req.goal.main_goal_type
        goal_time = req.goal.main_goal_target_time

        prediction_result = predict_for_goal(
            activities=progress_activities,
            goal_race_type=goal_race_type,
            goal_time=goal_time,
            sport="run",  # TODO: определять из goal_race_type
            tsb=current_tsb,
        )

    except Exception as e:
        logger.error("performance_prediction_error", error=str(e))
        prediction_result = {
            "status": "error",
            "error": str(e),
            "prediction": None,
            "recommendations": [
                "Unable to calculate race prediction due to technical error"
            ],
        }

    # 2) План на следующую неделю
    activities_for_plan = await fetch_recent_activities_for_coach(current_user.id, db, limit=80)

    # Load profile from DB instead of JSON file
    db_profile = crud.get_user_profile(db, current_user.id)
    if not db_profile:
        # Load profile from DB
        db_profile = crud.get_user_profile(db, current_user.id)
        if not db_profile:
            # Create default profile if doesn't exist
            db_profile = models.AthleteProfileDB(user_id=current_user.id)
            db.add(db_profile)
            db.commit()
            db.refresh(db_profile)
        
        # Convert DB profile to AthleteProfile for coach
        profile = AthleteProfile(
            id=db_profile.id,
            user_id=db_profile.user_id,
            age=db_profile.age,
            gender=db_profile.gender,
            weight_kg=db_profile.weight_kg,
            height_cm=db_profile.height_cm,
            years_of_experience=db_profile.years_of_experience or 0,
            primary_discipline=db_profile.primary_discipline,
            training_zones_run=db_profile.training_zones_run,
            training_zones_bike=db_profile.training_zones_bike,
            training_zones_swim=db_profile.training_zones_swim,
            available_hours_per_week=db_profile.available_hours_per_week or 8.0,
            auto_avg_hours_last_12_weeks=db_profile.auto_avg_hours_last_12_weeks or 0.0,
            auto_current_weekly_streak_weeks=db_profile.auto_current_weekly_streak_weeks or 0,
            preferred_training_days=db_profile.preferred_training_days,
            zones_last_updated=db_profile.zones_last_updated.isoformat() if db_profile.zones_last_updated else None,
            auto_weeks_analyzed=db_profile.auto_weeks_analyzed or 0,
            auto_longest_weekly_streak_weeks=db_profile.auto_longest_weekly_streak_weeks or 0,
            auto_discipline_hours_per_week=db_profile.auto_discipline_hours_per_week,
        )
    else:
        # Convert DB profile to AthleteProfile
        from athlete_profile import AthleteProfile
        profile = AthleteProfile(
            id=db_profile.id,
            user_id=db_profile.user_id,
            age=db_profile.age,
            gender=db_profile.gender,
            weight_kg=db_profile.weight_kg,
            height_cm=db_profile.height_cm,
            years_of_experience=db_profile.years_of_experience or 0,
            primary_discipline=db_profile.primary_discipline,
            training_zones_run=db_profile.training_zones_run,
            training_zones_bike=db_profile.training_zones_bike,
            training_zones_swim=db_profile.training_zones_swim,
            available_hours_per_week=db_profile.available_hours_per_week or 8.0,
            auto_avg_hours_last_12_weeks=db_profile.auto_avg_hours_last_12_weeks or 0.0,
            auto_current_weekly_streak_weeks=db_profile.auto_current_weekly_streak_weeks or 0,
            preferred_training_days=db_profile.preferred_training_days,
            zones_last_updated=db_profile.zones_last_updated.isoformat() if db_profile.zones_last_updated else None,
            auto_weeks_analyzed=db_profile.auto_weeks_analyzed or 0,
            auto_longest_weekly_streak_weeks=db_profile.auto_longest_weekly_streak_weeks or 0,
            auto_discipline_hours_per_week=db_profile.auto_discipline_hours_per_week,
        )

    plan_request = WeeklyPlanRequest(
        goal=req.goal,
        week_start_date=req.week_start_date,
        available_hours_per_week=req.available_hours_per_week,
        notes=req.notes,
    )

    plan_data = await run_weekly_plan(plan_request, activities_for_plan)

    # Сохраняем план
    save_weekly_plan(req.week_start_date, plan_data)

    # 2.5) Экспортируем план в календарь
    try:
        ics_filepath = export_weekly_plan_to_ics(plan_data)
        calendar_download_url = get_calendar_download_url(ics_filepath)
        calendar_filename = Path(ics_filepath).name
        logger.info("calendar_exported", filename=calendar_filename)
    except Exception as e:
        logger.error("calendar_export_error", error=str(e))
        calendar_download_url = None
        calendar_filename = None

    # 3) План vs факт (прошлая неделя) + Coach Feedback
    last_week_start = dt.date.fromisoformat(req.week_start_date) - dt.timedelta(
        days=7
    )

    plan_vs_fact_summary = None
    coach_feedback = None

    try:
        last_week_plan = load_weekly_plan(str(last_week_start))

        if last_week_plan is None:
            logger.warning("no_plan_for_last_week", week=str(last_week_start))
            plan_vs_fact_summary = None
            coach_feedback = None
        else:
            last_week_end = last_week_start + dt.timedelta(days=7)
            last_week_activities = (
                [
                    act
                    for act in progress_activities
                    if last_week_start
                    <= parse_activity_date(act)
                    < last_week_end
                ]
                if progress_activities
                else []
            )

            plan_vs_fact_summary = compare_plan_with_strava(
                last_week_plan, last_week_activities
            )

            logger.info("generating_coach_feedback", week=str(last_week_start))
            coach_feedback = analyze_week_with_coach(
                plan=last_week_plan,
                actual_activities=last_week_activities,
                comparison_stats=plan_vs_fact_summary,
                athlete_goal={
                    "main_goal_type": req.goal.main_goal_type,
                    "main_goal_target_time": req.goal.main_goal_target_time,
                    "main_goal_race_date": str(req.goal.main_goal_race_date),
                },
            )

    except FileNotFoundError:
        logger.warning(
            "no_plan_for_last_week_file_not_found", week=str(last_week_start)
        )
        plan_vs_fact_summary = None
        coach_feedback = None
    except Exception as e:
        logger.error("coach_feedback_error", error=str(e), week=str(last_week_start))
        plan_vs_fact_summary = None
        coach_feedback = {
            "overall_assessment": "Unable to generate coach feedback due to technical error",
            "execution_quality": "unknown",
            "error": str(e),
        }

    # HTML формирование
    week_start_str = plan_data.get("week_start_date", req.week_start_date)
    total_hours = plan_data.get("total_planned_hours", 0)
    days = plan_data.get("days", [])
    plan_notes = plan_data.get("notes", {})

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
        quality_color = (
            "#4caf50"
            if exec_quality in ["excellent", "good"]
            else ("#ff9800" if exec_quality == "fair" else "#f44336")
        )

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

    dashboard_url = f"{FRONTEND_BASE_URL.rstrip('/')}/dashboard"

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
        <h1>🏊‍♂️🚴‍♂️🏃‍♂️ Weekly Training Report</h1>

        <div class="section">
          <h2>🎯 Goal</h2>
          <div><span class="label">Main goal:</span>
            {goal.get("main_goal_type")} – {goal.get("main_goal_target_time")} on {goal.get("main_goal_race_date")}
          </div>
          <div><span class="label">Secondary goals:</span>
            {", ".join(goal.get("secondary_goals") or []) or "none"}
          </div>
        </div>

        <div class="section" style="background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); color: white; padding: 20px; border-radius: 8px;">
          <h2 style="color: white; margin-top: 0;">📊 Interactive Dashboard</h2>
          <p style="margin: 10px 0;">View your complete training analytics with interactive charts and graphs.</p>
          <a href="{dashboard_url}" style="display: inline-block; padding: 12px 24px; background: white; color: #11998e; text-decoration: none; border-radius: 6px; font-weight: 600; margin-top: 10px;">
            Open Training Dashboard →
          </a>
        </div>

        <div class="section">
          <h2>👤 Athlete Profile</h2>
          <div><span class="label">Level:</span> {profile.level}</div>
          <div><span class="label">Available hours per week:</span> {req.available_hours_per_week:.1f} h</div>
          <div><span class="label">Current weekly streak:</span> {profile.auto_current_weekly_streak_weeks} weeks</div>
          <div><span class="label">Longest weekly streak:</span> {profile.auto_longest_weekly_streak_weeks} weeks</div>
          <div><span class="label">Avg hours (last 12 weeks):</span> {profile.auto_avg_hours_last_12_weeks:.1f} h</div>
          <div><span class="label">Avg hours (last 52 weeks):</span> {profile.auto_avg_hours_last_52_weeks:.1f} h</div>
        </div>

        {plan_vs_fact_html}
        {coach_feedback_html}

        <div class="section">
          <h2>📈 Progress (last {summary.get("weeks_analyzed", 0)} weeks)</h2>
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
          <h2>📅 Plan for week starting {week_start_str}</h2>
          <div><span class="label">Planned volume:</span> {total_hours:.1f} h</div>
          
          {f'<div style="margin: 15px 0; padding: 15px; background: #e3f2fd; border-radius: 8px; border-left: 4px solid #2196f3;"><div style="font-weight: bold; margin-bottom: 8px;">📅 Add to Calendar</div><div style="margin-bottom: 10px;">Import your training plan into Google Calendar, Outlook, or Apple Calendar:</div><a href="{calendar_download_url}" download="{calendar_filename}" style="display: inline-block; padding: 10px 20px; background: #2196f3; color: white; text-decoration: none; border-radius: 5px; font-weight: 600;">Download .ics file</a><div style="margin-top: 10px; font-size: 13px; color: #666;">After downloading, simply open the file to import all workouts into your calendar.</div></div>' if calendar_download_url else ''}<!-- noqa: E501 -->

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
          <p><strong>Overall Focus:</strong> {plan_notes.get("overall_focus", "")}</p>
          <p><strong>Recovery Guidelines:</strong> {plan_notes.get("recovery_guidelines", "")}</p>
          <p><strong>Nutrition Tips:</strong> {plan_notes.get("nutrition_tips", "")}</p>
        </div>
      </body>
    </html>
    """

    subject = req.subject or f"AI Coach – Weekly report (week starting {week_start_str})"

    # Determine recipient: prefer current user's email, fallback to configured EMAIL_TO
    recipient_email = getattr(current_user, "email", None) or EMAIL_TO

    email_sent = False
    email_error: Optional[str] = None

    if not recipient_email:
        # No recipient configured at all - log and continue without raising
        email_error = "No recipient email configured. Set user.email or EMAIL_TO env var."
        logger.error("weekly_report_email_no_recipient", error=email_error)
    else:
        # Try to send email, but don't fail the whole request if email provider
        # is not configured or returns an error. This is critical in hosted
        # environments (Railway/Vercel) where SMTP/Resend may be missing.
        try:
            send_html_email(recipient_email, subject, html_body)
            email_sent = True
        except Exception as e:  # noqa: BLE001
            logger.error("weekly_report_email_send_error", error=str(e))
            email_error = str(e)

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
            "fatigue_analysis": fatigue_analysis,
            "performance_prediction": prediction_result,
            "email_sent": email_sent,
            "email_error": email_error,
            "recipient_email": recipient_email,
        },
    )

    return {
        "status": "ok",
        "message": (
            f"Weekly report sent to {recipient_email}"
            if email_sent and recipient_email
            else "Weekly report generated, but email sending failed"
        ),
        "week_start_date": week_start_str,
        "planned_hours": total_hours,
        "progress_weeks": summary.get("weeks_analyzed", 0),
        "readiness_score": evaluation.get("readiness_score", 0),
        "readiness_label": evaluation.get("score_label", ""),
        "coach_feedback": coach_feedback,
        "plan_vs_fact": plan_vs_fact_summary,
        "training_load_analytics": training_load_analytics,
        "fatigue_analysis": fatigue_analysis,
        "performance_prediction": prediction_result,
        "email_sent": email_sent,
        "email_error": email_error,
        "recipient_email": recipient_email,
    }


@router.get("/downloads/calendar/{filename}")
async def download_calendar_file(
    filename: str,
    current_user: models.User = Depends(get_current_user),
):
    """
    Download calendar file (ICS) for authenticated user
    
    Security: Users can only download their own files
    """
    # Security check: filename must start with user_{user_id}_
    expected_prefix = f"user_{current_user.id}_"
    if not filename.startswith(expected_prefix):
        logger.warning(
            "unauthorized_calendar_access_attempt",
            user_id=current_user.id,
            requested_filename=filename
        )
        raise HTTPException(
            status_code=403,
            detail="Access denied: You can only access your own calendar files"
        )
    
    # Validate filename - prevent directory traversal
    if ".." in filename or "/" in filename or "\\" in filename:
        logger.warning(
            "invalid_calendar_filename",
            user_id=current_user.id,
            filename=filename
        )
        raise HTTPException(
            status_code=400,
            detail="Invalid filename"
        )
    
    # Build file path
    filepath = EXPORTS_DIR / filename
    
    # Check file exists and is a file (not directory)
    if not filepath.exists() or not filepath.is_file():
        logger.info(
            "calendar_file_not_found",
            user_id=current_user.id,
            filename=filename
        )
        raise HTTPException(
            status_code=404,
            detail="Calendar file not found"
        )
    
    logger.info(
        "calendar_download_success",
        user_id=current_user.id,
        filename=filename
    )
    
    return FileResponse(
        path=str(filepath),
        media_type="text/calendar",
        filename=filename,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )
@router.post("/coach/zones/auto_from_activities")
async def calculate_zones_from_activities(
    weeks: int = 260,
    current_user: models.User = Depends(get_current_user),
    db: "Session" = Depends(get_db),
):
    """
    Автоматически рассчитывает тренировочные зоны на основе лучших результатов
    из истории тренировок в Strava.
    """
    from strava_client import fetch_activities_last_n_weeks_for_user
    activities = await fetch_activities_last_n_weeks_for_user(current_user.id, db, weeks=weeks)

    best_efforts = find_best_race_efforts(activities)

    if not best_efforts:
        return {
            "status": "no_race_efforts_found",
            "message": "No race efforts found in activity history. Try manual input.",
            "best_efforts": {},
            "zones_calculated": {
                "run": False,
                "bike": False,
                "swim": False,
            },
            "profile": crud.get_user_profile(db, current_user.id),
        }

    # Load profile from DB
    db_profile = crud.get_user_profile(db, current_user.id)
    if not db_profile:
        db_profile = models.AthleteProfileDB(user_id=current_user.id)
        db.add(db_profile)
        db.commit()
        db.refresh(db_profile)

    # Рассчитываем зоны для бега (приоритет: 10K > HM > 5K > Marathon)
    if "run_10k" in best_efforts:
        effort = best_efforts["run_10k"]
        zones_run = calculate_running_zones_from_race(
            distance_km=effort["distance_km"],
            time_seconds=effort["time_seconds"],
            race_type="10K",
        )
        db_profile.training_zones_run = zones_run.to_dict()
        if isinstance(db_profile.training_zones_run, dict):
            db_profile.training_zones_run["source"] = f"10K race on {effort['date']}"
    elif "run_hm" in best_efforts:
        effort = best_efforts["run_hm"]
        zones_run = calculate_running_zones_from_race(
            distance_km=effort["distance_km"],
            time_seconds=effort["time_seconds"],
            race_type="HM",
        )
        db_profile.training_zones_run = zones_run.to_dict()
        if isinstance(db_profile.training_zones_run, dict):
            db_profile.training_zones_run["source"] = f"Half Marathon on {effort['date']}"
    elif "run_5k" in best_efforts:
        effort = best_efforts["run_5k"]
        zones_run = calculate_running_zones_from_race(
            distance_km=effort["distance_km"],
            time_seconds=effort["time_seconds"],
            race_type="5K",
        )
        db_profile.training_zones_run = zones_run.to_dict()
        if isinstance(db_profile.training_zones_run, dict):
            db_profile.training_zones_run["source"] = f"5K race on {effort['date']}"

    # Плавание
    if "swim_1500m" in best_efforts:
        effort = best_efforts["swim_1500m"]
        css = estimate_css_from_swim(
            distance_m=effort["distance_m"],
            time_seconds=effort["time_seconds"],
        )
        zones_swim = calculate_swimming_zones_from_css(css)
        db_profile.training_zones_swim = zones_swim.to_dict()
        if isinstance(db_profile.training_zones_swim, dict):
            db_profile.training_zones_swim["source"] = f"1500m swim on {effort['date']}"

    db_profile.zones_last_updated = dt.datetime.now(dt.timezone.utc)
    db.commit()
    db.refresh(db_profile)

    return {
        "status": "success",
        "message": "Training zones calculated and saved to profile",
        "best_efforts": best_efforts,
        "zones_calculated": {
            "run": db_profile.training_zones_run is not None,
            "bike": db_profile.training_zones_bike is not None,
            "swim": db_profile.training_zones_swim is not None,
        },
        "profile": db_profile,
    }


@router.post("/zones/calculate")
async def calculate_zones(
    activity_type: str,
    current_user: models.User = Depends(get_current_user),
    db: "Session" = Depends(get_db),
):
    """
    Lightweight auto-calculation of zones per sport.
    If real data is unavailable, returns a simple preset and stores it.
    """
    activity_type = activity_type.lower()

    db_profile = crud.get_user_profile(db, current_user.id)
    if not db_profile:
        db_profile = models.AthleteProfileDB(user_id=current_user.id)
        db.add(db_profile)
        db.commit()
        db.refresh(db_profile)

    now = dt.datetime.utcnow()

    if activity_type == "run":
        db_profile.training_zones_run = {
            "z1": {"min_pace": "5:30", "max_pace": "6:00", "description": "Recovery"},
            "z2": {"min_pace": "5:00", "max_pace": "5:30", "description": "Endurance"},
            "z3": {"min_pace": "4:30", "max_pace": "5:00", "description": "Tempo"},
            "z4": {"min_pace": "4:00", "max_pace": "4:30", "description": "Threshold"},
            "z5": {"min_pace": "3:30", "max_pace": "4:00", "description": "VO2max"},
            "source": "Auto-calculated preset",
        }
    elif activity_type == "bike":
        db_profile.training_zones_bike = {
            "z1": {"min_hr": 120, "max_hr": 140, "description": "Recovery"},
            "z2": {"min_hr": 140, "max_hr": 155, "description": "Endurance"},
            "z3": {"min_hr": 155, "max_hr": 165, "description": "Tempo"},
            "z4": {"min_hr": 165, "max_hr": 175, "description": "Threshold"},
            "z5": {"min_hr": 175, "max_hr": 190, "description": "VO2max"},
            "source": "Auto-calculated preset",
        }
    elif activity_type == "swim":
        db_profile.training_zones_swim = {
            "z1": {"pace": "2:10 /100m", "description": "Recovery"},
            "z2": {"pace": "2:00 /100m", "description": "Endurance"},
            "z3": {"pace": "1:50 /100m", "description": "Tempo"},
            "z4": {"pace": "1:40 /100m", "description": "Threshold"},
            "z5": {"pace": "1:30 /100m", "description": "VO2max"},
            "source": "Auto-calculated preset",
        }
    else:
        raise HTTPException(status_code=400, detail="Unsupported activity_type. Use run/bike/swim.")

    db_profile.zones_last_updated = now
    db.commit()
    db.refresh(db_profile)

    return {
        "status": "ok",
        "zones_last_updated": now.isoformat(),
        "run": db_profile.training_zones_run,
        "bike": db_profile.training_zones_bike,
        "swim": db_profile.training_zones_swim,
    }


@router.post("/coach/zones/manual")
async def calculate_zones_manual(
    input_data: ManualZonesInput,
    current_user: models.User = Depends(get_current_user),
    db: "Session" = Depends(get_db),
):
    """
    Рассчитывает тренировочные зоны на основе ручного ввода данных для текущего пользователя.
    """
    # Load profile from DB
    db_profile = crud.get_user_profile(db, current_user.id)
    if not db_profile:
        db_profile = models.AthleteProfileDB(user_id=current_user.id)
        db.add(db_profile)
        db.commit()
        db.refresh(db_profile)

    # Running zones
    if (
        input_data.run_race_distance_km
        and input_data.run_race_time_seconds
        and input_data.run_race_type
    ):
        zones_run = calculate_running_zones_from_race(
            distance_km=input_data.run_race_distance_km,
            time_seconds=input_data.run_race_time_seconds,
            race_type=input_data.run_race_type,
        )
        db_profile.training_zones_run = zones_run.to_dict()
        if isinstance(db_profile.training_zones_run, dict):
            db_profile.training_zones_run["source"] = (
                f"Manual input: {input_data.run_race_type}"
            )

    # Cycling zones
    if input_data.bike_ftp_watts:
        zones_bike = calculate_cycling_zones_from_ftp(input_data.bike_ftp_watts)
        db_profile.training_zones_bike = zones_bike.to_dict()
        if isinstance(db_profile.training_zones_bike, dict):
            db_profile.training_zones_bike["source"] = "Manual FTP input"

    # Swimming zones
    if input_data.swim_css_pace_per_100m:
        zones_swim = calculate_swimming_zones_from_css(
            input_data.swim_css_pace_per_100m
        )
        db_profile.training_zones_swim = zones_swim.to_dict()
        if isinstance(db_profile.training_zones_swim, dict):
            db_profile.training_zones_swim["source"] = "Manual CSS input"

    db_profile.zones_last_updated = dt.datetime.now(dt.timezone.utc)
    db.commit()
    db.refresh(db_profile)

    return {
        "status": "success",
        "message": "Training zones calculated from manual input and saved",
        "zones_calculated": {
            "run": db_profile.training_zones_run is not None,
            "bike": db_profile.training_zones_bike is not None,
            "swim": db_profile.training_zones_swim is not None,
        },
        "profile": db_profile,
    }


@router.get("/coach/zones")
async def get_training_zones(
    current_user: models.User = Depends(get_current_user),
    db: "Session" = Depends(get_db),
):
    """
    Получить текущие тренировочные зоны для текущего пользователя.
    Поддерживает кеширование для оптимизации производительности.
    """
    # Check cache first
    cached_zones = get_cached_training_zones(current_user.id)
    if cached_zones is not None:
        return cached_zones
    
    # Cache miss - load from DB
    db_profile = crud.get_user_profile(db, current_user.id)
    if not db_profile:
        return {
            "zones_last_updated": None,
            "run": None,
            "bike": None,
            "swim": None,
        }
    
    zones_data = {
        "zones_last_updated": db_profile.zones_last_updated.isoformat() if db_profile.zones_last_updated else None,
        "run": db_profile.training_zones_run,
        "bike": db_profile.training_zones_bike,
        "swim": db_profile.training_zones_swim,
    }
    
    # Cache the result
    cache_training_zones(current_user.id, zones_data)
    
    return zones_data



