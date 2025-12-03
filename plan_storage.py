# plan_storage.py
import json
from pathlib import Path
from typing import Optional, Dict, Any

BASE_DIR = Path(__file__).resolve().parent
PLANS_DIR = BASE_DIR / "data" / "plans"
PLANS_DIR.mkdir(parents=True, exist_ok=True)


def save_weekly_plan(week_start_date: str, plan: Dict[str, Any]) -> None:
    """
    Сохраняем план недели в data/plans/{week_start_date}.json.
    Формат week_start_date: 'YYYY-MM-DD'
    """
    path = PLANS_DIR / f"{week_start_date}.json"
    with path.open("w", encoding="utf-8") as f:
        json.dump(plan, f, ensure_ascii=False, indent=2)


def load_weekly_plan(week_start_date: str) -> Optional[Dict[str, Any]]:
    """
    Загружаем план недели, если он есть. Иначе возвращаем None.
    """
    path = PLANS_DIR / f"{week_start_date}.json"
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)
