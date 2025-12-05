"""
Automatic Weekly Reports Scheduler
Автоматическая отправка еженедельных отчётов по расписанию.
"""

import schedule
import time
import datetime as dt
import json
from pathlib import Path
import asyncio
from config import logger, EMAIL_TO, FRONTEND_BASE_URL

# Импорты из основного приложения
from coach import GoalInput, WeeklyPlanRequest
from strava_client import fetch_activities_last_n_weeks, fetch_recent_activities_for_coach
from progress import ProgressRequest, run_progress_tracker
from plan_storage import save_weekly_plan
from email_client import send_html_email
from athlete_profile import load_athlete_profile
from utils import parse_activity_date, get_week_start
from analytics import analyze_training_load
from fatigue_detection import detect_fatigue
from performance_predictions import predict_for_goal
from plan_vs_fact import compare_plan_with_strava, analyze_week_with_coach
from report_storage import save_weekly_report
from calendar_export import export_weekly_plan_to_ics, get_calendar_download_url


BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "scheduler_config.json"


class SchedulerConfig:
    """Конфигурация планировщика"""
    
    def __init__(self):
        self.enabled = True
        self.day_of_week = "monday"  # monday, tuesday, etc.
        self.time = "07:00"  # HH:MM format
        self.goal = {
            "main_goal_type": "HALF_IRONMAN",
            "main_goal_target_time": "4:30",
            "main_goal_race_date": "2026-05-24",
            "secondary_goals": []
        }
        self.available_hours_per_week = 8.0
        self.progress_weeks = 8
        self.notes = None
    
    def load_from_file(self):
        """Загрузить конфигурацию из файла"""
        if CONFIG_PATH.exists():
            try:
                with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.enabled = data.get('enabled', True)
                    self.day_of_week = data.get('day_of_week', 'monday')
                    self.time = data.get('time', '07:00')
                    self.goal = data.get('goal', self.goal)
                    self.available_hours_per_week = data.get('available_hours_per_week', 8.0)
                    self.progress_weeks = data.get('progress_weeks', 8)
                    self.notes = data.get('notes', None)
                logger.info("scheduler_config_loaded", config=CONFIG_PATH)
            except Exception as e:
                logger.error("scheduler_config_load_error", error=str(e))
        else:
            # Создаём дефолтный конфиг
            self.save_to_file()
    
    def save_to_file(self):
        """Сохранить конфигурацию в файл"""
        data = {
            "enabled": self.enabled,
            "day_of_week": self.day_of_week,
            "time": self.time,
            "goal": self.goal,
            "available_hours_per_week": self.available_hours_per_week,
            "progress_weeks": self.progress_weeks,
            "notes": self.notes
        }
        
        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.info("scheduler_config_saved", config=CONFIG_PATH)
    
    def to_dict(self):
        return {
            "enabled": self.enabled,
            "day_of_week": self.day_of_week,
            "time": self.time,
            "goal": self.goal,
            "available_hours_per_week": self.available_hours_per_week,
            "progress_weeks": self.progress_weeks,
            "notes": self.notes
        }


async def send_automatic_weekly_report(config: SchedulerConfig):
    """
    Отправляет автоматический weekly report.
    Это основная функция которая вызывается по расписанию.
    """
    try:
        logger.info("automatic_weekly_report_started")
        
        # Определяем дату для плана (следующий понедельник)
        today = dt.date.today()
        days_until_monday = (7 - today.weekday()) % 7
        if days_until_monday == 0:
            days_until_monday = 7  # Если сегодня понедельник, берём следующий
        next_monday = today + dt.timedelta(days=days_until_monday)
        
        # Создаём goal объект
        goal = GoalInput(
            main_goal_type=config.goal['main_goal_type'],
            main_goal_target_time=config.goal['main_goal_target_time'],
            main_goal_race_date=config.goal['main_goal_race_date'],
            secondary_goals=config.goal.get('secondary_goals', [])
        )
        
        # 1) Прогресс
        progress_activities = await fetch_activities_last_n_weeks(weeks=config.progress_weeks)
        progress_result = await run_progress_tracker(
            ProgressRequest(goal=goal, weeks=config.progress_weeks),
            progress_activities,
        )
        
        goal_data = progress_result["goal"]
        summary = progress_result["summary"]
        evaluation = progress_result["evaluation"]
        
        # 1.5) Training Load Analytics
        try:
            training_load_analysis = analyze_training_load(
                activities=progress_activities,
                weeks_to_analyze=12
            )
        except Exception as e:
            logger.error("training_load_analytics_error", error=str(e))
            training_load_analysis = {
                "current_ctl": 0,
                "current_atl": 0,
                "current_tsb": 0,
                "form_status": "unknown",
                "form_interpretation": {"label": "Unknown", "description": "", "recommendation": ""},
                "ramp_rate": 0,
                "ramp_rate_status": {"label": "Unknown", "description": ""},
                "avg_weekly_tss": 0
            }
        
        # 1.6) Fatigue Detection
        try:
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
                "recommendations": ["Unable to analyze fatigue"]
            }
        
        # 1.7) Performance Predictions
        try:
            current_tsb = training_load_analysis.get('current_tsb', None)
            prediction_result = predict_for_goal(
                activities=progress_activities,
                goal_race_type=config.goal['main_goal_type'],
                goal_time=config.goal['main_goal_target_time'],
                sport="run",
                tsb=current_tsb
            )
        except Exception as e:
            logger.error("performance_prediction_error", error=str(e))
            prediction_result = {
                "status": "error",
                "error": str(e),
                "prediction": None,
                "recommendations": []
            }
        
        # 2) План на следующую неделю
        activities_for_plan = await fetch_recent_activities_for_coach(limit=80)
        profile = load_athlete_profile()
        
        from coach import run_weekly_plan
        plan_request = WeeklyPlanRequest(
            goal=goal,
            week_start_date=str(next_monday),
            available_hours_per_week=config.available_hours_per_week,
            notes=config.notes
        )
        
        plan_data = await run_weekly_plan(plan_request, activities_for_plan)
        save_weekly_plan(str(next_monday), plan_data)
        
        # Экспорт в календарь
        try:
            ics_filepath = export_weekly_plan_to_ics(plan_data)
            calendar_download_url = get_calendar_download_url(ics_filepath)
            calendar_filename = Path(ics_filepath).name
        except Exception as e:
            logger.error("calendar_export_error", error=str(e))
            calendar_download_url = None
            calendar_filename = None
        
        # 3) План vs факт (прошлая неделя)
        last_week_start = next_monday - dt.timedelta(days=14)
        
        plan_vs_fact_summary = None
        coach_feedback = None
        
        try:
            from plan_storage import load_weekly_plan
            last_week_plan = load_weekly_plan(str(last_week_start))
            
            if last_week_plan:
                last_week_end = last_week_start + dt.timedelta(days=7)
                last_week_activities = [
                    act for act in progress_activities
                    if last_week_start <= parse_activity_date(act) < last_week_end
                ] if progress_activities else []
                
                plan_vs_fact_summary = compare_plan_with_strava(last_week_plan, last_week_activities)
                
                coach_feedback = analyze_week_with_coach(
                    plan=last_week_plan,
                    actual_activities=last_week_activities,
                    comparison_stats=plan_vs_fact_summary,
                    athlete_goal={
                        "main_goal_type": config.goal['main_goal_type'],
                        "main_goal_target_time": config.goal['main_goal_target_time'],
                        "main_goal_race_date": config.goal['main_goal_race_date']
                    }
                )
        except Exception as e:
            logger.error("plan_vs_fact_error", error=str(e))
        
        # Формируем HTML (упрощённая версия - можно скопировать из main.py)
        week_start_str = plan_data.get("week_start_date", str(next_monday))
        
        subject = f"🏊‍♂️🚴‍♂️🏃‍♂️ AI Coach – Weekly Report (week starting {week_start_str})"
        dashboard_url = f"{FRONTEND_BASE_URL.rstrip('/')}/dashboard"
        
        # ВАЖНО: Здесь используется упрощённый HTML
        # Для полного HTML скопируйте код из coach_weekly_report_email в main.py
        html_body = f"""
        <html>
        <body style="font-family: Arial; padding: 20px;">
            <h1>Weekly Training Report (Automatic)</h1>
            <p>Report generated automatically on {dt.date.today()}</p>
            
            <h2>Goal</h2>
            <p>{config.goal['main_goal_type']} - {config.goal['main_goal_target_time']} on {config.goal['main_goal_race_date']}</p>
            
            <h2>This Week's Plan</h2>
            <p>Planned volume: {plan_data.get('total_planned_hours', 0):.1f} hours</p>
            <p>{len(plan_data.get('days', []))} workouts scheduled</p>
            
            <h2>Current Form</h2>
            <p>CTL: {training_load_analysis.get('current_ctl', 0)} | ATL: {training_load_analysis.get('current_atl', 0)} | TSB: {training_load_analysis.get('current_tsb', 0)}</p>
            <p>Status: {training_load_analysis.get('form_interpretation', {}).get('label', 'Unknown')}</p>
            
            <h2>Fatigue Level</h2>
            <p>{fatigue_analysis.get('overall_fatigue_level', 'unknown').upper()} (Score: {fatigue_analysis.get('fatigue_score', 0)}/100)</p>
            
            <p><a href="{dashboard_url}">View Full Dashboard</a></p>
            
            <p style="margin-top: 40px; color: #666;">
                This is an automatic report. To customize, edit scheduler_config.json or disable automatic reports.
            </p>
        </body>
        </html>
        """
        
        # Отправляем email
        send_html_email(EMAIL_TO, subject, html_body)
        
        # Сохраняем отчёт
        save_weekly_report(
            week_start_str,
            {
                "goal": goal_data,
                "summary": summary,
                "evaluation": evaluation,
                "plan": plan_data,
                "plan_vs_fact": plan_vs_fact_summary,
                "coach_feedback": coach_feedback,
                "training_load_analytics": training_load_analysis,
                "fatigue_analysis": fatigue_analysis,
                "performance_prediction": prediction_result,
                "automatic": True,
                "sent_at": str(dt.datetime.now())
            },
        )
        
        logger.info("automatic_weekly_report_sent", week=week_start_str)
        return True
        
    except Exception as e:
        logger.error("automatic_weekly_report_error", error=str(e))
        return False


def job_wrapper(config: SchedulerConfig):
    """Wrapper для запуска async функции из schedule"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(send_automatic_weekly_report(config))
        return result
    finally:
        loop.close()


def start_scheduler():
    """
    Запускает scheduler который работает в бесконечном цикле.
    """
    config = SchedulerConfig()
    config.load_from_file()
    
    if not config.enabled:
        logger.info("scheduler_disabled", message="Automatic reports are disabled in config")
        return
    
    logger.info("scheduler_started", 
                day=config.day_of_week, 
                time=config.time,
                goal=config.goal['main_goal_type'])
    
    # Настраиваем расписание
    day_of_week = config.day_of_week.lower()
    
    if day_of_week == "monday":
        schedule.every().monday.at(config.time).do(job_wrapper, config)
    elif day_of_week == "tuesday":
        schedule.every().tuesday.at(config.time).do(job_wrapper, config)
    elif day_of_week == "wednesday":
        schedule.every().wednesday.at(config.time).do(job_wrapper, config)
    elif day_of_week == "thursday":
        schedule.every().thursday.at(config.time).do(job_wrapper, config)
    elif day_of_week == "friday":
        schedule.every().friday.at(config.time).do(job_wrapper, config)
    elif day_of_week == "saturday":
        schedule.every().saturday.at(config.time).do(job_wrapper, config)
    elif day_of_week == "sunday":
        schedule.every().sunday.at(config.time).do(job_wrapper, config)
    else:
        logger.error("invalid_day_of_week", day=day_of_week)
        return
    
    print(f"✅ Scheduler started! Weekly reports will be sent every {day_of_week.title()} at {config.time}")
    print(f"📧 Reports will be sent to: {EMAIL_TO}")
    print(f"🎯 Goal: {config.goal['main_goal_type']} - {config.goal['main_goal_target_time']}")
    print(f"\nPress Ctrl+C to stop the scheduler.\n")
    
    # Бесконечный цикл
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # Проверяем каждую минуту
    except KeyboardInterrupt:
        logger.info("scheduler_stopped", message="Scheduler stopped by user")
        print("\n❌ Scheduler stopped.")


if __name__ == "__main__":
    start_scheduler()