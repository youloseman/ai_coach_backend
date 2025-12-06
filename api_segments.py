"""
API endpoints for Strava segments, personal records, and injury risk analysis.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
import datetime as dt

from database import get_db
from auth import get_current_user
from models import User, SegmentDB, SegmentEffortDB, PersonalRecordDB, InjuryRiskDB
import crud
from pydantic import BaseModel
from segment_sync import (
    sync_all_segment_efforts, 
    scan_all_activities_for_prs,
    analyze_injury_risk
)
from strava_client import fetch_activities_last_n_weeks_for_user

router = APIRouter(prefix="/analytics", tags=["analytics"])


# ===== SCHEMAS =====

class SegmentResponse(BaseModel):
    id: int
    strava_segment_id: str
    name: str
    activity_type: str
    distance_meters: float
    average_grade: Optional[float]
    elevation_gain: Optional[float]
    athlete_count: int
    effort_count: int
    city: Optional[str]
    country: Optional[str]
    
    class Config:
        from_attributes = True


class SegmentEffortResponse(BaseModel):
    id: int
    strava_effort_id: str
    segment_name: str
    segment_distance: float
    start_date: dt.datetime
    elapsed_time_seconds: int
    moving_time_seconds: Optional[int]
    average_heartrate: Optional[float]
    average_watts: Optional[float]
    pr_rank: Optional[int]
    kom_rank: Optional[int]
    is_pr: bool
    
    class Config:
        from_attributes = True


class PersonalRecordResponse(BaseModel):
    id: int
    sport_type: str
    distance_category: str
    distance_meters: float
    time_seconds: int
    pace_per_km: Optional[float]
    speed_kmh: Optional[float]
    achieved_date: dt.datetime
    activity_name: Optional[str]
    is_current_pr: bool
    average_heartrate: Optional[float]
    
    class Config:
        from_attributes = True


class InjuryRiskResponse(BaseModel):
    id: int
    risk_level: str
    risk_type: str
    title: str
    description: str
    recommendation: str
    detected_date: dt.date
    acknowledged: bool
    resolved: bool
    trigger_metrics: Optional[dict]
    
    class Config:
        from_attributes = True


# ===== SEGMENT ENDPOINTS =====

@router.get("/segments", response_model=List[SegmentResponse])
async def get_user_segments(
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get Strava segments that the user has ridden/run.
    Returns unique segments with at least one effort.
    """
    segments = crud.get_user_segments(db, current_user.id, limit=limit)
    return segments


@router.get("/segment-efforts", response_model=List[SegmentEffortResponse])
async def get_user_segment_efforts(
    segment_id: Optional[int] = None,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get user's efforts on Strava segments.
    Optionally filter by segment_id to see all efforts on a specific segment.
    """
    efforts = crud.get_user_segment_efforts(db, current_user.id, segment_id=segment_id, limit=limit)
    
    # Enrich with segment data
    result = []
    for effort in efforts:
        segment = db.query(SegmentDB).filter(SegmentDB.id == effort.segment_id).first()
        result.append({
            "id": effort.id,
            "strava_effort_id": effort.strava_effort_id,
            "segment_name": segment.name if segment else "Unknown",
            "segment_distance": segment.distance_meters if segment else 0,
            "start_date": effort.start_date,
            "elapsed_time_seconds": effort.elapsed_time_seconds,
            "moving_time_seconds": effort.moving_time_seconds,
            "average_heartrate": effort.average_heartrate,
            "average_watts": effort.average_watts,
            "pr_rank": effort.pr_rank,
            "kom_rank": effort.kom_rank,
            "is_pr": effort.is_pr,
        })
    
    return result


@router.get("/segment-prs", response_model=List[SegmentEffortResponse])
async def get_user_segment_prs(
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get user's personal records on Strava segments.
    Only returns efforts where is_pr=True.
    """
    prs = crud.get_user_prs_on_segments(db, current_user.id, limit=limit)
    
    result = []
    for effort in prs:
        segment = db.query(SegmentDB).filter(SegmentDB.id == effort.segment_id).first()
        result.append({
            "id": effort.id,
            "strava_effort_id": effort.strava_effort_id,
            "segment_name": segment.name if segment else "Unknown",
            "segment_distance": segment.distance_meters if segment else 0,
            "start_date": effort.start_date,
            "elapsed_time_seconds": effort.elapsed_time_seconds,
            "moving_time_seconds": effort.moving_time_seconds,
            "average_heartrate": effort.average_heartrate,
            "average_watts": effort.average_watts,
            "pr_rank": effort.pr_rank,
            "kom_rank": effort.kom_rank,
            "is_pr": True,
        })
    
    return result


# ===== PERSONAL RECORD ENDPOINTS =====

@router.get("/personal-records", response_model=List[PersonalRecordResponse])
async def get_personal_records(
    sport_type: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get user's current personal records for different distances.
    
    Examples:
    - 5K run
    - 10K run
    - Half Marathon
    - Marathon
    - 40K bike
    - 1500m swim
    """
    records = crud.get_current_personal_records(db, current_user.id, sport_type=sport_type)
    return records


@router.get("/personal-records/{sport_type}/{distance_category}", response_model=List[PersonalRecordResponse])
async def get_pr_history(
    sport_type: str,
    distance_category: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get historical progression of a specific personal record.
    
    Example: /personal-records/run/5K
    Returns all PRs for 5K run, showing progression over time.
    """
    history = crud.get_pr_history(db, current_user.id, sport_type, distance_category)
    return history


# ===== INJURY RISK ENDPOINTS =====

@router.get("/injury-risks", response_model=List[InjuryRiskResponse])
async def get_injury_risks(
    active_only: bool = True,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get injury risk warnings for the user.
    
    By default, only returns active (unresolved) risks.
    Set active_only=false to see all historical risks.
    """
    if active_only:
        risks = crud.get_active_injury_risks(db, current_user.id)
    else:
        risks = db.query(InjuryRiskDB).filter(
            InjuryRiskDB.user_id == current_user.id
        ).order_by(InjuryRiskDB.detected_date.desc()).all()
    
    return risks


@router.post("/injury-risks/{risk_id}/acknowledge")
async def acknowledge_injury_risk(
    risk_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Mark an injury risk warning as acknowledged (user has seen it).
    """
    risk = db.query(InjuryRiskDB).filter(InjuryRiskDB.id == risk_id).first()
    
    if not risk:
        raise HTTPException(status_code=404, detail="Risk not found")
    
    if risk.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    risk = crud.acknowledge_injury_risk(db, risk_id)
    return {"status": "ok", "acknowledged": True}


@router.post("/injury-risks/{risk_id}/resolve")
async def resolve_injury_risk(
    risk_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Mark an injury risk warning as resolved (issue is addressed).
    """
    risk = db.query(InjuryRiskDB).filter(InjuryRiskDB.id == risk_id).first()
    
    if not risk:
        raise HTTPException(status_code=404, detail="Risk not found")
    
    if risk.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    risk = crud.resolve_injury_risk(db, risk_id)
    return {"status": "ok", "resolved": True}


# ===== STATS & SUMMARY ENDPOINTS =====

@router.get("/performance-summary")
async def get_performance_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get overall performance summary:
    - Total PRs
    - Recent PRs (last 30 days)
    - Active injury risks
    - Segment achievements
    """
    # Current PRs
    current_prs = crud.get_current_personal_records(db, current_user.id)
    
    # Recent PRs (last 30 days)
    thirty_days_ago = dt.datetime.now() - dt.timedelta(days=30)
    recent_prs = [pr for pr in current_prs if pr.achieved_date >= thirty_days_ago]
    
    # Active injury risks
    active_risks = crud.get_active_injury_risks(db, current_user.id)
    
    # Segment PRs
    segment_prs = crud.get_user_prs_on_segments(db, current_user.id, limit=100)
    recent_segment_prs = [e for e in segment_prs if e.start_date >= thirty_days_ago]
    
    return {
        "total_personal_records": len(current_prs),
        "recent_prs_30_days": len(recent_prs),
        "active_injury_risks": len(active_risks),
        "high_risk_warnings": len([r for r in active_risks if r.risk_level in ["high", "critical"]]),
        "total_segment_prs": len(segment_prs),
        "recent_segment_prs_30_days": len(recent_segment_prs),
        "personal_records_by_sport": {
            "run": len([pr for pr in current_prs if pr.sport_type == "run"]),
            "bike": len([pr for pr in current_prs if pr.sport_type == "bike"]),
            "swim": len([pr for pr in current_prs if pr.sport_type == "swim"]),
        }
    }


# ===== SYNC ENDPOINTS =====

@router.post("/sync-segments")
async def sync_segments(
    limit_activities: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Manually trigger sync of segment efforts for user's recent activities.
    
    This will fetch detailed activity data from Strava including segment efforts,
    and save them to the database.
    """
    total_synced = await sync_all_segment_efforts(db, current_user.id, limit_activities=limit_activities)
    
    return {
        "status": "ok",
        "segments_synced": total_synced,
        "activities_checked": limit_activities
    }


@router.post("/scan-prs")
async def scan_personal_records(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Scan all user activities and detect personal records.
    
    This will analyze all activities in the database and identify PRs for:
    - Run: 5K, 10K, Half Marathon, Marathon, etc.
    - Bike: 20K, 40K, 100K, etc.
    - Swim: 400m, 1000m, 1500m, etc.
    """
    result = scan_all_activities_for_prs(db, current_user.id)
    
    return {
        "status": "ok",
        **result
    }


@router.post("/analyze-injury-risk")
async def run_injury_risk_analysis(
    weeks: int = 12,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Run AI-based injury risk analysis on user's recent training.
    
    Analyzes:
    - Training load trends (CTL/ATL/TSB)
    - Volume spikes
    - Fatigue indicators
    - Recovery patterns
    
    Creates InjuryRisk records if any risks are detected.
    """
    # Fetch recent activities
    activities = await fetch_activities_last_n_weeks_for_user(
        user_id=current_user.id,
        weeks=weeks,
        db=db
    )
    
    if not activities:
        raise HTTPException(status_code=400, detail="No activities found for analysis")
    
    # Run analysis
    risks = await analyze_injury_risk(db, current_user.id, activities)
    
    return {
        "status": "ok",
        "risks_detected": len(risks),
        "risks": risks
    }

