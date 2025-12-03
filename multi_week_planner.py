"""
Multi-Week Plan Generator
Генерация долгосрочных планов тренировок с периодизацией.
"""

import datetime as dt
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from coach import GoalInput, WeeklyPlanRequest, run_weekly_plan


@dataclass
class TrainingPhase:
    """Фаза тренировочного цикла"""
    name: str  # "Base", "Build", "Peak", "Taper"
    duration_weeks: int
    volume_multiplier: float  # Относительно базового объёма
    intensity_distribution: Dict[str, float]  # % от недельного объёма по интенсивности
    focus: str  # Основной фокус фазы
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "duration_weeks": self.duration_weeks,
            "volume_multiplier": self.volume_multiplier,
            "intensity_distribution": self.intensity_distribution,
            "focus": self.focus
        }


@dataclass
class WeekPlan:
    """План на одну неделю"""
    week_number: int
    week_start_date: str
    phase: str
    is_recovery_week: bool
    planned_hours: float
    volume_change_percent: float  # Относительно предыдущей недели
    notes: str
    days: List[Dict[str, Any]]  # Детальный план по дням
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "week_number": self.week_number,
            "week_start_date": self.week_start_date,
            "phase": self.phase,
            "is_recovery_week": self.is_recovery_week,
            "planned_hours": round(self.planned_hours, 1),
            "volume_change_percent": round(self.volume_change_percent, 1),
            "notes": self.notes,
            "days": self.days
        }


@dataclass
class MultiWeekPlan:
    """Полный план на несколько недель"""
    start_date: str
    race_date: str
    race_type: str
    num_weeks: int
    base_hours_per_week: float
    peak_hours_per_week: float
    phases: List[TrainingPhase]
    weeks: List[WeekPlan]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "start_date": self.start_date,
            "race_date": self.race_date,
            "race_type": self.race_type,
            "num_weeks": self.num_weeks,
            "base_hours_per_week": self.base_hours_per_week,
            "peak_hours_per_week": self.peak_hours_per_week,
            "phases": [p.to_dict() for p in self.phases],
            "weeks": [w.to_dict() for w in self.weeks],
            "total_hours": sum(w.planned_hours for w in self.weeks)
        }


# ===== PERIODIZATION TEMPLATES =====

def get_phase_template(race_type: str, num_weeks: int) -> List[TrainingPhase]:
    """
    Возвращает шаблон периодизации для конкретного типа гонки.
    
    Args:
        race_type: Тип гонки (HALF_IRONMAN, MARATHON, etc.)
        num_weeks: Количество недель до гонки
    
    Returns:
        Список фаз тренировочного цикла
    """
    
    # Базовые шаблоны для разных дистанций
    if race_type == "HALF_IRONMAN" or race_type == "IRONMAN":
        # Длинные дистанции - больше базы
        if num_weeks >= 16:
            return [
                TrainingPhase(
                    name="Base",
                    duration_weeks=6,
                    volume_multiplier=0.85,
                    intensity_distribution={"Z1-Z2": 80, "Z3": 15, "Z4-Z5": 5},
                    focus="Build aerobic base, technique work"
                ),
                TrainingPhase(
                    name="Build 1",
                    duration_weeks=4,
                    volume_multiplier=1.0,
                    intensity_distribution={"Z1-Z2": 70, "Z3": 20, "Z4-Z5": 10},
                    focus="Introduce tempo work, increase volume"
                ),
                TrainingPhase(
                    name="Build 2",
                    duration_weeks=3,
                    volume_multiplier=1.15,
                    intensity_distribution={"Z1-Z2": 65, "Z3": 25, "Z4-Z5": 10},
                    focus="Race-pace intervals, long workouts"
                ),
                TrainingPhase(
                    name="Peak",
                    duration_weeks=2,
                    volume_multiplier=1.2,
                    intensity_distribution={"Z1-Z2": 60, "Z3": 30, "Z4-Z5": 10},
                    focus="Peak volume, race-specific work"
                ),
                TrainingPhase(
                    name="Taper",
                    duration_weeks=1,
                    volume_multiplier=0.5,
                    intensity_distribution={"Z1-Z2": 80, "Z3": 15, "Z4-Z5": 5},
                    focus="Reduce volume, maintain intensity, rest"
                )
            ]
        elif num_weeks >= 12:
            return [
                TrainingPhase(name="Base", duration_weeks=4, volume_multiplier=0.85,
                             intensity_distribution={"Z1-Z2": 80, "Z3": 15, "Z4-Z5": 5},
                             focus="Build aerobic base"),
                TrainingPhase(name="Build", duration_weeks=5, volume_multiplier=1.05,
                             intensity_distribution={"Z1-Z2": 70, "Z3": 20, "Z4-Z5": 10},
                             focus="Increase volume and tempo work"),
                TrainingPhase(name="Peak", duration_weeks=2, volume_multiplier=1.15,
                             intensity_distribution={"Z1-Z2": 65, "Z3": 25, "Z4-Z5": 10},
                             focus="Peak volume"),
                TrainingPhase(name="Taper", duration_weeks=1, volume_multiplier=0.5,
                             intensity_distribution={"Z1-Z2": 80, "Z3": 15, "Z4-Z5": 5},
                             focus="Reduce volume, rest")
            ]
        else:
            # 8-11 недель
            return [
                TrainingPhase(name="Base", duration_weeks=3, volume_multiplier=0.85,
                             intensity_distribution={"Z1-Z2": 80, "Z3": 15, "Z4-Z5": 5},
                             focus="Build aerobic base"),
                TrainingPhase(name="Build", duration_weeks=4, volume_multiplier=1.0,
                             intensity_distribution={"Z1-Z2": 70, "Z3": 20, "Z4-Z5": 10},
                             focus="Build volume and intensity"),
                TrainingPhase(name="Peak", duration_weeks=1, volume_multiplier=1.1,
                             intensity_distribution={"Z1-Z2": 65, "Z3": 25, "Z4-Z5": 10},
                             focus="Peak week"),
                TrainingPhase(name="Taper", duration_weeks=1, volume_multiplier=0.5,
                             intensity_distribution={"Z1-Z2": 80, "Z3": 15, "Z4-Z5": 5},
                             focus="Taper and rest")
            ]
    
    elif race_type == "MARATHON":
        # Марафон - фокус на беге
        if num_weeks >= 16:
            return [
                TrainingPhase(name="Base", duration_weeks=6, volume_multiplier=0.8,
                             intensity_distribution={"Z1-Z2": 85, "Z3": 10, "Z4-Z5": 5},
                             focus="Build running base"),
                TrainingPhase(name="Build", duration_weeks=6, volume_multiplier=1.0,
                             intensity_distribution={"Z1-Z2": 75, "Z3": 15, "Z4-Z5": 10},
                             focus="Long runs + tempo"),
                TrainingPhase(name="Peak", duration_weeks=3, volume_multiplier=1.15,
                             intensity_distribution={"Z1-Z2": 70, "Z3": 20, "Z4-Z5": 10},
                             focus="Peak mileage + race pace"),
                TrainingPhase(name="Taper", duration_weeks=1, volume_multiplier=0.45,
                             intensity_distribution={"Z1-Z2": 85, "Z3": 10, "Z4-Z5": 5},
                             focus="Taper and rest")
            ]
        else:
            return [
                TrainingPhase(name="Base", duration_weeks=4, volume_multiplier=0.85,
                             intensity_distribution={"Z1-Z2": 85, "Z3": 10, "Z4-Z5": 5},
                             focus="Build base"),
                TrainingPhase(name="Build", duration_weeks=4, volume_multiplier=1.0,
                             intensity_distribution={"Z1-Z2": 75, "Z3": 15, "Z4-Z5": 10},
                             focus="Build volume"),
                TrainingPhase(name="Peak", duration_weeks=2, volume_multiplier=1.1,
                             intensity_distribution={"Z1-Z2": 70, "Z3": 20, "Z4-Z5": 10},
                             focus="Peak week"),
                TrainingPhase(name="Taper", duration_weeks=1, volume_multiplier=0.5,
                             intensity_distribution={"Z1-Z2": 85, "Z3": 10, "Z4-Z5": 5},
                             focus="Taper")
            ]
    
    else:  # Shorter races (HM, 10K, Olympic)
        if num_weeks >= 12:
            return [
                TrainingPhase(name="Base", duration_weeks=4, volume_multiplier=0.85,
                             intensity_distribution={"Z1-Z2": 75, "Z3": 15, "Z4-Z5": 10},
                             focus="Build aerobic base"),
                TrainingPhase(name="Build", duration_weeks=5, volume_multiplier=1.05,
                             intensity_distribution={"Z1-Z2": 65, "Z3": 20, "Z4-Z5": 15},
                             focus="Build speed and endurance"),
                TrainingPhase(name="Peak", duration_weeks=2, volume_multiplier=1.1,
                             intensity_distribution={"Z1-Z2": 60, "Z3": 25, "Z4-Z5": 15},
                             focus="Race-specific intervals"),
                TrainingPhase(name="Taper", duration_weeks=1, volume_multiplier=0.55,
                             intensity_distribution={"Z1-Z2": 75, "Z3": 15, "Z4-Z5": 10},
                             focus="Taper")
            ]
        else:
            return [
                TrainingPhase(name="Base", duration_weeks=3, volume_multiplier=0.85,
                             intensity_distribution={"Z1-Z2": 75, "Z3": 15, "Z4-Z5": 10},
                             focus="Build base"),
                TrainingPhase(name="Build", duration_weeks=3, volume_multiplier=1.0,
                             intensity_distribution={"Z1-Z2": 65, "Z3": 20, "Z4-Z5": 15},
                             focus="Build speed"),
                TrainingPhase(name="Peak", duration_weeks=1, volume_multiplier=1.05,
                             intensity_distribution={"Z1-Z2": 60, "Z3": 25, "Z4-Z5": 15},
                             focus="Peak"),
                TrainingPhase(name="Taper", duration_weeks=1, volume_multiplier=0.6,
                             intensity_distribution={"Z1-Z2": 75, "Z3": 15, "Z4-Z5": 10},
                             focus="Taper")
            ]


def calculate_weekly_hours(
    week_number: int,
    phase: TrainingPhase,
    base_hours: float,
    peak_hours: float,
    is_recovery_week: bool
) -> float:
    """
    Рассчитывает объём на неделю с учётом фазы и recovery weeks.
    """
    # Базовый объём для фазы
    phase_hours = base_hours + (peak_hours - base_hours) * (phase.volume_multiplier - 0.85) / 0.35
    
    # Recovery week - снижаем на 30%
    if is_recovery_week:
        return phase_hours * 0.7
    
    return phase_hours


def determine_recovery_weeks(num_weeks: int) -> List[int]:
    """
    Определяет какие недели будут recovery weeks.
    
    Обычно каждая 4-я неделя (3 недель нагрузки, 1 recovery).
    Но не последняя неделя (taper уже является recovery).
    """
    recovery_weeks = []
    
    for week_num in range(1, num_weeks):
        # Каждая 4-я неделя
        if week_num % 4 == 0:
            recovery_weeks.append(week_num)
    
    # Удаляем последнюю неделю если она попала (taper уже recovery)
    if num_weeks - 1 in recovery_weeks:
        recovery_weeks.remove(num_weeks - 1)
    
    return recovery_weeks


async def generate_multi_week_plan(
    goal: GoalInput,
    start_date: dt.date,
    num_weeks: int,
    base_hours_per_week: float,
    peak_hours_per_week: float,
    activities: List[dict],
    notes: Optional[str] = None
) -> MultiWeekPlan:
    """
    Генерирует долгосрочный план тренировок.
    
    Args:
        goal: Цель атлета
        start_date: Дата начала плана
        num_weeks: Количество недель
        base_hours_per_week: Базовый объём (начальный)
        peak_hours_per_week: Пиковый объём
        activities: История тренировок (для контекста)
        notes: Дополнительные пожелания
    
    Returns:
        MultiWeekPlan с детальным планом по неделям
    """
    
    # Получаем шаблон периодизации
    phases = get_phase_template(goal.main_goal_type, num_weeks)
    
    # Определяем recovery weeks
    recovery_weeks = determine_recovery_weeks(num_weeks)
    
    # Генерируем план по неделям
    weeks = []
    current_week_start = start_date
    week_number = 1
    current_phase_index = 0
    weeks_in_current_phase = 0
    
    previous_hours = base_hours_per_week
    
    while week_number <= num_weeks:
        # Определяем текущую фазу
        current_phase = phases[current_phase_index]
        
        # Переходим к следующей фазе?
        if weeks_in_current_phase >= current_phase.duration_weeks:
            current_phase_index = min(current_phase_index + 1, len(phases) - 1)
            current_phase = phases[current_phase_index]
            weeks_in_current_phase = 0
        
        # Recovery week?
        is_recovery = week_number in recovery_weeks
        
        # Рассчитываем объём на неделю
        week_hours = calculate_weekly_hours(
            week_number=week_number,
            phase=current_phase,
            base_hours=base_hours_per_week,
            peak_hours=peak_hours_per_week,
            is_recovery_week=is_recovery
        )
        
        # Генерируем детальный план на неделю через GPT
        week_plan_request = WeeklyPlanRequest(
            goal=goal,
            week_start_date=str(current_week_start),
            available_hours_per_week=week_hours,
            notes=f"{notes or ''}\nPhase: {current_phase.name}. Focus: {current_phase.focus}. {'RECOVERY WEEK - reduce intensity' if is_recovery else ''}"
        )
        
        week_plan_data = await run_weekly_plan(week_plan_request, activities)
        
        # Создаём WeekPlan
        volume_change = ((week_hours - previous_hours) / previous_hours) * 100 if previous_hours > 0 else 0
        
        week_notes = f"{current_phase.name} phase - Week {weeks_in_current_phase + 1}/{current_phase.duration_weeks}"
        if is_recovery:
            week_notes += " (RECOVERY WEEK)"
        
        week_plan = WeekPlan(
            week_number=week_number,
            week_start_date=str(current_week_start),
            phase=current_phase.name,
            is_recovery_week=is_recovery,
            planned_hours=week_hours,
            volume_change_percent=volume_change,
            notes=week_notes,
            days=week_plan_data.get("days", [])
        )
        
        weeks.append(week_plan)
        
        # Следующая неделя
        week_number += 1
        weeks_in_current_phase += 1
        current_week_start += dt.timedelta(days=7)
        previous_hours = week_hours
    
    return MultiWeekPlan(
        start_date=str(start_date),
        race_date=str(goal.main_goal_race_date),
        race_type=goal.main_goal_type,
        num_weeks=num_weeks,
        base_hours_per_week=base_hours_per_week,
        peak_hours_per_week=peak_hours_per_week,
        phases=phases,
        weeks=weeks
    )


def create_plan_summary_table(plan: MultiWeekPlan) -> str:
    """
    Создаёт HTML таблицу с обзором плана по неделям.
    """
    rows = ""
    
    for week in plan.weeks:
        recovery_badge = "🔵 Recovery" if week.is_recovery_week else ""
        volume_arrow = "📈" if week.volume_change_percent > 5 else ("📉" if week.volume_change_percent < -5 else "➡️")
        
        rows += f"""
        <tr style="{'background: #e3f2fd;' if week.is_recovery_week else ''}">
            <td><strong>Week {week.week_number}</strong></td>
            <td>{week.week_start_date}</td>
            <td><span style="display: inline-block; padding: 3px 8px; background: #4caf50; color: white; border-radius: 3px; font-size: 12px;">{week.phase}</span></td>
            <td>{week.planned_hours:.1f}h</td>
            <td>{volume_arrow} {week.volume_change_percent:+.0f}%</td>
            <td>{len(week.days)}</td>
            <td>{recovery_badge}</td>
        </tr>
        """
    
    html = f"""
    <table style="border-collapse: collapse; width: 100%; margin: 20px 0;">
        <thead>
            <tr style="background: #f5f5f5;">
                <th style="border: 1px solid #ddd; padding: 8px; text-align: left;">Week</th>
                <th style="border: 1px solid #ddd; padding: 8px; text-align: left;">Start Date</th>
                <th style="border: 1px solid #ddd; padding: 8px; text-align: left;">Phase</th>
                <th style="border: 1px solid #ddd; padding: 8px; text-align: left;">Hours</th>
                <th style="border: 1px solid #ddd; padding: 8px; text-align: left;">Change</th>
                <th style="border: 1px solid #ddd; padding: 8px; text-align: left;">Workouts</th>
                <th style="border: 1px solid #ddd; padding: 8px; text-align: left;">Notes</th>
            </tr>
        </thead>
        <tbody>
            {rows}
        </tbody>
    </table>
    """
    
    return html