"""
Synchronization of Strava segments and automatic PR detection.
"""

import httpx
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
import datetime as dt

from config import logger
import crud
from models import ActivityDB
from strava_client import get_valid_access_token


# ===== SEGMENT SYNC =====

async def sync_segment_efforts_for_activity(
    db: Session,
    user_id: int,
    activity_db: ActivityDB,
    strava_activity_id: str
) -> int:
    """
    Fetch and sync segment efforts for a specific activity.
    
    Returns:
        Number of segment efforts synced
    """
    try:
        access_token = await get_valid_access_token()
        
        # Fetch activity details with segments
        url = f"https://www.strava.com/api/v3/activities/{strava_activity_id}"
        headers = {"Authorization": f"Bearer {access_token}"}
        
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=headers)
        
        if resp.status_code != 200:
            logger.warning("failed_to_fetch_activity_details", 
                         activity_id=strava_activity_id, 
                         status=resp.status_code)
            return 0
        
        activity_data = resp.json()
        segment_efforts = activity_data.get("segment_efforts", [])
        
        if not segment_efforts:
            logger.debug("no_segment_efforts_found", activity_id=strava_activity_id)
            return 0
        
        synced_count = 0
        
        for effort in segment_efforts:
            try:
                # First, upsert the segment
                segment_data = effort.get("segment", {})
                if not segment_data or "id" not in segment_data:
                    continue
                
                segment_db = crud.upsert_segment(db, segment_data)
                
                # Then, upsert the effort
                crud.upsert_segment_effort(
                    db=db,
                    user_id=user_id,
                    activity_db_id=activity_db.id,
                    strava_effort=effort,
                    segment_db_id=segment_db.id
                )
                
                synced_count += 1
                
            except Exception as e:
                logger.error("failed_to_sync_segment_effort", 
                           effort_id=effort.get("id"),
                           error=str(e))
                continue
        
        logger.info("segment_efforts_synced", 
                   activity_id=strava_activity_id,
                   count=synced_count)
        
        return synced_count
        
    except Exception as e:
        logger.error("segment_sync_error", 
                    activity_id=strava_activity_id,
                    error=str(e))
        return 0


async def sync_all_segment_efforts(db: Session, user_id: int, limit_activities: int = 50) -> int:
    """
    Sync segment efforts for user's recent activities.
    
    Returns:
        Total number of segment efforts synced
    """
    # Get recent activities from DB
    activities = db.query(ActivityDB).filter(
        ActivityDB.user_id == user_id
    ).order_by(ActivityDB.start_date.desc()).limit(limit_activities).all()
    
    if not activities:
        logger.info("no_activities_to_sync_segments")
        return 0
    
    total_synced = 0
    
    for activity in activities:
        count = await sync_segment_efforts_for_activity(
            db=db,
            user_id=user_id,
            activity_db=activity,
            strava_activity_id=activity.strava_id
        )
        total_synced += count
    
    logger.info("all_segment_efforts_synced", 
               user_id=user_id,
               activities_checked=len(activities),
               total_efforts=total_synced)
    
    return total_synced


# ===== PERSONAL RECORD DETECTION =====

def detect_personal_records(db: Session, user_id: int, activity: ActivityDB) -> List[str]:
    """
    Detect if an activity contains any personal records.
    
    Checks for standard race distances:
    - Run: 5K, 10K, HM (21.1K), Marathon (42.2K)
    - Bike: 20K, 40K, 100K
    - Swim: 400m, 1000m, 1500m, 3800m
    
    Returns:
        List of PRs detected (e.g., ["5K", "10K"])
    """
    if not activity.distance_meters or not activity.moving_time_seconds:
        return []
    
    sport_type = _normalize_sport_type(activity.sport_type)
    if sport_type == "unknown":
        return []
    
    distance_km = activity.distance_meters / 1000
    time_seconds = activity.moving_time_seconds
    
    # Define distance categories and their ranges
    distance_categories = _get_distance_categories(sport_type)
    
    prs_detected = []
    
    for category_name, (min_dist, max_dist) in distance_categories.items():
        if min_dist <= distance_km <= max_dist:
            # Check if this is a PR
            is_pr = _check_if_pr(
                db=db,
                user_id=user_id,
                sport_type=sport_type,
                distance_category=category_name,
                distance_meters=activity.distance_meters,
                time_seconds=time_seconds
            )
            
            if is_pr:
                # Create PR record
                crud.create_personal_record(
                    db=db,
                    user_id=user_id,
                    activity_db_id=activity.id,
                    sport_type=sport_type,
                    distance_category=category_name,
                    distance_meters=activity.distance_meters,
                    time_seconds=time_seconds,
                    achieved_date=activity.start_date,
                    activity_name=activity.name,
                    average_heartrate=activity.average_heartrate,
                    average_watts=activity.average_watts,
                    elevation_gain=activity.total_elevation_gain
                )
                
                prs_detected.append(category_name)
                logger.info("personal_record_detected",
                          user_id=user_id,
                          sport=sport_type,
                          distance=category_name,
                          time=time_seconds)
    
    return prs_detected


def _normalize_sport_type(sport_type: str) -> str:
    """Normalize sport type to run/bike/swim."""
    sport_lower = sport_type.lower()
    
    if any(x in sport_lower for x in ["run", "trail", "track"]):
        return "run"
    elif any(x in sport_lower for x in ["ride", "bike", "cycling", "virtual"]):
        return "bike"
    elif any(x in sport_lower for x in ["swim"]):
        return "swim"
    else:
        return "unknown"


def _get_distance_categories(sport_type: str) -> Dict[str, tuple]:
    """
    Get distance categories with (min_km, max_km) ranges.
    """
    if sport_type == "run":
        return {
            "5K": (4.5, 5.5),
            "10K": (9.5, 10.5),
            "15K": (14.5, 15.5),
            "HM": (20.0, 22.0),  # Half Marathon
            "25K": (24.0, 26.0),
            "30K": (29.0, 31.0),
            "Marathon": (41.0, 43.0),
            "50K": (48.0, 52.0),
        }
    elif sport_type == "bike":
        return {
            "20K": (18.0, 22.0),
            "40K": (38.0, 42.0),
            "60K": (58.0, 62.0),
            "80K": (78.0, 82.0),
            "100K": (95.0, 105.0),
            "120K": (115.0, 125.0),
            "160K": (155.0, 165.0),
            "180K": (175.0, 185.0),
        }
    elif sport_type == "swim":
        return {
            "400m": (0.35, 0.45),
            "800m": (0.75, 0.85),
            "1000m": (0.95, 1.05),
            "1500m": (1.4, 1.6),
            "3800m": (3.6, 4.0),
        }
    else:
        return {}


def _check_if_pr(
    db: Session,
    user_id: int,
    sport_type: str,
    distance_category: str,
    distance_meters: float,
    time_seconds: int
) -> bool:
    """
    Check if this time is a personal record for the distance category.
    """
    # Get current PR for this distance
    existing_prs = crud.get_pr_history(db, user_id, sport_type, distance_category)
    
    if not existing_prs:
        # No existing PR - this is the first one
        return True
    
    # Check if this time is better than current PR
    current_pr = existing_prs[0]  # First one is most recent
    
    # Lower time is better
    return time_seconds < current_pr.time_seconds


def scan_all_activities_for_prs(db: Session, user_id: int) -> Dict[str, int]:
    """
    Scan all user activities and detect personal records.
    
    Returns:
        Dictionary with counts: {"total_activities": X, "prs_detected": Y}
    """
    activities = db.query(ActivityDB).filter(
        ActivityDB.user_id == user_id
    ).order_by(ActivityDB.start_date.asc()).all()  # Process oldest first
    
    total_prs = 0
    
    for activity in activities:
        prs = detect_personal_records(db, user_id, activity)
        total_prs += len(prs)
    
    logger.info("pr_scan_complete",
               user_id=user_id,
               activities_scanned=len(activities),
               prs_detected=total_prs)
    
    return {
        "total_activities": len(activities),
        "prs_detected": total_prs
    }


# ===== INJURY RISK DETECTION =====

async def analyze_injury_risk(
    db: Session,
    user_id: int,
    activities: List[dict],
    training_load: Optional[dict] = None
) -> List[Dict]:
    """
    Analyze training data for injury risk factors.
    
    Checks for:
    - Sudden volume spikes (>10% week-over-week)
    - Chronic high TSB (overreaching)
    - Consecutive high-intensity days
    - Insufficient recovery
    
    Returns:
        List of detected risks
    """
    from analytics import analyze_training_load
    from fatigue_detection import detect_fatigue
    
    risks = []
    
    # Get or calculate training load
    if not training_load:
        training_load = analyze_training_load(activities, weeks_to_analyze=12)
    
    current_ctl = training_load.get("current_ctl", 0)
    current_atl = training_load.get("current_atl", 0)
    current_tsb = training_load.get("current_tsb", 0)
    ramp_rate = training_load.get("ramp_rate", 0)
    
    # Risk 1: Negative TSB (fatigue > fitness)
    if current_tsb < -30:
        risks.append({
            "risk_level": "high" if current_tsb < -50 else "medium",
            "risk_type": "negative_tsb",
            "title": "High Fatigue Level",
            "description": f"Your TSB is {current_tsb:.1f}, indicating accumulated fatigue. You're training harder than your body can recover from.",
            "recommendation": "Take 2-3 easy days or a full rest day. Reduce training volume by 30-40% this week.",
            "trigger_metrics": {
                "tsb": current_tsb,
                "ctl": current_ctl,
                "atl": current_atl
            }
        })
    
    # Risk 2: High ramp rate (>5-8 TSS/day per week)
    if ramp_rate > 8:
        risks.append({
            "risk_level": "high" if ramp_rate > 12 else "medium",
            "risk_type": "high_ramp_rate",
            "title": "Training Load Increasing Too Fast",
            "description": f"Your training load is increasing by {ramp_rate:.1f} TSS/day per week. Safe rate is <8 TSS/day.",
            "recommendation": "Reduce weekly volume by 20-30%. Follow the 10% rule: don't increase weekly training by more than 10%.",
            "trigger_metrics": {
                "ramp_rate": ramp_rate,
                "ctl": current_ctl
            }
        })
    
    # Risk 3: Fatigue indicators
    fatigue_report = detect_fatigue(activities)
    if fatigue_report.overall_fatigue_level in ["high", "critical"]:
        risks.append({
            "risk_level": fatigue_report.overall_fatigue_level,
            "risk_type": "fatigue_detected",
            "title": "Multiple Fatigue Indicators Detected",
            "description": f"Fatigue score: {fatigue_report.fatigue_score}/100. {len(fatigue_report.indicators)} warning signs.",
            "recommendation": "; ".join(fatigue_report.recommendations),
            "trigger_metrics": {
                "fatigue_score": fatigue_report.fatigue_score,
                "indicators": [ind.type for ind in fatigue_report.indicators],
                "days_since_rest": fatigue_report.days_since_rest
            }
        })
    
    # Risk 4: Very high CTL without gradual build
    if current_ctl > 100 and ramp_rate > 10:
        risks.append({
            "risk_level": "medium",
            "risk_type": "high_ctl_with_spike",
            "title": "High Fitness with Rapid Build",
            "description": f"CTL of {current_ctl:.0f} combined with fast ramp rate increases injury risk.",
            "recommendation": "Implement a recovery week (50% volume reduction) within the next 2 weeks.",
            "trigger_metrics": {
                "ctl": current_ctl,
                "ramp_rate": ramp_rate
            }
        })
    
    # Save risks to database
    today = dt.date.today()
    for risk_data in risks:
        # Check if this type of risk was already detected recently (last 7 days)
        existing = db.query(crud.InjuryRiskDB).filter(
            crud.InjuryRiskDB.user_id == user_id,
            crud.InjuryRiskDB.risk_type == risk_data["risk_type"],
            crud.InjuryRiskDB.detected_date >= today - dt.timedelta(days=7),
            crud.InjuryRiskDB.resolved == False
        ).first()
        
        if not existing:
            crud.create_injury_risk(
                db=db,
                user_id=user_id,
                risk_level=risk_data["risk_level"],
                risk_type=risk_data["risk_type"],
                title=risk_data["title"],
                description=risk_data["description"],
                recommendation=risk_data["recommendation"],
                trigger_metrics=risk_data["trigger_metrics"],
                detected_date=today
            )
    
    return risks

