from typing import Optional

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy import text

# NEW: Database imports
from database import init_db, get_db

import datetime as dt

from config import (
    STRAVA_CLIENT_ID,
    STRAVA_REDIRECT_URI,
    logger,
)
from analytics import (
    analyze_training_load,
    calculate_training_metrics,
    get_form_interpretation,
)
from strava_client import (
    exchange_code_for_token,
    fetch_activities,
    fetch_activities_last_n_weeks,
    fetch_activities_last_n_weeks_for_user,
    load_tokens,
)
from strava_auth import save_strava_tokens
from models import User
from auth import get_current_user
from performance_predictions import predict_for_goal, find_best_efforts, predict_race_times
from fatigue_detection import detect_fatigue
from progress import ProgressRequest, run_progress_tracker
from dashboard_generator import generate_dashboard_html
from scheduler import SchedulerConfig, send_automatic_weekly_report
from api_auth import router as auth_router
from api_user import router as user_router
from api_coach import router as coach_router


app = FastAPI(title="AI Triathlon Coach API")

# Initialize database
init_db()

# CORS middleware
# Разрешаем запросы с локального фронта и прод-фронта (Railway).
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # локальный Next.js
        "https://frontend-production-8c08.up.railway.app",  # прод-фронтенд на Railway
        "https://aicoachbackend-production.up.railway.app",  # сам бекенд (на всякий)
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(user_router)
app.include_router(coach_router)


# ===== ANALYTICS =====

@app.get("/analytics/training_load")
async def get_training_load_analytics(weeks: int = 12):
    """
    Получить комплексный анализ тренировочной нагрузки.
    
    Возвращает:
    - CTL (Chronic Training Load) - fitness
    - ATL (Acute Training Load) - fatigue
    - TSB (Training Stress Balance) - form
    - Ramp Rate - скорость набора формы
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
    """
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

@app.get("/analytics/fatigue")
async def get_fatigue_analysis(weeks: int = 4):
    """
    Анализ усталости на основе HR данных и performance metrics.
    
    Детектирует:
    - HR drift (повышение пульса при той же нагрузке)
    - Chronic high HR (3+ дня подряд высокий HR)
    - Pace decline (падение темпа при том же HR)
    - Days since rest (сколько дней без отдыха)
    
    Returns:
        FatigueReport с уровнем усталости и рекомендациями
    """
    try:
        # Получаем активности за последние N недель
        activities = await fetch_activities_last_n_weeks(weeks=weeks)
        
        if not activities:
            return {
                "error": "No activities found",
                "overall_fatigue_level": "unknown",
                "fatigue_score": 0
            }
        
        # Анализируем усталость
        fatigue_report = detect_fatigue(activities)
        
        return {
            "status": "success",
            "fatigue_analysis": fatigue_report.to_dict()
        }
        
    except Exception as e:
        logger.error("fatigue_analysis_error", error=str(e))
        return {
            "error": str(e),
            "overall_fatigue_level": "unknown",
            "fatigue_score": 0
        }

# ===== PERFORMANCE PREDICTIONS =====

@app.get("/analytics/predict_race")
async def predict_race_performance(
    goal_race_type: str = "HM",  # "5K", "10K", "HM", "Marathon"
    goal_time: str = "1:30:00",
    sport: str = "run",
    weeks: int = 12
):
    """
    Прогнозирует время на гонку на основе тренировочных данных.
    
    Args:
        goal_race_type: Тип гонки ("5K", "10K", "HM", "Marathon")
        goal_time: Целевое время (формат "H:MM:SS" или "MM:SS")
        sport: Вид спорта ("run", "bike", "swim")
        weeks: За сколько недель анализировать активности
    
    Returns:
        Прогноз с вероятностью успеха и рекомендациями
    """
    try:
        # Получаем активности
        activities = await fetch_activities_last_n_weeks(weeks=weeks)
        
        if not activities:
            return {
                "error": "No activities found",
                "status": "no_data"
            }
        
        # Получаем текущую форму (TSB)
        try:
            from analytics import calculate_training_metrics
            today = dt.date.today()
            metrics = calculate_training_metrics(activities, today, days=90)
            current_tsb = metrics[-1].tsb if metrics else None
        except:  # noqa: E722
            current_tsb = None
        
        # Делаем прогноз
        prediction_result = predict_for_goal(
            activities=activities,
            goal_race_type=goal_race_type,
            goal_time=goal_time,
            sport=sport,
            tsb=current_tsb
        )
        
        return prediction_result
        
    except Exception as e:
        logger.error("race_prediction_error", error=str(e))
        return {
            "error": str(e),
            "status": "error"
        }


@app.get("/analytics/all_predictions")
async def get_all_race_predictions(sport: str = "run", weeks: int = 12):
    """
    Прогнозы на все стандартные дистанции (5K, 10K, HM, Marathon).
    """
    try:
        # Получаем активности
        activities = await fetch_activities_last_n_weeks(weeks=weeks)
        
        if not activities:
            return {
                "error": "No activities found",
                "predictions": []
            }
        
        # Получаем TSB
        try:
            from analytics import calculate_training_metrics
            today = dt.date.today()
            metrics = calculate_training_metrics(activities, today, days=90)
            current_tsb = metrics[-1].tsb if metrics else None
        except:  # noqa: E722
            current_tsb = None
        
        # Находим лучшие результаты
        best_efforts = find_best_efforts(activities, sport=sport)
        
        if not best_efforts:
            return {
                "status": "no_data",
                "message": "No race efforts found. Complete some benchmark workouts.",
                "predictions": []
            }
        
        # Прогнозируем все дистанции
        predictions = predict_race_times(
            best_efforts=best_efforts,
            race_types=["5K", "10K", "HM", "Marathon"],
            tsb=current_tsb
        )
        
        return {
            "status": "success",
            "sport": sport,
            "current_form": {
                "tsb": current_tsb,
                "form_status": "fresh" if current_tsb and current_tsb > 5 else ("fatigued" if current_tsb and current_tsb < -10 else "neutral")
            } if current_tsb is not None else None,
            "best_efforts": {k: v.to_dict() for k, v in best_efforts.items()},
            "predictions": [p.to_dict() for p in predictions]
        }
        
    except Exception as e:
        logger.error("all_predictions_error", error=str(e))
        return {
            "error": str(e),
            "predictions": []
        }

# ===== TRAINING DASHBOARD =====

@app.get("/dashboard", response_class=HTMLResponse)
async def get_training_dashboard(weeks: int = 12):
    """
    Генерирует интерактивный HTML dashboard с графиками прогресса.
    
    Включает:
    - Performance Management Chart (CTL/ATL/TSB)
    - Weekly Volume Trends
    - Training Distribution
    - Pace Progression
    - Calendar Heatmap
    
    Args:
        weeks: За сколько недель загружать данные (по умолчанию 12)
    
    Returns:
        HTML страница с интерактивными графиками
    """
    try:
        # Получаем активности
        activities = await fetch_activities_last_n_weeks(weeks=weeks)
        
        if not activities:
            return HTMLResponse(content="""
                <html>
                <body style="font-family: Arial; padding: 40px; text-align: center;">
                    <h1>No Data Available</h1>
                    <p>No activities found. Please sync your Strava account first.</p>
                </body>
                </html>
            """)
        
        # Получаем профиль атлета
        from athlete_profile import load_athlete_profile
        profile = load_athlete_profile()
        athlete_name = "Athlete"  # Можно добавить имя в профиль
        
        # Генерируем dashboard
        dashboard_html = generate_dashboard_html(activities, athlete_name=athlete_name)
        
        return HTMLResponse(content=dashboard_html)
        
    except Exception as e:
        logger.error("dashboard_generation_error", error=str(e))
        return HTMLResponse(content=f"""
            <html>
            <body style="font-family: Arial; padding: 40px; text-align: center;">
                <h1>Error Generating Dashboard</h1>
                <p>{str(e)}</p>
            </body>
            </html>
        """, status_code=500)


@app.get("/dashboard/download")
async def download_dashboard(weeks: int = 12):
    """
    Скачивает dashboard как HTML файл.
    """
    try:
        from fastapi.responses import FileResponse
        from pathlib import Path
        
        # Получаем активности
        activities = await fetch_activities_last_n_weeks(weeks=weeks)
        
        if not activities:
            raise HTTPException(status_code=404, detail="No activities found")
        
        # Генерируем dashboard
        from athlete_profile import load_athlete_profile
        profile = load_athlete_profile()
        dashboard_html = generate_dashboard_html(activities, athlete_name="Athlete")
        
        # Сохраняем во временный файл
        dashboard_dir = Path(__file__).resolve().parent / "data" / "dashboards"
        dashboard_dir.mkdir(parents=True, exist_ok=True)
        
        filename = f"training_dashboard_{dt.date.today()}.html"
        filepath = dashboard_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(dashboard_html)
        
        return FileResponse(
            path=str(filepath),
            media_type="text/html",
            filename=filename,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("dashboard_download_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

# ===== PROGRESS TRACKING =====

@app.post("/progress/track")
async def progress_track(req: ProgressRequest):
    """
    Отслеживание прогресса за последние N недель.
    """
    activities = await fetch_activities_last_n_weeks(weeks=req.weeks)
    result = await run_progress_tracker(req, activities)
    return result


# ===== STRAVA OAuth =====

@app.get("/")
async def root():
    """
    Корневой endpoint с ссылкой на авторизацию Strava.
    """
    auth_url = (
        f"https://www.strava.com/oauth/authorize"
        f"?client_id={STRAVA_CLIENT_ID}"
        f"&redirect_uri={STRAVA_REDIRECT_URI}"
        f"&response_type=code"
        f"&scope=read,activity:read_all"
    )
    return HTMLResponse(f"""
        <html>
            <body>
                <h1>AI Coach Backend</h1>
                <p>Для начала работы необходимо авторизоваться в Strava.</p>
                <a href="{auth_url}">Авторизоваться в Strava</a>
            </body>
        </html>
    """)


@app.get("/auth/strava/callback")
async def strava_callback(code: str):
    """
    Обратный вызов от Strava после авторизации.
    Сохраняет токены Strava в файл strava_token.json (глобальный для сервера).
    """
    await exchange_code_for_token(code)
    return JSONResponse(
        content={
            "status": "ok",
            "message": "Strava authorization successful",
            "token_saved": True,
        }
    )


@app.get("/strava/activities")
async def get_strava_activities(page: int = 1, per_page: int = 50):
    """
    Получить активности из Strava (с пагинацией).
    """
    activities = await fetch_activities(page=page, per_page=per_page)
    return {
        "count": len(activities),
        "page": page,
        "per_page": per_page,
        "activities": activities
    }


@app.get("/strava/status")
async def strava_status():
  """
  Простой статус подключения Strava для фронтенда.
  """
  try:
      tokens = load_tokens()
      athlete = tokens.get("athlete", {}) or {}
      return {
          "connected": True,
          "athlete_name": f"{athlete.get('firstname', '')} {athlete.get('lastname', '')}".strip()
          or None,
          "athlete_id": athlete.get("id"),
          "expires_at": tokens.get("expires_at"),
      }
  except Exception:
      return {"connected": False}

@app.get("/scheduler/config")
async def get_scheduler_config():
    """
    Получить текущую конфигурацию scheduler.
    """
    config = SchedulerConfig()
    config.load_from_file()
    return {
        "status": "success",
        "config": config.to_dict()
    }


@app.post("/scheduler/config")
async def update_scheduler_config(
    enabled: bool = True,
    day_of_week: str = "monday",
    time: str = "07:00",
    goal_type: str = "HALF_IRONMAN",
    goal_time: str = "4:30",
    goal_race_date: str = "2026-05-24",
    available_hours_per_week: float = 8.0,
    progress_weeks: int = 8,
    notes: Optional[str] = None
):
    """
    Обновить конфигурацию scheduler.
    """
    config = SchedulerConfig()
    config.enabled = enabled
    config.day_of_week = day_of_week
    config.time = time
    config.goal = {
        "main_goal_type": goal_type,
        "main_goal_target_time": goal_time,
        "main_goal_race_date": goal_race_date,
        "secondary_goals": []
    }
    config.available_hours_per_week = available_hours_per_week
    config.progress_weeks = progress_weeks
    config.notes = notes
    
    config.save_to_file()
    
    return {
        "status": "success",
        "message": "Scheduler configuration updated. Restart scheduler to apply changes.",
        "config": config.to_dict()
    }

@app.get("/health")
async def health_check():
    """Health check endpoint для monitoring"""
    return {
        "status": "healthy",
        "timestamp": dt.datetime.now().isoformat(),
        "version": "1.0.0"
    }

@app.get("/health/db")
async def health_check_db(db: Session = Depends(get_db)):
    """Health check с проверкой БД"""
    try:
        # Простой query чтобы проверить соединение
        db.execute(text("SELECT 1"))
        return {
            "status": "healthy",
            "database": "connected",
            "timestamp": dt.datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database unhealthy: {str(e)}")

@app.post("/scheduler/test")
async def test_scheduler():
    """
    Тестовая отправка weekly report (без ожидания расписания).
    """
    try:
        config = SchedulerConfig()
        config.load_from_file()
        
        result = await send_automatic_weekly_report(config)
        
        if result:
            return {
                "status": "success",
                "message": "Test report sent successfully"
            }
        else:
            return {
                "status": "error",
                "message": "Failed to send test report"
            }
    except Exception as e:
        logger.error("scheduler_test_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


