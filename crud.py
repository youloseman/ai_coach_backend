from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import datetime, date
from typing import Optional, List

from models import User, AthleteProfileDB, GoalDB, WeeklyPlanDB, ActivityDB
from schemas import UserCreate, ProfileUpdate, GoalCreate
from auth import get_password_hash


# ===== USER CRUD =====

def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """Get user by email"""
    return db.query(User).filter(User.email == email).first()


def get_user_by_username(db: Session, username: str) -> Optional[User]:
    """Get user by username"""
    return db.query(User).filter(User.username == username).first()


def create_user(db: Session, user: UserCreate) -> User:
    """Create new user with hashed password"""
    hashed_password = get_password_hash(user.password)
    
    db_user = User(
        email=user.email,
        username=user.username,
        hashed_password=hashed_password,
        full_name=user.full_name
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    # Create default profile
    profile = AthleteProfileDB(user_id=db_user.id)
    db.add(profile)
    db.commit()
    
    return db_user


def update_user_last_login(db: Session, user_id: int):
    """Update last login timestamp"""
    db.query(User).filter(User.id == user_id).update({"last_login_at": datetime.utcnow()})
    db.commit()


# ===== PROFILE CRUD =====

def get_user_profile(db: Session, user_id: int) -> Optional[AthleteProfileDB]:
    """Get athlete profile for user"""
    return db.query(AthleteProfileDB).filter(AthleteProfileDB.user_id == user_id).first()


def update_user_profile(db: Session, user_id: int, profile_update: ProfileUpdate) -> AthleteProfileDB:
    """Update athlete profile"""
    profile = get_user_profile(db, user_id)
    
    if not profile:
        # Create if doesn't exist
        profile = AthleteProfileDB(user_id=user_id)
        db.add(profile)
    
    # Update fields
    update_data = profile_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(profile, field, value)
    
    db.commit()
    db.refresh(profile)
    
    return profile


# ===== GOAL CRUD =====

def create_goal(db: Session, user_id: int, goal: GoalCreate) -> GoalDB:
    """Create new training goal"""
    # If this is primary goal, unset other primary goals
    if goal.is_primary:
        db.query(GoalDB).filter(
            and_(GoalDB.user_id == user_id, GoalDB.is_primary == True)
        ).update({"is_primary": False})
    
    db_goal = GoalDB(
        user_id=user_id,
        **goal.model_dump()
    )
    
    db.add(db_goal)
    db.commit()
    db.refresh(db_goal)
    
    return db_goal


def get_user_goals(db: Session, user_id: int, include_completed: bool = False) -> List[GoalDB]:
    """Get all goals for user"""
    query = db.query(GoalDB).filter(GoalDB.user_id == user_id)
    
    if not include_completed:
        query = query.filter(GoalDB.is_completed == False)
    
    return query.order_by(GoalDB.race_date).all()


def get_primary_goal(db: Session, user_id: int) -> Optional[GoalDB]:
    """Get user's primary goal"""
    return db.query(GoalDB).filter(
        and_(GoalDB.user_id == user_id, GoalDB.is_primary == True)
    ).first()


# ===== WEEKLY PLAN CRUD =====

def save_weekly_plan_db(
    db: Session, 
    user_id: int, 
    week_start_date: date, 
    plan_json: dict,
    goal_id: Optional[int] = None,
    available_hours: Optional[float] = None
) -> WeeklyPlanDB:
    """Save or update weekly plan"""
    # Check if plan exists
    existing = db.query(WeeklyPlanDB).filter(
        and_(
            WeeklyPlanDB.user_id == user_id,
            WeeklyPlanDB.week_start_date == week_start_date
        )
    ).first()
    
    if existing:
        # Update existing
        existing.plan_json = plan_json
        existing.goal_id = goal_id
        existing.available_hours = available_hours
        db.commit()
        db.refresh(existing)
        return existing
    else:
        # Create new
        plan = WeeklyPlanDB(
            user_id=user_id,
            week_start_date=week_start_date,
            plan_json=plan_json,
            goal_id=goal_id,
            available_hours=available_hours
        )
        db.add(plan)
        db.commit()
        db.refresh(plan)
        return plan


def get_weekly_plan_db(db: Session, user_id: int, week_start_date: date) -> Optional[WeeklyPlanDB]:
    """Get weekly plan for specific week"""
    return db.query(WeeklyPlanDB).filter(
        and_(
            WeeklyPlanDB.user_id == user_id,
            WeeklyPlanDB.week_start_date == week_start_date
        )
    ).first()


# ===== ACTIVITY CACHE =====

def cache_activity(db: Session, user_id: int, strava_activity: dict):
    """Cache Strava activity in database"""
    existing = db.query(ActivityDB).filter(
        ActivityDB.strava_id == str(strava_activity["id"])
    ).first()
    
    if existing:
        return existing
    
    activity = ActivityDB(
        user_id=user_id,
        strava_id=str(strava_activity["id"]),
        name=strava_activity.get("name", ""),
        sport_type=strava_activity.get("sport_type", strava_activity.get("type", "")),
        start_date=datetime.fromisoformat(strava_activity["start_date"].replace("Z", "+00:00")),
        distance_meters=strava_activity.get("distance"),
        moving_time_seconds=strava_activity.get("moving_time"),
        elapsed_time_seconds=strava_activity.get("elapsed_time"),
        total_elevation_gain=strava_activity.get("total_elevation_gain"),
        average_heartrate=strava_activity.get("average_heartrate"),
        max_heartrate=strava_activity.get("max_heartrate"),
        average_watts=strava_activity.get("average_watts"),
        weighted_average_watts=strava_activity.get("weighted_average_watts"),
        raw_data=strava_activity
    )
    
    db.add(activity)
    db.commit()
    db.refresh(activity)
    
    return activity