# services/activity_service.py

from typing import Optional, Dict, List
from sqlalchemy.orm import Session
from models import ActivityDB, User, AthleteProfileDB
from analytics.tss import auto_calculate_tss
from config import logger


def get_user_training_zones(user: User, db: Session, use_cache: bool = True) -> dict:
    """
    Extract training zones from user's profile with caching
    
    Args:
        user: User object
        db: Database session
        use_cache: Whether to use Redis cache (default: True)
    
    Returns:
        Training zones dict
    """
    # Try cache first
    if use_cache:
        from cache import get_cached_training_zones
        cached_zones = get_cached_training_zones(user.id)
        if cached_zones:
            return cached_zones
    
    # Load from database
    profile = db.query(AthleteProfileDB).filter(
        AthleteProfileDB.user_id == user.id
    ).first()
    
    if not profile:
        default_zones = {
            "ftp": 0,
            "threshold_pace": 0,
            "css_pace_100m": 0,
            "threshold_hr": 0,
            "max_hr": 0,
            "rest_hr": 0,
        }
        # Cache default zones too
        if use_cache:
            from cache import cache_training_zones
            cache_training_zones(user.id, default_zones, ttl=3600)
        return default_zones
    
    # Extract zones
    zones = {
        "ftp": _extract_ftp(profile),
        "threshold_pace": _extract_threshold_pace(profile),
        "css_pace_100m": _extract_css(profile),
        "threshold_hr": 0,  # TODO: extract if available
        "max_hr": 0,
        "rest_hr": 0,
    }
    
    # Cache for 1 hour
    if use_cache:
        from cache import cache_training_zones
        cache_training_zones(user.id, zones, ttl=3600)
    
    return zones


def _extract_ftp(profile: AthleteProfileDB) -> float:
    """Extract FTP from bike zones"""
    if not profile.training_zones_bike:
        return 0.0
    
    ftp = profile.training_zones_bike.get("ftp", 0) or \
          profile.training_zones_bike.get("FTP", 0) or 0
    
    try:
        return float(ftp) if ftp else 0.0
    except (TypeError, ValueError):
        return 0.0


def _extract_threshold_pace(profile: AthleteProfileDB) -> float:
    """Extract threshold pace from run zones"""
    if not profile.training_zones_run:
        return 0.0
    
    pace = profile.training_zones_run.get("threshold_pace", 0) or \
           profile.training_zones_run.get("threshold_pace_min_per_km", 0) or 0
    
    try:
        return float(pace) if pace else 0.0
    except (TypeError, ValueError):
        return 0.0


def _extract_css(profile: AthleteProfileDB) -> float:
    """Extract CSS from swim zones"""
    if not profile.training_zones_swim:
        return 0.0
    
    css = profile.training_zones_swim.get("css_pace_100m", 0) or \
          profile.training_zones_swim.get("css_pace_100m_seconds", 0) or \
          profile.training_zones_swim.get("css", 0) or 0
    
    try:
        return float(css) if css else 0.0
    except (TypeError, ValueError):
        return 0.0


def calculate_and_save_tss(
    activity: ActivityDB,
    user: User,
    db: Session,
    user_profile: Optional[Dict] = None,
    force: bool = False
) -> ActivityDB:
    """
    Calculate TSS for activity and save to database
    
    Args:
        activity: ActivityDB object
        user: User object
        db: Database session
        user_profile: Pre-loaded training zones (for performance)
        force: Force recalculation even if TSS exists
    
    Returns:
        Updated activity with TSS
    """
    # Skip if TSS already calculated (unless force=True)
    if not force and activity.tss is not None:
        logger.debug("tss_already_calculated", activity_id=activity.id)
        return activity
    
    # Get user training zones (use provided or fetch)
    if user_profile is None:
        user_profile = get_user_training_zones(user, db)
    
    # Guard: sport_type is required
    if not activity.sport_type:
        activity.tss = None
        db.add(activity)
        db.commit()
        db.refresh(activity)
        return activity
    
    # Prepare activity data for TSS calculation
    activity_data = {
        "sport_type": activity.sport_type.lower().strip(),
        "duration_s": activity.moving_time_seconds or activity.elapsed_time_seconds or 0,
        "distance_m": activity.distance_meters or 0,
    }
    
    # Add power data (prefer NP proxy if available)
    if activity.weighted_average_watts:
        activity_data["normalized_power"] = activity.weighted_average_watts
    elif activity.average_watts:
        activity_data["avg_power"] = activity.average_watts
    
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
            activity.tss = None
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
    db.flush()
    db.refresh(activity)
    
    return activity


def calculate_tss_batch(
    activities: List[ActivityDB],
    user: User,
    db: Session,
    force: bool = False
) -> List[ActivityDB]:
    """
    Calculate TSS for multiple activities efficiently
    
    Performance: Single DB query for zones, single commit for all
    
    Args:
        activities: List of ActivityDB objects
        user: User object
        db: Database session
        force: Force recalculation
    
    Returns:
        List of updated activities
    """
    if not activities:
        return []
    
    # Get zones ONCE for all activities
    user_profile = get_user_training_zones(user, db)
    
    successful = 0
    failed = 0
    
    # Process each activity
    for activity in activities:
        try:
            # Skip if already calculated
            if not force and activity.tss is not None:
                continue
            
            # Prepare activity data
            activity_data = prepare_activity_data(activity)
            if not activity_data:
                activity.tss = None
                failed += 1
                continue
            
            # Calculate TSS
            tss = auto_calculate_tss(activity_data, user_profile)
            activity.tss = tss
            
            if tss <= 0:
                failed += 1
            else:
                successful += 1
            
        except Exception as e:
            logger.error(
                "batch_tss_error",
                activity_id=activity.id,
                error=str(e)
            )
            activity.tss = None
            failed += 1
    
    # Single commit for ALL activities
    db.add_all(activities)
    db.commit()
    
    logger.info(
        "batch_tss_complete",
        total=len(activities),
        successful=successful,
        failed=failed,
        user_id=user.id
    )
    
    return activities


def prepare_activity_data(activity: ActivityDB) -> Optional[Dict]:
    """
    Prepare activity data for TSS calculation
    
    Returns:
        Dict with activity data or None if invalid
    """
    # Validate sport type
    if not activity.sport_type:
        logger.warning("missing_sport_type", activity_id=activity.id)
        return None
    
    # Use moving_time for calculations
    duration_s = activity.moving_time_seconds
    if not duration_s or duration_s <= 0:
        logger.warning("invalid_duration", activity_id=activity.id)
        return None
    
    activity_data = {
        "sport_type": activity.sport_type.lower().strip(),
        "duration_s": duration_s,
        "distance_m": activity.distance_meters or 0,
    }
    
    # Add power data if available
    if activity.weighted_average_watts:
        activity_data["normalized_power"] = activity.weighted_average_watts
    elif activity.average_watts:
        activity_data["avg_power"] = activity.average_watts
    
    # Add HR data
    if activity.average_heartrate:
        activity_data["avg_hr"] = int(activity.average_heartrate)
    
    # Calculate pace
    if activity.distance_meters and activity.distance_meters > 0:
        distance_km = activity.distance_meters / 1000.0
        duration_min = duration_s / 60.0
        if distance_km > 0:
            activity_data["avg_pace_min_per_km"] = duration_min / distance_km
    
    return activity_data

