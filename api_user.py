from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
import models
from schemas import ProfileUpdate, ProfileResponse, GoalCreate, GoalResponse
from auth import get_current_user
import crud


router = APIRouter()


# ===== PROFILE ENDPOINTS =====


@router.get("/profile", response_model=ProfileResponse)
async def get_profile(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get current user's athlete profile."""
    profile = crud.get_user_profile(db, current_user.id)

    if not profile:
        # Create default profile if doesn't exist
        profile = models.AthleteProfileDB(user_id=current_user.id)
        db.add(profile)
        db.commit()
        db.refresh(profile)

    return ProfileResponse.model_validate(profile)


@router.patch("/profile", response_model=ProfileResponse)
async def update_profile(
    profile_update: ProfileUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update current user's athlete profile."""
    profile = crud.update_user_profile(db, current_user.id, profile_update)
    return ProfileResponse.model_validate(profile)


# ===== GOALS ENDPOINTS =====


@router.post("/goals", response_model=GoalResponse)
async def create_goal(
    goal: GoalCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create new training goal."""
    db_goal = crud.create_goal(db, current_user.id, goal)
    return GoalResponse.model_validate(db_goal)


@router.get("/goals", response_model=List[GoalResponse])
async def get_goals(
    include_completed: bool = False,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get all user's goals."""
    goals = crud.get_user_goals(db, current_user.id, include_completed)
    return [GoalResponse.model_validate(g) for g in goals]


@router.get("/goals/primary", response_model=GoalResponse)
async def get_primary_goal(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get user's primary goal."""
    goal = crud.get_primary_goal(db, current_user.id)

    if not goal:
        raise HTTPException(status_code=404, detail="No primary goal set")

    return GoalResponse.model_validate(goal)


