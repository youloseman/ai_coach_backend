# services/activity_service.py

from sqlalchemy.orm import Session
from models import ActivityDB, User, AthleteProfileDB
from analytics.tss import auto_calculate_tss
from config import logger


def get_user_training_zones(user: User, db: Session) -> dict:
    """
    Extract training zones from user's profile
    
    Returns:
        {
            "ftp": float or 0,
            "threshold_pace": float or 0,  # min/km
            "css_pace_100m": float or 0    # seconds per 100m
        }
    """
    profile = db.query(AthleteProfileDB).filter(
        AthleteProfileDB.user_id == user.id
    ).first()
    
    if not profile:
        return {
            "ftp": 0,
            "threshold_pace": 0,
            "css_pace_100m": 0
        }
    
    # Extract FTP from bike zones
    ftp = 0
    if profile.training_zones_bike:
        ftp = profile.training_zones_bike.get("ftp", 0) or \
              profile.training_zones_bike.get("FTP", 0) or 0
    
    # Extract threshold pace from run zones
    threshold_pace = 0
    if profile.training_zones_run:
        threshold_pace = profile.training_zones_run.get("threshold_pace", 0) or \
                        profile.training_zones_run.get("threshold_pace_min_per_km", 0) or 0
    
    # Extract CSS from swim zones
    css_pace_100m = 0
    if profile.training_zones_swim:
        css_pace_100m = profile.training_zones_swim.get("css_pace_100m", 0) or \
                       profile.training_zones_swim.get("css_pace_100m_seconds", 0) or \
                       profile.training_zones_swim.get("css", 0) or 0
    
    return {
        "ftp": float(ftp) if ftp else 0,
        "threshold_pace": float(threshold_pace) if threshold_pace else 0,
        "css_pace_100m": float(css_pace_100m) if css_pace_100m else 0
    }


def calculate_and_save_tss(
    activity: ActivityDB,
    user: User,
    db: Session
) -> ActivityDB:
    """
    Calculate TSS for activity and save to database
    
    Args:
        activity: ActivityDB object
        user: User with training zones (ftp, threshold_pace, etc)
        db: Database session
    
    Returns:
        Updated activity with TSS
    """
    # Get user training zones
    user_profile = get_user_training_zones(user, db)
    
    # Prepare activity data for TSS calculation
    activity_data = {
        "sport_type": activity.sport_type.lower(),
        "duration_s": activity.moving_time_seconds or activity.elapsed_time_seconds or 0,
        "distance_m": activity.distance_meters or 0,
    }
    
    # Add optional fields if available
    if activity.average_watts:
        activity_data["avg_power"] = activity.average_watts
    elif activity.weighted_average_watts:
        activity_data["avg_power"] = activity.weighted_average_watts
        activity_data["normalized_power"] = activity.weighted_average_watts
    
    # Calculate pace from distance and time (if not available)
    if not activity_data.get("avg_pace_min_per_km") and activity_data["distance_m"] > 0 and activity_data["duration_s"] > 0:
        # Calculate pace: min/km
        distance_km = activity_data["distance_m"] / 1000.0
        duration_min = activity_data["duration_s"] / 60.0
        if distance_km > 0:
            activity_data["avg_pace_min_per_km"] = duration_min / distance_km
    
    # Calculate TSS
    try:
        tss = auto_calculate_tss(activity_data, user_profile)
        
        if tss > 0:
            activity.tss = tss
            logger.info(
                "tss_calculated",
                activity_id=activity.id,
                sport_type=activity.sport_type,
                tss=tss,
                duration_s=activity_data["duration_s"]
            )
        else:
            logger.warning(
                "tss_calculation_failed",
                activity_id=activity.id,
                sport_type=activity.sport_type,
                reason="TSS calculation returned 0"
            )
    except Exception as e:
        logger.error(
            "tss_calculation_error",
            activity_id=activity.id,
            error=str(e)
        )
        # Don't fail the whole operation if TSS calculation fails
        activity.tss = None
    
    # Save to database
    db.add(activity)
    db.commit()
    db.refresh(activity)
    
    return activity

