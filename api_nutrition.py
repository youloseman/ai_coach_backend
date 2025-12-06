"""
Nutrition API endpoints for triathletes.
Provides daily nutrition targets, race day fueling plans, and recovery nutrition.
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from database import get_db
import models
from auth import get_current_user
import crud
from nutrition import (
    calculate_nutrition_targets,
    calculate_race_fueling_plan,
    NutritionTargets,
    RaceFuelingPlan,
)


router = APIRouter()


# ===== REQUEST/RESPONSE MODELS =====

class NutritionTargetsRequest(BaseModel):
    """Request to calculate nutrition targets"""
    weight_kg: float
    height_cm: float
    age: int
    gender: str = "male"  # "male" or "female"
    activity_level: str = "active"  # "sedentary", "light", "moderate", "active", "very_active"
    training_hours_per_week: float = 8.0
    goal_type: str = "performance"  # "maintain", "lose_weight", "gain_muscle", "performance"


class NutritionTargetsResponse(BaseModel):
    """Daily nutrition targets response"""
    calories: float
    carbs_grams: float
    protein_grams: float
    fat_grams: float
    breakdown: dict  # Percentage breakdown


class RaceFuelingRequest(BaseModel):
    """Request for race day fueling plan"""
    race_type: str  # "5K", "10K", "HM", "Marathon", "Ironman", etc.
    race_duration_hours: float
    weight_kg: Optional[float] = 70.0


# ===== NUTRITION TARGETS ENDPOINTS =====

@router.post("/targets/calculate", response_model=NutritionTargetsResponse)
async def calculate_targets(
    request: NutritionTargetsRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Calculate daily nutrition targets based on user profile and goals.
    """
    targets = calculate_nutrition_targets(
        weight_kg=request.weight_kg,
        height_cm=request.height_cm,
        age=request.age,
        gender=request.gender,
        activity_level=request.activity_level,
        training_hours_per_week=request.training_hours_per_week,
        goal_type=request.goal_type
    )
    
    # Calculate percentage breakdown
    total_calories = targets.calories
    breakdown = {
        "carbs_percent": round((targets.carbs_grams * 4 / total_calories) * 100, 1),
        "protein_percent": round((targets.protein_grams * 4 / total_calories) * 100, 1),
        "fat_percent": round((targets.fat_grams * 9 / total_calories) * 100, 1),
    }
    
    # Save to database
    existing = db.query(models.NutritionTargetDB).filter(
        models.NutritionTargetDB.user_id == current_user.id
    ).first()
    
    if existing:
        existing.daily_calories = targets.calories
        existing.daily_carbs_grams = targets.carbs_grams
        existing.daily_protein_grams = targets.protein_grams
        existing.daily_fat_grams = targets.fat_grams
        existing.activity_level = request.activity_level
        existing.training_days_per_week = int(request.training_hours_per_week / 2)  # Rough estimate
        existing.goal_type = request.goal_type
    else:
        existing = models.NutritionTargetDB(
            user_id=current_user.id,
            daily_calories=targets.calories,
            daily_carbs_grams=targets.carbs_grams,
            daily_protein_grams=targets.protein_grams,
            daily_fat_grams=targets.fat_grams,
            activity_level=request.activity_level,
            training_days_per_week=int(request.training_hours_per_week / 2),
            goal_type=request.goal_type,
        )
        db.add(existing)
    
    db.commit()
    
    return NutritionTargetsResponse(
        calories=targets.calories,
        carbs_grams=targets.carbs_grams,
        protein_grams=targets.protein_grams,
        fat_grams=targets.fat_grams,
        breakdown=breakdown,
    )


@router.get("/targets", response_model=NutritionTargetsResponse)
async def get_targets(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get saved nutrition targets for current user.
    """
    targets = db.query(models.NutritionTargetDB).filter(
        models.NutritionTargetDB.user_id == current_user.id
    ).first()
    
    if not targets:
        raise HTTPException(
            status_code=404,
            detail="No nutrition targets found. Calculate targets first."
        )
    
    total_calories = targets.daily_calories or 0
    if total_calories == 0:
        raise HTTPException(
            status_code=404,
            detail="Nutrition targets not calculated yet."
        )
    
    breakdown = {
        "carbs_percent": round((targets.daily_carbs_grams * 4 / total_calories) * 100, 1) if total_calories > 0 else 0,
        "protein_percent": round((targets.daily_protein_grams * 4 / total_calories) * 100, 1) if total_calories > 0 else 0,
        "fat_percent": round((targets.daily_fat_grams * 9 / total_calories) * 100, 1) if total_calories > 0 else 0,
    }
    
    return NutritionTargetsResponse(
        calories=targets.daily_calories,
        carbs_grams=targets.daily_carbs_grams,
        protein_grams=targets.daily_protein_grams,
        fat_grams=targets.daily_fat_grams,
        breakdown=breakdown,
    )


# ===== RACE FUELING ENDPOINTS =====

@router.post("/race-fueling", response_model=dict)
async def calculate_race_fueling(
    request: RaceFuelingRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Generate race day fueling plan.
    """
    plan = calculate_race_fueling_plan(
        race_type=request.race_type,
        race_duration_hours=request.race_duration_hours,
        weight_kg=request.weight_kg or 70.0
    )
    
    # Save to database
    nutrition_plan = models.NutritionPlanDB(
        user_id=current_user.id,
        plan_type="race_day",
        race_type=request.race_type,
        race_duration_hours=request.race_duration_hours,
        pre_race_meals=plan.pre_race_meals,
        during_race_fueling=[s.to_dict() for s in plan.fueling_strategies],
        recovery_nutrition=plan.post_race_recovery,
        notes=plan.notes,
    )
    db.add(nutrition_plan)
    db.commit()
    
    return plan.to_dict()


@router.get("/race-fueling/{race_type}", response_model=dict)
async def get_race_fueling_plan(
    race_type: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get saved race fueling plan for specific race type.
    """
    plan = db.query(models.NutritionPlanDB).filter(
        models.NutritionPlanDB.user_id == current_user.id,
        models.NutritionPlanDB.plan_type == "race_day",
        models.NutritionPlanDB.race_type == race_type
    ).order_by(models.NutritionPlanDB.created_at.desc()).first()
    
    if not plan:
        raise HTTPException(
            status_code=404,
            detail=f"No race fueling plan found for {race_type}. Calculate one first."
        )
    
    return {
        "race_type": plan.race_type,
        "race_duration_hours": plan.race_duration_hours,
        "pre_race_meals": plan.pre_race_meals or [],
        "during_race_fueling": plan.during_race_fueling or [],
        "recovery_nutrition": plan.recovery_nutrition or {},
        "notes": plan.notes,
        "created_at": plan.created_at.isoformat() if plan.created_at else None,
    }


@router.get("/race-fueling", response_model=list)
async def list_race_fueling_plans(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List all saved race fueling plans for current user.
    """
    plans = db.query(models.NutritionPlanDB).filter(
        models.NutritionPlanDB.user_id == current_user.id,
        models.NutritionPlanDB.plan_type == "race_day"
    ).order_by(models.NutritionPlanDB.created_at.desc()).all()
    
    return [
        {
            "id": p.id,
            "race_type": p.race_type,
            "race_duration_hours": p.race_duration_hours,
            "created_at": p.created_at.isoformat() if p.created_at else None,
        }
        for p in plans
    ]

