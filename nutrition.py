"""
Nutrition calculator for triathletes.
Calculates daily macros, race day fueling plans, and recovery nutrition.
"""
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass
class NutritionTargets:
    """Daily nutrition targets"""
    calories: float  # kcal
    carbs_grams: float  # grams
    protein_grams: float  # grams
    fat_grams: float  # grams
    
    def to_dict(self) -> Dict[str, float]:
        return {
            "calories": round(self.calories, 0),
            "carbs_grams": round(self.carbs_grams, 1),
            "protein_grams": round(self.protein_grams, 1),
            "fat_grams": round(self.fat_grams, 1),
        }


@dataclass
class FuelingStrategy:
    """Single fueling event during race"""
    time_minutes: int  # Minutes into race
    type: str  # "gel", "drink", "bar", "banana", etc.
    carbs_grams: float
    calories: float
    notes: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "time_minutes": self.time_minutes,
            "type": self.type,
            "carbs_grams": round(self.carbs_grams, 1),
            "calories": round(self.calories, 0),
            "notes": self.notes,
        }


@dataclass
class RaceFuelingPlan:
    """Complete race day fueling strategy"""
    race_type: str
    race_duration_hours: float
    total_carbs_grams: float
    total_calories: float
    fueling_strategies: List[FuelingStrategy]
    pre_race_meals: List[Dict[str, Any]]
    post_race_recovery: Dict[str, Any]
    notes: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "race_type": self.race_type,
            "race_duration_hours": round(self.race_duration_hours, 2),
            "total_carbs_grams": round(self.total_carbs_grams, 1),
            "total_calories": round(self.total_calories, 0),
            "fueling_strategies": [s.to_dict() for s in self.fueling_strategies],
            "pre_race_meals": self.pre_race_meals,
            "post_race_recovery": self.post_race_recovery,
            "notes": self.notes,
        }


# Activity level multipliers for BMR (Basal Metabolic Rate)
ACTIVITY_MULTIPLIERS = {
    "sedentary": 1.2,
    "light": 1.375,
    "moderate": 1.55,
    "active": 1.725,
    "very_active": 1.9,
}


def calculate_bmr(weight_kg: float, height_cm: float, age: int, gender: str = "male") -> float:
    """
    Calculate Basal Metabolic Rate using Mifflin-St Jeor equation.
    
    Args:
        weight_kg: Weight in kilograms
        height_cm: Height in centimeters
        age: Age in years
        gender: "male" or "female"
    
    Returns:
        BMR in kcal/day
    """
    if gender.lower() == "female":
        bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age - 161
    else:  # male
        bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age + 5
    
    return max(bmr, 1200)  # Minimum BMR


def calculate_daily_calories(
    weight_kg: float,
    height_cm: float,
    age: int,
    gender: str = "male",
    activity_level: str = "active",
    training_hours_per_week: float = 8.0,
    goal_type: str = "maintain"
) -> float:
    """
    Calculate daily calorie needs.
    
    Args:
        weight_kg: Weight in kg
        height_cm: Height in cm
        age: Age in years
        gender: "male" or "female"
        activity_level: Activity level (see ACTIVITY_MULTIPLIERS)
        training_hours_per_week: Hours of training per week
        goal_type: "maintain", "lose_weight", "gain_muscle", "performance"
    
    Returns:
        Daily calories in kcal
    """
    bmr = calculate_bmr(weight_kg, height_cm, age, gender)
    
    # Adjust activity level based on training
    if training_hours_per_week > 10:
        activity_multiplier = ACTIVITY_MULTIPLIERS.get("very_active", 1.9)
    elif training_hours_per_week > 6:
        activity_multiplier = ACTIVITY_MULTIPLIERS.get("active", 1.725)
    else:
        activity_multiplier = ACTIVITY_MULTIPLIERS.get(activity_level, 1.55)
    
    tdee = bmr * activity_multiplier
    
    # Add calories for training (roughly 500-800 kcal per hour)
    training_calories_per_day = (training_hours_per_week / 7) * 600
    total_calories = tdee + training_calories_per_day
    
    # Adjust for goals
    if goal_type == "lose_weight":
        total_calories *= 0.85  # 15% deficit
    elif goal_type == "gain_muscle":
        total_calories *= 1.15  # 15% surplus
    elif goal_type == "performance":
        total_calories *= 1.05  # 5% surplus for performance
    
    return round(total_calories, 0)


def calculate_daily_macros(
    calories: float,
    goal_type: str = "performance",
    training_hours_per_week: float = 8.0
) -> NutritionTargets:
    """
    Calculate daily macronutrient targets.
    
    Args:
        calories: Daily calorie target
        goal_type: "maintain", "lose_weight", "gain_muscle", "performance"
        training_hours_per_week: Hours of training per week
    
    Returns:
        NutritionTargets with carbs, protein, fat
    """
    # Protein: 1.6-2.2 g/kg for athletes (use 2.0 g/kg as default)
    # For 70kg athlete: 140g protein = 560 kcal
    # We'll use percentage-based approach for flexibility
    
    if goal_type == "performance" or training_hours_per_week > 8:
        # High carb for endurance athletes
        carbs_percent = 0.55  # 55% carbs
        protein_percent = 0.20  # 20% protein
        fat_percent = 0.25  # 25% fat
    elif goal_type == "gain_muscle":
        # Higher protein for muscle gain
        carbs_percent = 0.45
        protein_percent = 0.30
        fat_percent = 0.25
    elif goal_type == "lose_weight":
        # Moderate carbs, higher protein
        carbs_percent = 0.40
        protein_percent = 0.30
        fat_percent = 0.30
    else:  # maintain
        carbs_percent = 0.50
        protein_percent = 0.25
        fat_percent = 0.25
    
    # Calculate grams (carbs and protein = 4 kcal/g, fat = 9 kcal/g)
    carbs_grams = (calories * carbs_percent) / 4
    protein_grams = (calories * protein_percent) / 4
    fat_grams = (calories * fat_percent) / 9
    
    return NutritionTargets(
        calories=calories,
        carbs_grams=round(carbs_grams, 1),
        protein_grams=round(protein_grams, 1),
        fat_grams=round(fat_grams, 1),
    )


def calculate_race_fueling_plan(
    race_type: str,
    race_duration_hours: float,
    weight_kg: float = 70.0
) -> RaceFuelingPlan:
    """
    Generate race day fueling plan.
    
    Args:
        race_type: "5K", "10K", "HM", "Marathon", "Ironman", etc.
        race_duration_hours: Expected race duration
        weight_kg: Athlete weight
    
    Returns:
        RaceFuelingPlan with complete strategy
    """
    # Pre-race meal (3-4 hours before)
    pre_race_meals = [
        {
            "timing_hours_before": 3,
            "description": "Pre-race breakfast",
            "carbs_grams": 100,
            "protein_grams": 20,
            "fat_grams": 10,
            "calories": 560,
            "examples": "Oatmeal with banana, toast with honey, coffee"
        }
    ]
    
    # For short races (< 1 hour), minimal fueling needed
    if race_duration_hours < 1.0:
        return RaceFuelingPlan(
            race_type=race_type,
            race_duration_hours=race_duration_hours,
            total_carbs_grams=0,
            total_calories=0,
            fueling_strategies=[],
            pre_race_meals=pre_race_meals,
            post_race_recovery={
                "within_30min": {
                    "carbs_grams": 50,
                    "protein_grams": 20,
                    "calories": 300,
                    "examples": "Chocolate milk, recovery shake, banana with protein"
                },
                "within_2hours": {
                    "carbs_grams": 50,
                    "protein_grams": 30,
                    "calories": 400,
                    "examples": "Full meal with carbs and protein"
                }
            },
            notes=f"For {race_type}, no fueling needed during race. Focus on hydration."
        )
    
    # For longer races, calculate fueling needs
    # Target: 30-60g carbs per hour for endurance events
    # For very long events (>3h): 60-90g carbs per hour
    
    carbs_per_hour = 45  # Default
    if race_duration_hours > 3.0:
        carbs_per_hour = 60  # Ironman, ultra
    elif race_duration_hours > 2.0:
        carbs_per_hour = 50  # Marathon
    elif race_duration_hours > 1.5:
        carbs_per_hour = 40  # Half Marathon
    
    total_carbs_needed = carbs_per_hour * race_duration_hours
    total_calories_needed = total_carbs_needed * 4  # Carbs = 4 kcal/g
    
    # Generate fueling strategy (every 20-30 minutes)
    fueling_interval_minutes = 25
    fueling_strategies = []
    
    current_minutes = 0
    carbs_remaining = total_carbs_needed
    
    while current_minutes < race_duration_hours * 60 and carbs_remaining > 0:
        carbs_this_time = min(25, carbs_remaining)  # 25g per fueling
        
        fueling_strategies.append(
            FuelingStrategy(
                time_minutes=current_minutes,
                type="gel" if current_minutes % 50 == 0 else "drink",
                carbs_grams=carbs_this_time,
                calories=carbs_this_time * 4,
                notes=f"{carbs_this_time}g carbs - {fueling_strategies[-1].type if fueling_strategies else 'gel or sports drink'}"
            )
        )
        
        carbs_remaining -= carbs_this_time
        current_minutes += fueling_interval_minutes
    
    # Post-race recovery
    post_race_recovery = {
        "within_30min": {
            "carbs_grams": 60,
            "protein_grams": 20,
            "calories": 360,
            "examples": "Recovery shake, chocolate milk, banana with protein bar"
        },
        "within_2hours": {
            "carbs_grams": 100,
            "protein_grams": 30,
            "calories": 600,
            "examples": "Full meal: pasta with chicken, rice bowl, or similar"
        },
        "notes": "Focus on 3:1 or 4:1 carbs to protein ratio for optimal recovery"
    }
    
    notes = f"""
    Race fueling strategy for {race_type} ({race_duration_hours:.1f}h):
    - Target: {carbs_per_hour}g carbs per hour
    - Total: {total_carbs_needed:.0f}g carbs during race
    - Fuel every {fueling_interval_minutes} minutes
    - Start fueling early (within first hour)
    - Practice this strategy in training!
    """
    
    return RaceFuelingPlan(
        race_type=race_type,
        race_duration_hours=race_duration_hours,
        total_carbs_grams=total_carbs_needed,
        total_calories=total_calories_needed,
        fueling_strategies=fueling_strategies,
        pre_race_meals=pre_race_meals,
        post_race_recovery=post_race_recovery,
        notes=notes.strip()
    )


def calculate_nutrition_targets(
    weight_kg: float,
    height_cm: float,
    age: int,
    gender: str = "male",
    activity_level: str = "active",
    training_hours_per_week: float = 8.0,
    goal_type: str = "performance"
) -> NutritionTargets:
    """
    Complete nutrition calculator - calculates daily calories and macros.
    
    Args:
        weight_kg: Weight in kg
        height_cm: Height in cm
        age: Age in years
        gender: "male" or "female"
        activity_level: Activity level
        training_hours_per_week: Training hours
        goal_type: "maintain", "lose_weight", "gain_muscle", "performance"
    
    Returns:
        NutritionTargets with all daily targets
    """
    calories = calculate_daily_calories(
        weight_kg=weight_kg,
        height_cm=height_cm,
        age=age,
        gender=gender,
        activity_level=activity_level,
        training_hours_per_week=training_hours_per_week,
        goal_type=goal_type
    )
    
    return calculate_daily_macros(
        calories=calories,
        goal_type=goal_type,
        training_hours_per_week=training_hours_per_week
    )

