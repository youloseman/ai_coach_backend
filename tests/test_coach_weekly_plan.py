import json
import asyncio

from coach import GoalInput, WeeklyPlanRequest, run_weekly_plan


class _DummyMessage:
    def __init__(self, content: str) -> None:
        self.content = content


class _DummyChoice:
    def __init__(self, content: str) -> None:
        self.message = _DummyMessage(content)


class _DummyCompletion:
    def __init__(self, content: str) -> None:
        self.choices = [_DummyChoice(content)]


class _DummyCompletions:
    def create(self, **kwargs):
        # Return a small but valid weekly plan JSON string
        plan = {
            "week_start_date": "2025-03-10",
            "total_planned_hours": 8.0,
            "days": [
                {
                    "date": "2025-03-10",
                    "sport": "Run",
                    "session_type": "Easy run",
                    "duration_min": 45,
                    "intensity": "Z2",
                    "description": "Easy aerobic run",
                    "primary_goal": "aerobic base",
                    "priority": "medium",
                },
                {
                    "date": "2025-03-11",
                    "sport": "Rest",
                    "session_type": "Rest day",
                    "duration_min": 0,
                    "intensity": "Z1",
                    "description": "Full rest",
                    "primary_goal": "recovery",
                    "priority": "low",
                },
            ],
            "notes": {
                "overall_focus": "Base endurance",
                "recovery_guidelines": "Keep easy days easy",
                "nutrition_tips": "Stay hydrated",
            },
        }
        return _DummyCompletion(json.dumps(plan))


class _DummyChat:
    def __init__(self) -> None:
        self.completions = _DummyCompletions()


class _DummyOpenAIClient:
    def __init__(self) -> None:
        self.chat = _DummyChat()


def test_run_weekly_plan_uses_openai_and_returns_plan(monkeypatch):
    """
    run_weekly_plan should call OpenAI client and return parsed weekly plan dict.
    We mock the openai_client so that no real network calls are performed.
    """
    import coach as coach_module

    dummy_client = _DummyOpenAIClient()
    monkeypatch.setattr(coach_module, "openai_client", dummy_client)

    goal = GoalInput(
        main_goal_type="HALF_IRONMAN",
        main_goal_target_time="4:30",
        main_goal_race_date="2025-06-08",
    )
    req = WeeklyPlanRequest(
        goal=goal,
        week_start_date="2025-03-10",
        available_hours_per_week=10.0,
    )

    activities = [
        {"sport_type": "Run", "distance": 10000, "moving_time": 3600},
    ]

    plan = asyncio.run(run_weekly_plan(req, activities))

    assert plan["week_start_date"] == "2025-03-10"
    assert "days" in plan and len(plan["days"]) == 2
    assert plan["notes"]["overall_focus"] == "Base endurance"


