import datetime as dt
from collections import defaultdict
from typing import Dict, Any, List
import json

from utils import normalize_sport, parse_activity_date, activity_duration_minutes
from config import openai_client, GPT_MODEL, logger
from prompts.trainer_prompt import WEEKLY_FEEDBACK_PROMPT


def compare_plan_with_strava(plan: Dict[str, Any], activities: List[dict]) -> Dict[str, Any]:
    """
    plan: dict из run_weekly_plan (как возвращает GPT), включая:
      - "week_start_date": "YYYY-MM-DD"
      - "days": [{ "date", "sport", "duration_min", "priority", ... }, ...]
    activities: список тренировок в формате strava_client.fetch_activities_between.
    """
    week_start_str = plan.get("week_start_date")
    if not week_start_str:
        raise ValueError("Plan must contain 'week_start_date'")
    week_start = dt.date.fromisoformat(week_start_str)
    week_end = week_start + dt.timedelta(days=6)

    days = plan.get("days", []) or []

    # 1. Фильтруем активности за эту же неделю
    week_acts: list[dict] = []
    for a in activities:
        d = parse_activity_date(a)
        if not d:
            continue
        if week_start <= d <= week_end:
            week_acts.append(a)

    # 2. Группируем активности по (date, sport_category)
    acts_by_key: dict[tuple[dt.date, str], list[dict]] = defaultdict(list)
    for a in week_acts:
        d = parse_activity_date(a)
        if not d:
            continue
        sport_cat = normalize_sport(a.get("sport_type"))
        acts_by_key[(d, sport_cat)].append(a)

    sessions: list[dict] = []
    planned_minutes_total = 0
    actual_minutes_from_planned = 0
    unplanned_minutes = 0

    key_total = 0
    key_done = 0

    # 3. Проходим по запланированным дням
    for idx, day in enumerate(days):
        date_str = day.get("date")
        if not date_str:
            continue
        d = dt.date.fromisoformat(date_str)

        sport_raw = day.get("sport")
        sport_cat = normalize_sport(sport_raw)
        planned_min = int(day.get("duration_min") or 0)
        priority = (day.get("priority") or "").lower()
        is_key = priority == "high"

        planned_minutes_total += planned_min
        if is_key:
            key_total += 1

        key = (d, sport_cat)
        candidates = acts_by_key.get(key, [])

        if not candidates:
            sessions.append(
                {
                    "session_id": f"{date_str}-{sport_cat}-{idx}",
                    "date": date_str,
                    "sport": sport_cat,
                    "planned_minutes": planned_min,
                    "actual_minutes": 0,
                    "status": "missed",
                    "is_key_session": is_key,
                    "strava_activity_id": None,
                    "note": "Нет подходящей тренировки в Strava",
                }
            )
            continue

        # Берём активность с длительностью, ближе всего к плану
        best = min(
            candidates,
            key=lambda a: abs(activity_duration_minutes(a) - planned_min),
        )
        actual_min = activity_duration_minutes(best)
        actual_minutes_from_planned += actual_min

        ratio = (actual_min / planned_min) if planned_min > 0 else 0.0
        if ratio >= 1.3:
            status = "overachieved"
        elif ratio >= 0.8:
            status = "done"
        elif ratio >= 0.4:
            status = "shortened"
        else:
            status = "missed"

        if is_key and status in ("done", "overachieved", "shortened"):
            key_done += 1

        sessions.append(
            {
                "session_id": f"{date_str}-{sport_cat}-{idx}",
                "date": date_str,
                "sport": sport_cat,
                "planned_minutes": planned_min,
                "actual_minutes": actual_min,
                "status": status,
                "is_key_session": is_key,
                "strava_activity_id": best.get("id"),
                "note": None,
            }
        )

        # Убираем использованную активность
        acts_by_key[key].remove(best)

    # 4. Остатки — незапланированные тренировки
    for (d, sport_cat), leftovers in acts_by_key.items():
        for a in leftovers:
            m = activity_duration_minutes(a)
            unplanned_minutes += m
            sessions.append(
                {
                    "session_id": "unplanned",
                    "date": d.isoformat(),
                    "sport": sport_cat,
                    "planned_minutes": 0,
                    "actual_minutes": m,
                    "status": "unplanned",
                    "is_key_session": False,
                    "strava_activity_id": a.get("id"),
                    "note": "Незапланированная тренировка",
                }
            )

    planned_hours = round(planned_minutes_total / 60.0, 2)
    actual_hours = round(actual_minutes_from_planned / 60.0, 2)
    unplanned_hours = round(unplanned_minutes / 60.0, 2)
    completion_pct = round(
        (actual_minutes_from_planned / planned_minutes_total * 100.0)
        if planned_minutes_total > 0
        else 0.0,
        1,
    )

    return {
        "week_start_date": week_start_str,
        "week_end_date": week_end.isoformat(),
        "planned_hours": planned_hours,
        "actual_hours": actual_hours,
        "completion_pct": completion_pct,
        "key_sessions_total": key_total,
        "key_sessions_done": key_done,
        "unplanned_hours": unplanned_hours,
        "sessions": sessions,
    }

def analyze_week_with_coach(
    plan: dict,
    actual_activities: List[dict],
    comparison_stats: dict,
    athlete_goal: dict
) -> dict:
    """
    GPT анализирует выполнение недельного плана и даёт персональный feedback.
    
    Args:
        plan: Weekly plan (JSON с days=[...])
        actual_activities: Реальные активности из Strava
        comparison_stats: Результат compare_plan_vs_fact()
        athlete_goal: Цель атлета (main_goal_type, target_time, race_date)
    
    Returns:
        dict с анализом и рекомендациями
    """
    
    # Подготовим данные для GPT
    payload = {
        "week_start_date": plan.get("week_start_date"),
        "athlete_goal": athlete_goal,
        "planned_sessions": len(plan.get("days", [])),
        "planned_hours": plan.get("total_planned_hours"),
        "plan_details": plan.get("days", []),
        "comparison_stats": comparison_stats,
        "actual_activities_summary": [
            {
                "date": act.get("start_date", "")[:10],
                "sport": act.get("sport_type"),
                "name": act.get("name"),
                "duration_min": activity_duration_minutes(act),
                "distance_km": round(act.get("distance", 0) / 1000, 2) if act.get("distance") else None
            }
            for act in actual_activities[:20]  # первые 20 активностей
        ]
    }
    
    # Формируем промпт для GPT
    user_message = f"""Analyze this athlete's week:

ATHLETE'S GOAL:
- Type: {athlete_goal.get('main_goal_type')}
- Target Time: {athlete_goal.get('main_goal_target_time')}
- Race Date: {athlete_goal.get('main_goal_race_date')}

PLANNED WEEK:
{json.dumps(plan.get('days', []), indent=2)}

EXECUTION STATISTICS:
- Completed: {comparison_stats.get('completed')} sessions
- Missed: {comparison_stats.get('missed')} sessions
- Shortened: {comparison_stats.get('shortened')} sessions
- Total sessions planned: {len(plan.get('days', []))}

ACTUAL ACTIVITIES FROM STRAVA:
{json.dumps(payload['actual_activities_summary'], indent=2)}

DETAILED COMPARISON:
{json.dumps(comparison_stats.get('sessions_by_sport', {}), indent=2)}

Provide detailed coach feedback in JSON format as specified.
"""

    try:
        logger.info("weekly_coach_feedback_start", week=plan.get("week_start_date"))
        
        completion = openai_client.chat.completions.create(
            model=GPT_MODEL,
            temperature=0.3,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": WEEKLY_FEEDBACK_PROMPT
                },
                {
                    "role": "user",
                    "content": user_message
                }
            ]
        )
        
        response_json = completion.choices[0].message.content
        analysis = json.loads(response_json)
        
        logger.info(
            "weekly_coach_feedback_success",
            execution_quality=analysis.get("execution_quality"),
            execution_pct=analysis.get("execution_percentage")
        )
        
        return analysis
    
    except json.JSONDecodeError as e:
        logger.error("coach_feedback_invalid_json", error=str(e))
        return {
            "overall_assessment": "Unable to generate feedback due to technical error",
            "execution_quality": "unknown",
            "error": "Failed to parse GPT response"
        }
    
    except Exception as e:
        logger.error("coach_feedback_error", error=str(e))
        return {
            "overall_assessment": "Unable to generate feedback due to technical error",
            "execution_quality": "unknown",
            "error": str(e)
        }