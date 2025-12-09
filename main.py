from typing import Optional
import base64
import os

from fastapi import FastAPI, HTTPException, Depends, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy import text

# Rate limiting
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# NEW: Database imports
from database import init_db, get_db

import datetime as dt

from config import (
    STRAVA_CLIENT_ID,
    STRAVA_REDIRECT_URI,
    STRAVA_WEBHOOK_VERIFY_TOKEN,
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
    fetch_activity_by_id,
)
from strava_auth import save_strava_tokens
from models import User
import models
import crud
from auth import get_current_user
from performance_predictions import predict_for_goal, find_best_efforts, predict_race_times
from fatigue_detection import detect_fatigue
from progress import ProgressRequest, run_progress_tracker
from dashboard_generator import generate_dashboard_html
from scheduler import SchedulerConfig, send_automatic_weekly_report
from api_auth import router as auth_router
from api_user import router as user_router
from api_coach import router as coach_router
from api_segments import router as segments_router
from api_nutrition import router as nutrition_router
from segment_sync import sync_segment_efforts_for_activity, detect_personal_records
import threading

# Initialize cache on startup (for logging and connection testing)
# Import with error handling to prevent startup failures
try:
    from cache import cache
except Exception as e:
    # If cache fails to import, create a dummy cache object
    class DummyCache:
        enabled = False
        def get(self, *args, **kwargs): return None
        def set(self, *args, **kwargs): return False
        def delete(self, *args, **kwargs): return False
    cache = DummyCache()
    logger.warning("cache_import_failed", error=str(e))


app = FastAPI(title="AI Triathlon Coach API")

# CORS middleware MUST be added BEFORE rate limiting
# CORS configuration - allow all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Rate limiting setup
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Initialize database (non-blocking, errors are logged but don't crash app)
# This runs in background to not block startup
def init_db_async():
    try:
        init_db()
        logger.info("database_initialized", status="success")
    except Exception as e:
        logger.error("database_initialization_failed", error=str(e))
        # Don't crash - migrations will handle table creation

# Start DB init in background thread to not block startup
db_init_thread = threading.Thread(target=init_db_async, daemon=True)
db_init_thread.start()

# Log cache status on startup
try:
    if cache.enabled:
        logger.info("cache_initialized", status="enabled")
    else:
        logger.info("cache_initialized", status="disabled")
except Exception as e:
    logger.warning("cache_initialization_failed", error=str(e))

# CORS middleware moved to top (after app creation, before rate limiting)

app.include_router(auth_router)
app.include_router(user_router)
app.include_router(coach_router)
app.include_router(segments_router)
app.include_router(nutrition_router, prefix="/nutrition", tags=["nutrition"])


# ===== ANALYTICS =====

@app.get("/analytics/training_load")
@limiter.limit("30/minute")
async def get_training_load_analytics(
    request: Request,
    weeks: int = 12,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Получить комплексный анализ тренировочной нагрузки.
    
    Возвращает:
    - CTL (Chronic Training Load) - fitness
    - ATL (Acute Training Load) - fatigue
    - TSB (Training Stress Balance) - form
    - Ramp Rate - скорость набора формы
    """
    try:
        # Получаем активности для текущего пользователя
        activities = await fetch_activities_last_n_weeks_for_user(current_user.id, db, weeks=weeks)
        
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
async def get_fitness_timeline(
    days: int = 90,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Получить timeline метрик (CTL, ATL, TSB) за период.
    """
    try:
        # Получаем активности за этот период для текущего пользователя
        weeks = (days // 7) + 1
        activities = await fetch_activities_last_n_weeks_for_user(current_user.id, db, weeks=weeks)
        
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
async def get_current_form_status(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Получить текущий статус формы (TSB интерпретация).
    """
    try:
        # Получаем последние 12 недель для текущего пользователя
        activities = await fetch_activities_last_n_weeks_for_user(current_user.id, db, weeks=12)
        
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
async def get_fatigue_analysis(
    weeks: int = 4,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
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
        # Получаем активности за последние N недель для текущего пользователя
        activities = await fetch_activities_last_n_weeks(current_user.id, db, weeks=weeks)
        
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
    weeks: int = 12,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
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
        # Получаем активности для текущего пользователя
        activities = await fetch_activities_last_n_weeks(current_user.id, db, weeks=weeks)
        
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
async def get_all_race_predictions(
    sport: str = "run", 
    weeks: int = 12,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Прогнозы на все стандартные дистанции (5K, 10K, HM, Marathon).
    """
    try:
        # Получаем активности для текущего пользователя
        activities = await fetch_activities_last_n_weeks(current_user.id, db, weeks=weeks)
        
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
async def get_training_dashboard(
    weeks: int = 12,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
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
        # Получаем активности для текущего пользователя
        activities = await fetch_activities_last_n_weeks(current_user.id, db, weeks=weeks)
        
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
async def download_dashboard(
    weeks: int = 12,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Скачивает dashboard как HTML файл.
    """
    try:
        from fastapi.responses import FileResponse
        from pathlib import Path
        
        # Получаем активности для текущего пользователя
        activities = await fetch_activities_last_n_weeks(current_user.id, db, weeks=weeks)
        
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
async def progress_track(
    req: ProgressRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Отслеживание прогресса за последние N недель.
    """
    activities = await fetch_activities_last_n_weeks(current_user.id, db, weeks=req.weeks)
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


@app.get("/auth/strava/login")
async def strava_login(
    state: Optional[str] = None,
):
    """
    Редиректит пользователя на Strava OAuth с state параметром (JWT token).
    """
    from fastapi.responses import RedirectResponse
    
    auth_url = (
        f"https://www.strava.com/oauth/authorize"
        f"?client_id={STRAVA_CLIENT_ID}"
        f"&redirect_uri={STRAVA_REDIRECT_URI}"
        f"&response_type=code"
        f"&scope=read,activity:read_all"
    )
    
    if state:
        auth_url += f"&state={state}"
    
    return RedirectResponse(url=auth_url, status_code=302)


@app.get("/auth/strava/callback")
async def strava_callback(
    request: Request,
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    Обратный вызов от Strava после авторизации.
    Сохраняет токены Strava в БД для текущего пользователя.
    
    Uses 'state' parameter to pass JWT token (encoded in base64) for user identification.
    """
    if error:
        raise HTTPException(status_code=400, detail=f"Strava returned error: {error}")
    
    if not code:
        raise HTTPException(status_code=400, detail="Missing 'code' parameter from Strava")
    
    # Extract user_id from state parameter (JWT token encoded in base64)
    # If state is not provided, try to get token from Authorization header
    user_id = None
    
    if state:
        try:
            # Decode base64 state parameter
            token = base64.b64decode(state).decode('utf-8')
            from auth import decode_access_token
            payload = decode_access_token(token)
            if payload:
                user_id = payload.get("sub")
                logger.info("strava_callback_state_decoded", user_id=user_id)
        except Exception as e:
            logger.error("failed_to_decode_state", error=str(e), state_preview=state[:20] if state else None)
    
    # Fallback: try Authorization header
    if not user_id:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.replace("Bearer ", "")
            from auth import decode_access_token
            payload = decode_access_token(token)
            if payload:
                user_id = payload.get("sub")
    
    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="User identification required. Please provide 'state' parameter with JWT token or Authorization header.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Get user from database
    current_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not current_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    try:
        from strava_client import exchange_code_for_token
        token_data = await exchange_code_for_token(code)
        
        # Save tokens to DB for current user
        athlete_id = str(token_data.get("athlete", {}).get("id", ""))
        access_token = token_data.get("access_token")
        refresh_token = token_data.get("refresh_token")
        expires_at = token_data.get("expires_at")
        
        if not all([athlete_id, access_token, refresh_token, expires_at]):
            logger.error("strava_callback_invalid_token_data", 
                        has_athlete_id=bool(athlete_id),
                        has_access_token=bool(access_token),
                        has_refresh_token=bool(refresh_token),
                        has_expires_at=bool(expires_at))
            raise HTTPException(status_code=400, detail="Invalid token data from Strava")
        
        await save_strava_tokens(
            user_id=current_user.id,
            athlete_id=athlete_id,
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=expires_at,
            db=db
        )
        
        logger.info("strava_connected", user_id=current_user.id, athlete_id=athlete_id)
        
        # Return HTML that redirects to frontend
        frontend_url = os.getenv("FRONTEND_BASE_URL", "http://localhost:3000")
        return HTMLResponse(content=f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Strava Connected</title>
                <script>
                    if (window.opener) {{
                        window.opener.postMessage({{ type: 'strava_connected', success: true }}, '*');
                        window.close();
                    }}
                </script>
            </head>
            <body>
                <p>Strava authorization successful! You can close this window.</p>
                <script>
                    setTimeout(() => {{
                        window.location.href = '{frontend_url}/coach';
                    }}, 2000);
                </script>
            </body>
            </html>
        """)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("strava_callback_error", error=str(e), user_id=current_user.id if 'current_user' in locals() else None)
        raise HTTPException(status_code=500, detail=f"Error processing Strava callback: {str(e)}")


@app.get("/strava/activities")
async def get_strava_activities(
    page: int = 1,
    per_page: int = 50,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Получить активности из Strava для текущего пользователя (с пагинацией).
    """
    from strava_client import fetch_activities
    activities = await fetch_activities(current_user.id, db, page=page, per_page=per_page)
    return {
        "count": len(activities),
        "page": page,
        "per_page": per_page,
        "activities": activities
    }


@app.get("/strava/status")
async def strava_status(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
  """
  Простой статус подключения Strava для текущего пользователя.
  """
  try:
      from strava_auth import get_user_tokens
      tokens = await get_user_tokens(current_user.id, db)
      return {
          "connected": True,
          "athlete_id": tokens.get("athlete_id"),
          "expires_at": int(tokens.get("expires_at").timestamp()) if tokens.get("expires_at") else None,
      }
  except (ValueError, Exception):
      return {"connected": False}


@app.get("/strava/webhook")
async def strava_webhook_verify(
    hub_mode: str = Query(..., alias="hub.mode"),
    hub_verify_token: str = Query(..., alias="hub.verify_token"),
    hub_challenge: str = Query(..., alias="hub.challenge"),
):
    """
    Verify Strava webhook subscription challenge.
    """
    if (
        STRAVA_WEBHOOK_VERIFY_TOKEN
        and hub_mode == "subscribe"
        and hub_verify_token == STRAVA_WEBHOOK_VERIFY_TOKEN
    ):
        return JSONResponse({"hub.challenge": hub_challenge})

    raise HTTPException(status_code=403, detail="Invalid verify token")


@app.post("/strava/webhook")
async def strava_webhook_event(request: Request, db: Session = Depends(get_db)):
    """
    Handle Strava webhook events (activity create/update/delete).
    """
    payload = await request.json()
    logger.info("strava_webhook_event", payload=payload)

    if payload.get("object_type") != "activity":
        return {"status": "ignored"}

    owner_id = payload.get("owner_id")
    try:
        activity_id = int(payload.get("object_id"))
    except (TypeError, ValueError):
        activity_id = None
    aspect_type = payload.get("aspect_type")

    if not owner_id or activity_id is None:
        return {"status": "ignored"}

    user = crud.get_user_by_strava_athlete_id(db, str(owner_id))
    if not user:
        logger.warning("strava_webhook_unknown_owner", owner_id=owner_id)
        return {"status": "ignored"}

    if aspect_type in ("create", "update"):
        try:
            activity = await fetch_activity_by_id(activity_id, user.id, db)
            activity_db = crud.upsert_activity(db, user.id, activity)
            logger.info(
                "strava_webhook_activity_upserted",
                user_id=user.id,
                activity_id=activity_id,
                aspect=aspect_type,
            )
            
            # Sync segment efforts for this activity
            try:
                segments_count = await sync_segment_efforts_for_activity(
                    db=db,
                    user_id=user.id,
                    activity_db=activity_db,
                    strava_activity_id=str(activity_id)
                )
                if segments_count > 0:
                    logger.info("segments_synced", activity_id=activity_id, count=segments_count)
            except Exception as e:
                logger.warning("segment_sync_failed", activity_id=activity_id, error=str(e))
            
            # Detect personal records
            try:
                prs_detected = detect_personal_records(db, user.id, activity_db)
                if prs_detected:
                    logger.info("personal_records_detected", activity_id=activity_id, prs=prs_detected)
            except Exception as e:
                logger.warning("pr_detection_failed", activity_id=activity_id, error=str(e))
                
        except HTTPException:
            raise
        except Exception as exc:
            logger.error(
                "strava_webhook_processing_failed",
                activity_id=activity_id,
                error=str(exc),
            )
            raise HTTPException(
                status_code=500, detail="Failed to process webhook event"
            )
    elif aspect_type == "delete":
        crud.delete_activity_by_strava_id(db, str(activity_id))
        logger.info(
            "strava_webhook_activity_deleted",
            user_id=user.id,
            activity_id=activity_id,
        )
    else:
        logger.info("strava_webhook_aspect_ignored", aspect=aspect_type)

    return {"status": "ok"}

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
    """Health check endpoint для monitoring - must be fast and never fail"""
    try:
        return {
            "status": "healthy",
            "timestamp": dt.datetime.now().isoformat(),
            "version": "1.0.0"
        }
    except Exception as e:
        # Even if something fails, return healthy status
        return {
            "status": "healthy",
            "timestamp": "unknown",
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


