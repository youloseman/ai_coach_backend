# api_analytics.py

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from database import get_db
from models import User
from auth import get_current_user
from analytics.pmc import PMCCalculator
from analytics.tss import auto_calculate_tss
from strava_client import fetch_activities_last_n_weeks_for_user
from athlete_profile import load_athlete_profile
from config import logger

router = APIRouter()


@router.get("/analytics/pmc")
async def get_pmc_data(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    lts_days: int = Query(42, ge=7, le=84, description="Long Term Stress period (days)"),
    sts_days: int = Query(7, ge=3, le=21, description="Short Term Stress period (days)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get Performance Management Chart data
    
    Returns CTL/ATL/TSB/RR arrays for visualization
    
    Args:
        start_date: Start date (YYYY-MM-DD), defaults to 90 days ago
        end_date: End date (YYYY-MM-DD), defaults to today
        lts_days: Long Term Stress period (default: 42 days for CTL)
        sts_days: Short Term Stress period (default: 7 days for ATL)
    
    Returns:
        {
            "dates": [...],
            "stress": [...],  # Daily TSS
            "ctl": [...],     # Fitness
            "atl": [...],     # Fatigue
            "tsb": [...],     # Form
            "rr": [...]       # Ramp Rate
        }
    """
    try:
        # Parse dates
        if not end_date:
            end_dt = datetime.now()
        else:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        
        if not start_date:
            start_dt = end_dt - timedelta(days=90)
        else:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        
        # Fetch activities from Strava
        activities = await fetch_activities_last_n_weeks_for_user(
            current_user.id, 
            db, 
            weeks=13  # ~90 days
        )
        
        if not activities:
            return {
                "dates": [],
                "stress": [],
                "ctl": [],
                "atl": [],
                "tsb": [],
                "rr": [],
                "message": "No activities found. Connect Strava to see your PMC data."
            }
        
        # Load athlete profile for TSS calculation
        profile = load_athlete_profile()
        profile_dict = profile.model_dump() if profile else {}
        
        # Prepare activity data with TSS
        activity_data = []
        for act in activities:
            act_date = act.get("start_date") or act.get("start_date_local")
            if not act_date:
                continue
            
            # Parse date
            if isinstance(act_date, str):
                try:
                    date_obj = datetime.strptime(act_date.split("T")[0], "%Y-%m-%d")
                except:
                    continue
            else:
                date_obj = act_date
            
            # Skip if outside date range
            if date_obj.date() < start_dt.date() or date_obj.date() > end_dt.date():
                continue
            
            # Calculate TSS
            user_profile = {
                "ftp": profile_dict.get("ftp") or profile_dict.get("training_zones_bike", {}).get("ftp"),
                "threshold_pace": profile_dict.get("threshold_pace") or profile_dict.get("training_zones_run", {}).get("threshold_pace"),
                "css_pace_100m": profile_dict.get("css_pace_100m") or profile_dict.get("training_zones_swim", {}).get("css_pace_100m"),
            }
            
            tss = auto_calculate_tss(act, user_profile)
            
            if tss > 0:
                activity_data.append({
                    "date": date_obj.strftime("%Y-%m-%d"),
                    "tss": tss
                })
        
        if not activity_data:
            return {
                "dates": [],
                "stress": [],
                "ctl": [],
                "atl": [],
                "tsb": [],
                "rr": [],
                "message": "No activities with TSS found in date range."
            }
        
        # Calculate PMC
        calculator = PMCCalculator(lts_days=lts_days, sts_days=sts_days)
        pmc_data = calculator.calculate_pmc(activity_data)
        
        return pmc_data
        
    except Exception as e:
        logger.error("pmc_calculation_error", error=str(e), user_id=current_user.id)
        raise HTTPException(status_code=500, detail=f"Failed to calculate PMC: {str(e)}")


@router.get("/analytics/summary")
async def get_analytics_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get current fitness summary
    
    Returns:
    {
        "ctl": 85.3,
        "atl": 72.1,
        "tsb": 13.2,
        "rr": 5.2,
        "status": "optimal",
        "message": "Ready to race!",
        "form_status": "optimal_race"
    }
    """
    try:
        # Get last 90 days of activities
        activities = await fetch_activities_last_n_weeks_for_user(
            current_user.id,
            db,
            weeks=13
        )
        
        if not activities:
            return {
                "ctl": 0.0,
                "atl": 0.0,
                "tsb": 0.0,
                "rr": 0.0,
                "status": "no_data",
                "message": "No training data yet. Connect Strava to get started!",
                "form_status": "no_data"
            }
        
        # Load profile for TSS calculation
        profile = load_athlete_profile()
        profile_dict = profile.model_dump() if profile else {}
        
        # Prepare activity data with TSS
        activity_data = []
        for act in activities:
            act_date = act.get("start_date") or act.get("start_date_local")
            if not act_date:
                continue
            
            if isinstance(act_date, str):
                try:
                    date_obj = datetime.strptime(act_date.split("T")[0], "%Y-%m-%d")
                except:
                    continue
            else:
                date_obj = act_date
            
            user_profile = {
                "ftp": profile_dict.get("ftp") or profile_dict.get("training_zones_bike", {}).get("ftp"),
                "threshold_pace": profile_dict.get("threshold_pace") or profile_dict.get("training_zones_run", {}).get("threshold_pace"),
                "css_pace_100m": profile_dict.get("css_pace_100m") or profile_dict.get("training_zones_swim", {}).get("css_pace_100m"),
            }
            
            tss = auto_calculate_tss(act, user_profile)
            
            if tss > 0:
                activity_data.append({
                    "date": date_obj.strftime("%Y-%m-%d"),
                    "tss": tss
                })
        
        if not activity_data:
            return {
                "ctl": 0.0,
                "atl": 0.0,
                "tsb": 0.0,
                "rr": 0.0,
                "status": "no_data",
                "message": "No activities with TSS found.",
                "form_status": "no_data"
            }
        
        calculator = PMCCalculator()
        pmc = calculator.calculate_pmc(activity_data)
        
        # Get latest values
        # Find last non-zero CTL
        latest_idx = len(pmc["dates"]) - 1
        for i in range(latest_idx, 0, -1):
            if pmc["ctl"][i] > 0:
                latest_idx = i
                break
        
        latest = {
            "ctl": round(pmc["ctl"][latest_idx], 1),
            "atl": round(pmc["atl"][latest_idx], 1),
            "tsb": round(pmc["tsb"][latest_idx], 1),
            "rr": round(pmc["rr"][latest_idx], 1)
        }
        
        # Determine status based on TSB
        tsb = latest["tsb"]
        rr = latest["rr"]
        
        if tsb < -30:
            status = "overtrained"
            message = "⚠️ High fatigue! Consider rest days."
        elif -5 <= tsb <= 5:
            status = "optimal"
            message = "✅ Optimal training zone. Keep it up!"
        elif 5 < tsb < 15:
            status = "race_ready"
            message = "🎯 You're race ready!"
        elif tsb > 15:
            status = "detraining"
            message = "⚠️ Fitness declining. Increase load."
        else:
            status = "fresh"
            message = "💪 Fresh and ready for hard training!"
        
        if rr > 8:
            message += " ⚠️ Warning: Ramp rate too high!"
        
        # Get form status from calculator
        form_status = calculator._interpret_tsb(tsb)
        
        return {
            **latest,
            "status": status,
            "message": message,
            "form_status": form_status
        }
        
    except Exception as e:
        logger.error("analytics_summary_error", error=str(e), user_id=current_user.id)
        raise HTTPException(status_code=500, detail=f"Failed to calculate summary: {str(e)}")

