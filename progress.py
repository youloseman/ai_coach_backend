import json
import datetime as dt
from typing import Optional, List, Dict, Any

from pydantic import BaseModel
from athlete_profile import load_athlete_profile
from config import openai_client, GPT_MODEL, GPT_TEMPERATURE_PROGRESS
from coach import GoalInput
from prompts.trainer_prompt import TRAINER_SYSTEM_PROMPT
from utils import normalize_sport, parse_activity_date, activity_duration_hours


class ProgressRequest(BaseModel):
    goal: GoalInput
    weeks: int = 8  # по умолчанию смотрим 8 недель


def aggregate_by_week(activities: List[dict]) -> List[dict]:
    """
    Группируем тренировки по неделям (понедельник–воскресенье),
    считаем часы по видам спорта и всего.
    """
    weeks: Dict[str, Dict[str, Any]] = {}

    for a in activities:
        raw_start = a.get("start_date")
        if not raw_start:
            continue
        try:
            dt_start = dt.datetime.fromisoformat(raw_start.replace("Z", "+00:00"))
        except ValueError:
            continue

        # начало недели (понедельник)
        week_start = dt_start.date() - dt.timedelta(days=dt_start.weekday())
        key = week_start.isoformat()

        moving_time_s = a.get("moving_time_s") or a.get("moving_time") or 0
        hours = float(moving_time_s) / 3600.0

        sport = normalize_sport(a.get("sport_type"))

        if key not in weeks:
            weeks[key] = {
                "week_start_date": key,
                "total_hours": 0.0,
                "run_hours": 0.0,
                "bike_hours": 0.0,
                "swim_hours": 0.0,
                "other_hours": 0.0,
                "num_sessions": 0,
            }

        w = weeks[key]
        w["total_hours"] += hours
        if sport == "run":
            w["run_hours"] += hours
        elif sport == "bike":
            w["bike_hours"] += hours
        elif sport == "swim":
            w["swim_hours"] += hours
        else:
            w["other_hours"] += hours
        w["num_sessions"] += 1

    # сортируем по дате недели (от старой к новой)
    result = sorted(weeks.values(), key=lambda x: x["week_start_date"])
    return result


async def run_progress_tracker(req: ProgressRequest, activities: List[dict]) -> dict:
    """
    Делает агрегаты по неделям и спрашивает у GPT-коуча:
    - оценка реалистичности цели (0–100)
    - текстовый отчёт
    """
    weekly = aggregate_by_week(activities)

    num_weeks = len(weekly) if weekly else 0
    total_hours = sum(w["total_hours"] for w in weekly) if weekly else 0.0
    avg_hours = total_hours / num_weeks if num_weeks > 0 else 0.0

    avg_run = sum(w["run_hours"] for w in weekly) / num_weeks if num_weeks > 0 else 0.0
    avg_bike = sum(w["bike_hours"] for w in weekly) / num_weeks if num_weeks > 0 else 0.0
    avg_swim = sum(w["swim_hours"] for w in weekly) / num_weeks if num_weeks > 0 else 0.0

    best_week = max(weekly, key=lambda w: w["total_hours"], default=None)

    weeks_over_6h = sum(1 for w in weekly if w["total_hours"] >= 6.0)
    consistency_ratio = weeks_over_6h / num_weeks if num_weeks > 0 else 0.0

    summary = {
        "weeks_analyzed": num_weeks,
        "total_hours": total_hours,
        "avg_hours_per_week": avg_hours,
        "avg_run_hours_per_week": avg_run,
        "avg_bike_hours_per_week": avg_bike,
        "avg_swim_hours_per_week": avg_swim,
        "consistency_ratio_weeks_over_6h": consistency_ratio,
        "best_week": best_week,
        "weekly_breakdown": weekly,
    }

    athlete_profile = load_athlete_profile()

    payload = {
        "goal": {
            "main_goal_type": req.goal.main_goal_type,
            "main_goal_target_time": req.goal.main_goal_target_time,
            "main_goal_race_date": req.goal.main_goal_race_date,
            "secondary_goals": req.goal.secondary_goals or [],
        },
        "athlete_profile": athlete_profile.model_dump(),
        "athlete_notes": req.goal.comments or "",
        "summary": summary,
    }
    

    completion = openai_client.chat.completions.create(
        model=GPT_MODEL,
        temperature=GPT_TEMPERATURE_PROGRESS,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": (
                    TRAINER_SYSTEM_PROMPT
                    + "\n\nYou are now acting as a PROGRESS TRACKER. "
                    "You evaluate how realistic the athlete's main goal is given the last weeks of training."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Below is the athlete's TRIATHLON / ENDURANCE goal and aggregated training load "
                    "for the last weeks. You MUST respond with a single JSON object with this structure:\n"
                    "{\n"
                    '  "readiness_score": float,   // 0–100, where 0 = almost impossible, 100 = very realistic\n'
                    '  "score_label": "low | medium | high",\n'
                    '  "comment": "short summary in 3-5 sentences",\n'
                    '  "main_risks": ["string", ...],\n'
                    '  "recommendations": ["string", ...]\n'
                    "}\n\n"
                    "Consider:\n"
                    "- average weekly volume vs typical requirements for the given goal/time,\n"
                    "- balance between swim/bike/run,\n"
                    "- consistency across weeks,\n"
                    "- how close the race date is (time remaining).\n\n"
                    f"DATA (JSON): {json.dumps(payload)}"
                ),
            },
        ],
    )

    content = completion.choices[0].message.content
    result = json.loads(content)

    return {
        "goal": payload["goal"],
        "summary": summary,
        "evaluation": result,
    }
