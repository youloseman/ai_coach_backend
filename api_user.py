from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
import models
from schemas import ProfileUpdate, ProfileResponse, GoalCreate, GoalResponse
from auth import get_current_user
import crud
from cache import (
    get_cached_user_profile,
    cache_user_profile,
    TTL_USER_PROFILE,
)


router = APIRouter()


# ===== PROFILE ENDPOINTS =====


@router.get("/profile", response_model=ProfileResponse)
async def get_profile(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get current user's athlete profile. Supports caching for performance."""
    # Check cache first
    cached_profile = get_cached_user_profile(current_user.id)
    if cached_profile is not None:
        return ProfileResponse(**cached_profile)
    
    # Cache miss - fetch from DB
    profile = crud.get_user_profile(db, current_user.id)

    if not profile:
        # Create default profile if doesn't exist
        profile = models.AthleteProfileDB(user_id=current_user.id)
        db.add(profile)
        db.commit()
        db.refresh(profile)

    profile_response = ProfileResponse.model_validate(profile)
    
    # Cache the result
    cache_user_profile(current_user.id, profile_response.model_dump())
    
    return profile_response


@router.patch("/profile", response_model=ProfileResponse)
async def update_profile(
    profile_update: ProfileUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update current user's athlete profile. Invalidates cache."""
    from cache import cache
    
    profile = crud.update_user_profile(db, current_user.id, profile_update)
    profile_response = ProfileResponse.model_validate(profile)
    
    # Invalidate and update cache
    cache.delete(f"user:profile:{current_user.id}")
    cache_user_profile(current_user.id, profile_response.model_dump())
    
    return profile_response


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


