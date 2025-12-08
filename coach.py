import json
from typing import List, Optional

from pydantic import BaseModel
from athlete_profile import load_athlete_profile
from config import (
    openai_client,
    GPT_MODEL,
    GPT_TEMPERATURE_PLANNING,
    GPT_TEMPERATURE_ASSESSMENT,
    logger
)
from prompts.trainer_prompt import TRAINER_SYSTEM_PROMPT


class GoalInput(BaseModel):
    main_goal_type: str          # "HALF_IRONMAN" / "MARATHON" / "10K"
    main_goal_target_time: str   # "4:30" или "3:00"
    main_goal_race_date: str     # "2025-06-08" (ISO date)
    secondary_goals: Optional[list[str]] = None
    comments: Optional[str] = None  # опыт, травмы, ограничения

class WeeklyPlanRequest(BaseModel):
    goal: GoalInput
    week_start_date: str               # "2025-03-10"
    available_hours_per_week: float    # например 8.5
    notes: Optional[str] = None        # пожелания типа "вторник — бассейн, воскресенье — длинная"


async def run_initial_assessment(goal: GoalInput, activities: list[dict]) -> dict:
    """
    Вызывает GPT-4o и возвращает текст оценки + данные целей.
    """
    logger.info("initial_assessment_started", goal_type=goal.main_goal_type, activities_count=len(activities))
    athlete_profile = load_athlete_profile()

    user_payload = {
        "goals": {
            "main_goal_type": goal.main_goal_type,
            "main_goal_target_time": goal.main_goal_target_time,
            "main_goal_race_date": goal.main_goal_race_date,
            "secondary_goals": goal.secondary_goals or [],
        },
        "athlete_profile": athlete_profile.model_dump(),
        "athlete_notes": goal.comments or "",
        "recent_activities": activities,
    }

    try:
        completion = openai_client.chat.completions.create(
            model=GPT_MODEL,
            temperature=GPT_TEMPERATURE_ASSESSMENT,
            messages=[
                {"role": "system", "content": TRAINER_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        "You are PERSONAL COACH. Analyze the athlete's recent training history "
                        "and goals below. Then:\n"
                        "1) Describe current fitness level and main strengths/weaknesses.\n"
                        "2) Assess realism of the main goal and secondary goals.\n"
                        "3) Propose a high-level periodization plan (blocks: base, build, peak, taper) "
                        "until the main race date.\n"
                        "4) Provide key weekly focus and approximate weekly hours for each phase.\n\n"
                        f"DATA (JSON): {json.dumps(user_payload)}"
                    ),
                },
            ],
        )

        answer = completion.choices[0].message.content
        logger.info("initial_assessment_completed", goal_type=goal.main_goal_type, response_length=len(answer))

        return {
            "goals": user_payload["goals"],
            "assessment": answer,
        }
    except Exception as e:
        logger.error("initial_assessment_failed", goal_type=goal.main_goal_type, error=str(e))
        raise

async def run_weekly_plan(req: WeeklyPlanRequest, activities: list[dict]) -> dict:
    """
    Вызывает GPT-4o и возвращает недельный план в виде JSON:
    {
      "week_start_date": "...",
      "total_planned_hours": ...,
      "days": [...],
      "notes": {...}
    }
    """
    logger.info("weekly_plan_generation_started", 
                week_start=req.week_start_date, 
                available_hours=req.available_hours_per_week,
                activities_count=len(activities))
    athlete_profile = load_athlete_profile()

    user_payload = {
        "goals": {
            "main_goal_type": req.goal.main_goal_type,
            "main_goal_target_time": req.goal.main_goal_target_time,
            "main_goal_race_date": req.goal.main_goal_race_date,
            "secondary_goals": req.goal.secondary_goals or [],
        },
        "athlete_profile": athlete_profile.model_dump(),
        "athlete_notes": req.goal.comments or "",
        "week_context": {
            "week_start_date": req.week_start_date,
            "available_hours_per_week": req.available_hours_per_week,
            "extra_notes": req.notes or "",
        },
        "recent_activities": activities,
    }
    try:
        completion = openai_client.chat.completions.create(
            model=GPT_MODEL,
            temperature=GPT_TEMPERATURE_PLANNING,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": TRAINER_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        "You are PERSONAL COACH. Based on the athlete's recent training history and goals "
                        "in the JSON below, generate a realistic training plan for the next 7 days.\n\n"
                        "REQUIREMENTS:\n"
                        "- Respect the available weekly hours.\n"
                        "- Respect principles of progressive overload and recovery.\n"
                        "- Include at least 1 full rest or very easy day.\n"
                        "- Specify sport, session_type, duration_min, intensity, and clear description.\n"
                        "- Mark especially important sessions with priority = 'high'.\n"
                        "- Do NOT create more than one very hard session per sport type per week.\n\n"
                        "Return ONLY a single JSON object with the following structure:\n"
                        "{\n"
                        '  "week_start_date": "YYYY-MM-DD",\n'
                        '  "total_planned_hours": float,\n'
                        '  "days": [\n'
                        "    {\n"
                        '      "date": "YYYY-MM-DD",\n'
                        '      "sport": "Run | Bike | Swim | Strength | Rest",\n'
                        '      "session_type": "Easy run | Interval | Long ride | ...",\n'
                        '      "duration_min": int,\n'
                        '      "intensity": "Z1/Z2/Z3/Z4/Z5 or RPE description",\n'
                        '      "description": "short human-readable instructions",\n'
                        '      "primary_goal": "a short description of the training goal",\n'
                        '      "priority": "low | medium | high"\n'
                        "    }\n"
                        "  ],\n"
                        '  "notes": {\n'
                        '    "overall_focus": "string",\n'
                        '    "recovery_guidelines": "string",\n'
                        '    "nutrition_tips": "string"\n'
                        "  }\n"
                        "}\n\n"
                        f"DATA (JSON): {json.dumps(user_payload)}"
                    ),
                },
            ],
        )

        plan_json = completion.choices[0].message.content
        plan = json.loads(plan_json)
        
        logger.info("weekly_plan_generation_completed", 
                    week_start=req.week_start_date,
                    total_hours=plan.get("total_planned_hours", 0),
                    days_count=len(plan.get("days", [])))

        return plan
    except json.JSONDecodeError as e:
        logger.error("weekly_plan_json_decode_failed", 
                    week_start=req.week_start_date, 
                    error=str(e),
                    response_preview=completion.choices[0].message.content[:200] if 'completion' in locals() else None)
        raise ValueError(f"Failed to parse GPT response as JSON: {e}")
    except Exception as e:
        logger.error("weekly_plan_generation_failed", 
                    week_start=req.week_start_date, 
                    error=str(e))
        raise
    except json.JSONDecodeError as e:
        logger.error("gpt_invalid_json", error=str(e), response=plan_json[:200])
        raise RuntimeError("GPT returned invalid JSON. Please try again.")
    
    except Exception as e:
        logger.error("gpt_error_weekly_plan", error=str(e))
        raise RuntimeError("Unable to generate weekly plan. Please try again later.")