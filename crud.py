from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import datetime, date, timezone
from typing import Optional, List

from models import (
    User, AthleteProfileDB, GoalDB, WeeklyPlanDB, ActivityDB,
    SegmentDB, SegmentEffortDB, PersonalRecordDB, InjuryRiskDB
)
from schemas import UserCreate, ProfileUpdate, GoalCreate
from auth import get_password_hash
from exceptions import ValidationError, NotFoundError, DatabaseError


# ===== USER CRUD =====

def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """Get user by email"""
    return db.query(User).filter(User.email == email).first()


def get_user_by_username(db: Session, username: str) -> Optional[User]:
    """Get user by username"""
    return db.query(User).filter(User.username == username).first()


def get_user_by_strava_athlete_id(db: Session, athlete_id: str) -> Optional[User]:
    """Get user by linked Strava athlete id"""
    return db.query(User).filter(User.strava_athlete_id == str(athlete_id)).first()


def create_user(db: Session, user: UserCreate) -> User:
    """Create new user with profile"""
    try:
        # Check if email exists
        existing = db.query(User).filter(User.email == user.email).first()
        if existing:
            raise ValidationError(f"User with email {user.email} already exists")
        
        # Check if username exists
        existing_username = db.query(User).filter(User.username == user.username).first()
        if existing_username:
            raise ValidationError(f"User with username {user.username} already exists")
        
        # Create user
        hashed_password = get_password_hash(user.password)
        db_user = User(
            email=user.email,
            username=user.username,
            hashed_password=hashed_password,
            full_name=user.full_name
        )
        db.add(db_user)
        db.flush()  # Get ID
        
        # Create profile
        profile = AthleteProfileDB(user_id=db_user.id)
        db.add(profile)
        
        # Single commit
        db.commit()
        db.refresh(db_user)
        
        from config import logger
        logger.info("user_created", user_id=db_user.id, email=user.email)
        return db_user
        
    except ValidationError:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        from config import logger
        logger.error("user_creation_failed", error=str(e))
        raise DatabaseError("Failed to create user")


def update_user_last_login(db: Session, user_id: int):
    """Update last login timestamp"""
    db.query(User).filter(User.id == user_id).update({"last_login_at": datetime.now(timezone.utc)})
    db.commit()


def verify_user_email(db: Session, user_id: int) -> User:
    """Mark user email as verified"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise ValueError("User not found")
    
    user.is_verified = True
    user.email_verified_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(user)
    return user


# ===== PROFILE CRUD =====

def get_user_profile(db: Session, user_id: int) -> Optional[AthleteProfileDB]:
    """Get athlete profile for user"""
    return db.query(AthleteProfileDB).filter(AthleteProfileDB.user_id == user_id).first()


def update_user_profile(db: Session, user_id: int, profile_update: ProfileUpdate) -> AthleteProfileDB:
    """Update athlete profile"""
    try:
        profile = get_user_profile(db, user_id)
        
        if not profile:
            raise NotFoundError(f"Profile not found for user {user_id}")
        
        # Update fields
        update_data = profile_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if hasattr(profile, field):
                setattr(profile, field, value)
        
        db.commit()
        db.refresh(profile)
        
        # Invalidate cache
        from cache import invalidate_training_zones
        invalidate_training_zones(user_id)
        
        from config import logger
        logger.info("profile_updated", user_id=user_id)
        return profile
        
    except NotFoundError:
        raise
    except Exception as e:
        db.rollback()
        from config import logger
        logger.error("profile_update_failed", user_id=user_id, error=str(e))
        raise DatabaseError("Failed to update profile")


# ===== GOAL CRUD =====

def create_goal(db: Session, user_id: int, goal: GoalCreate) -> GoalDB:
    """Create new training goal"""
    try:
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
        
        from config import logger
        logger.info("goal_created", goal_id=db_goal.id, user_id=user_id)
        return db_goal
        
    except Exception as e:
        db.rollback()
        from config import logger
        logger.error("goal_creation_failed", user_id=user_id, error=str(e))
        raise DatabaseError("Failed to create goal")


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
    try:
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
            
    except Exception as e:
        db.rollback()
        from config import logger
        logger.error("weekly_plan_save_failed", user_id=user_id, week_start_date=str(week_start_date), error=str(e))
        raise DatabaseError("Failed to save weekly plan")


def get_weekly_plan_db(db: Session, user_id: int, week_start_date: date) -> Optional[WeeklyPlanDB]:
    """Get weekly plan for specific week"""
    return db.query(WeeklyPlanDB).filter(
        and_(
            WeeklyPlanDB.user_id == user_id,
            WeeklyPlanDB.week_start_date == week_start_date
        )
    ).first()


# ===== ACTIVITY CACHE =====

def _apply_activity_fields(activity: ActivityDB, user_id: int, strava_activity: dict):
    activity.user_id = user_id
    activity.strava_id = str(strava_activity["id"])
    activity.name = strava_activity.get("name", "")
    activity.sport_type = strava_activity.get("sport_type", strava_activity.get("type", ""))
    start_date = strava_activity.get("start_date")
    if start_date:
        activity.start_date = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
    activity.distance_meters = strava_activity.get("distance")
    activity.moving_time_seconds = strava_activity.get("moving_time")
    activity.elapsed_time_seconds = strava_activity.get("elapsed_time")
    activity.total_elevation_gain = strava_activity.get("total_elevation_gain")
    activity.average_heartrate = strava_activity.get("average_heartrate")
    activity.max_heartrate = strava_activity.get("max_heartrate")
    activity.average_watts = strava_activity.get("average_watts")
    activity.weighted_average_watts = strava_activity.get("weighted_average_watts")
    activity.raw_data = strava_activity


def upsert_activity(db: Session, user_id: int, strava_activity: dict, compute_tss: bool = True) -> ActivityDB:
    """Insert or update cached Strava activity for specific user."""
    try:
        existing = db.query(ActivityDB).filter(
            and_(
                ActivityDB.user_id == user_id,
                ActivityDB.strava_id == str(strava_activity["id"])
            )
        ).first()

        if existing:
            _apply_activity_fields(existing, user_id, strava_activity)
            db.commit()
            db.refresh(existing)
            # Calculate TSS if not already set
            if compute_tss and existing.tss is None:
                try:
                    from services.activity_service import calculate_and_save_tss
                    user = db.query(User).filter(User.id == user_id).first()
                    if user:
                        calculate_and_save_tss(existing, user, db)
                        # Note: For batch processing multiple activities, use calculate_tss_batch instead
                except Exception as e:
                    # Don't fail if TSS calculation fails
                    from config import logger
                    logger.warning("tss_calculation_failed_on_import", activity_id=existing.id, error=str(e))
            return existing

        activity = ActivityDB()
        _apply_activity_fields(activity, user_id, strava_activity)
        db.add(activity)
        db.commit()
        db.refresh(activity)

        # Calculate TSS automatically
        if compute_tss:
            try:
                from services.activity_service import calculate_and_save_tss
                user = db.query(User).filter(User.id == user_id).first()
                if user:
                    calculate_and_save_tss(activity, user, db)
                    # Note: For batch processing multiple activities, use calculate_tss_batch instead
            except Exception as e:
                # Don't fail if TSS calculation fails
                from config import logger
                logger.warning("tss_calculation_failed_on_import", activity_id=activity.id, error=str(e))

        return activity
        
    except Exception as e:
        db.rollback()
        from config import logger
        logger.error("activity_upsert_failed", user_id=user_id, activity_id=strava_activity.get("id"), error=str(e))
        raise DatabaseError("Failed to upsert activity")


def cache_activity(db: Session, user_id: int, strava_activity: dict):
    """Backwards-compatible helper to upsert activity."""
    return upsert_activity(db, user_id, strava_activity)


def delete_activity_by_strava_id(db: Session, user_id: int, strava_activity_id: str) -> None:
    """Delete cached activity by Strava activity id for specific user."""
    db.query(ActivityDB).filter(
        and_(
            ActivityDB.user_id == user_id,
            ActivityDB.strava_id == str(strava_activity_id)
        )
    ).delete()
    db.commit()


# ===== SEGMENT CRUD =====

def upsert_segment(db: Session, strava_segment: dict) -> SegmentDB:
    """Insert or update Strava segment."""
    segment_id = str(strava_segment["id"])
    existing = db.query(SegmentDB).filter(SegmentDB.strava_segment_id == segment_id).first()
    
    segment_data = {
        "strava_segment_id": segment_id,
        "name": strava_segment.get("name", ""),
        "activity_type": strava_segment.get("activity_type", ""),
        "distance_meters": strava_segment.get("distance", 0),
        "city": strava_segment.get("city"),
        "state": strava_segment.get("state"),
        "country": strava_segment.get("country"),
        "average_grade": strava_segment.get("average_grade"),
        "maximum_grade": strava_segment.get("maximum_grade"),
        "elevation_high": strava_segment.get("elevation_high"),
        "elevation_low": strava_segment.get("elevation_low"),
        "total_elevation_gain": strava_segment.get("total_elevation_gain"),
        "athlete_count": strava_segment.get("athlete_count", 0),
        "effort_count": strava_segment.get("effort_count", 0),
        "star_count": strava_segment.get("star_count", 0),
        "raw_data": strava_segment,
    }
    
    if existing:
        for key, value in segment_data.items():
            if key != "strava_segment_id":  # Don't update ID
                setattr(existing, key, value)
        db.commit()
        db.refresh(existing)
        return existing
    
    segment = SegmentDB(**segment_data)
    db.add(segment)
    db.commit()
    db.refresh(segment)
    return segment


def get_segment_by_strava_id(db: Session, strava_segment_id: str) -> Optional[SegmentDB]:
    """Get segment by Strava segment ID."""
    return db.query(SegmentDB).filter(SegmentDB.strava_segment_id == str(strava_segment_id)).first()


def get_user_segments(db: Session, user_id: int, limit: int = 50) -> List[SegmentDB]:
    """Get segments that user has efforts on."""
    segments = db.query(SegmentDB).join(SegmentEffortDB).filter(
        SegmentEffortDB.user_id == user_id
    ).distinct().limit(limit).all()
    return segments


# ===== SEGMENT EFFORT CRUD =====

def upsert_segment_effort(
    db: Session,
    user_id: int,
    activity_db_id: Optional[int],
    strava_effort: dict,
    segment_db_id: int
) -> SegmentEffortDB:
    """Insert or update segment effort."""
    effort_id = str(strava_effort["id"])
    existing = db.query(SegmentEffortDB).filter(
        and_(
            SegmentEffortDB.user_id == user_id,
            SegmentEffortDB.strava_effort_id == effort_id
        )
    ).first()
    
    # Parse start date
    start_date_str = strava_effort.get("start_date") or strava_effort.get("start_date_local")
    if start_date_str:
        start_date = datetime.fromisoformat(start_date_str.replace("Z", "+00:00"))
    else:
        start_date = datetime.now(timezone.utc)
    
    effort_data = {
        "user_id": user_id,
        "activity_id": activity_db_id,
        "segment_id": segment_db_id,
        "strava_effort_id": effort_id,
        "start_date": start_date,
        "elapsed_time_seconds": strava_effort.get("elapsed_time", 0),
        "moving_time_seconds": strava_effort.get("moving_time"),
        "average_heartrate": strava_effort.get("average_heartrate"),
        "max_heartrate": strava_effort.get("max_heartrate"),
        "average_watts": strava_effort.get("average_watts"),
        "average_cadence": strava_effort.get("average_cadence"),
        "pr_rank": strava_effort.get("pr_rank"),
        "kom_rank": strava_effort.get("kom_rank"),
        "is_pr": strava_effort.get("pr_rank") == 1,
        "device_watts": strava_effort.get("device_watts", False),
        "raw_data": strava_effort,
    }
    
    if existing:
        for key, value in effort_data.items():
            if key != "strava_effort_id":
                setattr(existing, key, value)
        db.commit()
        db.refresh(existing)
        return existing
    
    effort = SegmentEffortDB(**effort_data)
    db.add(effort)
    db.commit()
    db.refresh(effort)
    return effort


def get_user_segment_efforts(
    db: Session,
    user_id: int,
    segment_id: Optional[int] = None,
    limit: int = 100
) -> List[SegmentEffortDB]:
    """Get user's segment efforts, optionally filtered by segment."""
    query = db.query(SegmentEffortDB).filter(SegmentEffortDB.user_id == user_id)
    
    if segment_id:
        query = query.filter(SegmentEffortDB.segment_id == segment_id)
    
    return query.order_by(SegmentEffortDB.start_date.desc()).limit(limit).all()


def get_user_prs_on_segments(db: Session, user_id: int, limit: int = 50) -> List[SegmentEffortDB]:
    """Get user's personal records on segments."""
    return db.query(SegmentEffortDB).filter(
        and_(
            SegmentEffortDB.user_id == user_id,
            SegmentEffortDB.is_pr == True
        )
    ).order_by(SegmentEffortDB.start_date.desc()).limit(limit).all()


# ===== PERSONAL RECORD CRUD =====

def create_personal_record(
    db: Session,
    user_id: int,
    activity_db_id: Optional[int],
    sport_type: str,
    distance_category: str,
    distance_meters: float,
    time_seconds: int,
    achieved_date: datetime,
    **kwargs
) -> PersonalRecordDB:
    """Create a new personal record."""
    # Mark previous records as superseded
    db.query(PersonalRecordDB).filter(
        and_(
            PersonalRecordDB.user_id == user_id,
            PersonalRecordDB.sport_type == sport_type,
            PersonalRecordDB.distance_category == distance_category,
            PersonalRecordDB.is_current_pr == True
        )
    ).update({
        "is_current_pr": False,
        "superseded_at": datetime.now(timezone.utc)
    })
    
    # Calculate pace/speed
    pace_per_km = None
    speed_kmh = None
    if distance_meters > 0 and time_seconds > 0:
        pace_per_km = time_seconds / (distance_meters / 1000)  # seconds per km
        speed_kmh = (distance_meters / 1000) / (time_seconds / 3600)  # km/h
    
    pr = PersonalRecordDB(
        user_id=user_id,
        activity_id=activity_db_id,
        sport_type=sport_type,
        distance_category=distance_category,
        distance_meters=distance_meters,
        time_seconds=time_seconds,
        pace_per_km=pace_per_km,
        speed_kmh=speed_kmh,
        achieved_date=achieved_date,
        is_current_pr=True,
        **kwargs
    )
    
    db.add(pr)
    db.commit()
    db.refresh(pr)
    return pr


def get_current_personal_records(db: Session, user_id: int, sport_type: Optional[str] = None) -> List[PersonalRecordDB]:
    """Get user's current personal records."""
    query = db.query(PersonalRecordDB).filter(
        and_(
            PersonalRecordDB.user_id == user_id,
            PersonalRecordDB.is_current_pr == True
        )
    )
    
    if sport_type:
        query = query.filter(PersonalRecordDB.sport_type == sport_type)
    
    return query.order_by(PersonalRecordDB.achieved_date.desc()).all()


def get_pr_history(
    db: Session,
    user_id: int,
    sport_type: str,
    distance_category: str
) -> List[PersonalRecordDB]:
    """Get history of personal records for a specific distance."""
    return db.query(PersonalRecordDB).filter(
        and_(
            PersonalRecordDB.user_id == user_id,
            PersonalRecordDB.sport_type == sport_type,
            PersonalRecordDB.distance_category == distance_category
        )
    ).order_by(PersonalRecordDB.achieved_date.desc()).all()


# ===== INJURY RISK CRUD =====

def create_injury_risk(
    db: Session,
    user_id: int,
    risk_level: str,
    risk_type: str,
    title: str,
    description: str,
    recommendation: str,
    trigger_metrics: dict,
    detected_date: date
) -> InjuryRiskDB:
    """Create injury risk warning."""
    risk = InjuryRiskDB(
        user_id=user_id,
        risk_level=risk_level,
        risk_type=risk_type,
        title=title,
        description=description,
        recommendation=recommendation,
        trigger_metrics=trigger_metrics,
        detected_date=detected_date
    )
    
    db.add(risk)
    db.commit()
    db.refresh(risk)
    return risk


def get_active_injury_risks(db: Session, user_id: int) -> List[InjuryRiskDB]:
    """Get unresolved injury risk warnings."""
    return db.query(InjuryRiskDB).filter(
        and_(
            InjuryRiskDB.user_id == user_id,
            InjuryRiskDB.resolved == False
        )
    ).order_by(InjuryRiskDB.detected_date.desc()).all()


def acknowledge_injury_risk(db: Session, user_id: int, risk_id: int) -> Optional[InjuryRiskDB]:
    """Mark injury risk as acknowledged for specific user."""
    risk = db.query(InjuryRiskDB).filter(
        and_(
            InjuryRiskDB.id == risk_id,
            InjuryRiskDB.user_id == user_id
        )
    ).first()
    if risk:
        risk.acknowledged = True
        risk.acknowledged_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(risk)
    return risk


def resolve_injury_risk(db: Session, user_id: int, risk_id: int) -> Optional[InjuryRiskDB]:
    """Mark injury risk as resolved for specific user."""
    risk = db.query(InjuryRiskDB).filter(
        and_(
            InjuryRiskDB.id == risk_id,
            InjuryRiskDB.user_id == user_id
        )
    ).first()
    if risk:
        risk.resolved = True
        risk.resolved_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(risk)
    return risk