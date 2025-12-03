# report_storage.py
import json
from pathlib import Path
from typing import Dict, Any
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent
REPORTS_DIR = BASE_DIR / "data" / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


def save_weekly_report(week_start_date: str, payload: Dict[str, Any]) -> None:
    """
    Сохраняем готовый weekly report (всё, что нужно для истории).
    """
    path = REPORTS_DIR / f"{week_start_date}.json"

    data = {
        "week_start_date": week_start_date,
        "saved_at_utc": datetime.utcnow().isoformat(),
        **payload,
    }

    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
