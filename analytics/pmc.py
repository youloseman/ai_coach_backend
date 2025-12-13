# analytics/pmc.py

import math
from datetime import datetime, timedelta
from typing import List, Dict, Optional

class PMCCalculator:
    """
    Performance Management Chart Calculator
    Based on GoldenCheetah PMCData.cpp
    
    Calculates:
    - CTL (Chronic Training Load / Fitness) - 42-day exponential average
    - ATL (Acute Training Load / Fatigue) - 7-day exponential average
    - TSB (Training Stress Balance / Form) = CTL - ATL
    - RR (Ramp Rate) - Rate of fitness increase
    """
    
    def __init__(self, lts_days: int = 42, sts_days: int = 7):
        """
        Args:
            lts_days: Long Term Stress period (default: 42)
            sts_days: Short Term Stress period (default: 7)
        """
        self.lts_days = lts_days
        self.sts_days = sts_days
        
        # Exponential decay constants (from GoldenCheetah)
        self.lte = math.exp(-1.0 / lts_days)  # ~0.9764 for 42 days
        self.ste = math.exp(-1.0 / sts_days)  # ~0.8670 for 7 days
    
    def calculate_pmc(self, activities: List[Dict]) -> Dict:
        """
        Calculate PMC from activities
        
        Args:
            activities: [
                {"date": "2025-01-01", "tss": 100},
                {"date": "2025-01-02", "tss": 80},
                ...
            ]
        
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
        if not activities:
            return {
                "dates": [],
                "stress": [],
                "ctl": [],
                "atl": [],
                "tsb": [],
                "rr": []
            }
        
        # Remove duplicates by id/strava_id
        seen_ids = set()
        unique_activities = []
        for activity in activities:
            activity_id = activity.get("id") or activity.get("strava_id")
            if activity_id and activity_id not in seen_ids:
                seen_ids.add(activity_id)
                unique_activities.append(activity)
            elif not activity_id:
                unique_activities.append(activity)
        
        activities = unique_activities
        
        # Sort by date
        activities = sorted(activities, key=lambda x: x["date"])
        
        # Date range - handle both string and datetime
        first_date = activities[0]["date"]
        last_date = activities[-1]["date"]
        
        if isinstance(first_date, str):
            start_date = datetime.strptime(first_date, "%Y-%m-%d")
        else:
            start_date = first_date  # Already datetime
        
        if isinstance(last_date, str):
            end_date = datetime.strptime(last_date, "%Y-%m-%d")
        else:
            end_date = last_date  # Already datetime
        
        # Create arrays
        days = (end_date - start_date).days + 1
        dates = [(start_date + timedelta(days=i)).strftime("%Y-%m-%d") 
                 for i in range(days)]
        
        stress = [0.0] * days
        ctl = [0.0] * days
        atl = [0.0] * days
        tsb = [0.0] * days
        rr = [0.0] * days
        
        # Fill stress array (daily TSS)
        # Pre-parse all dates for performance
        for activity in activities:
            try:
                if isinstance(activity["date"], str):
                    act_date = datetime.strptime(activity["date"], "%Y-%m-%d")
                else:
                    act_date = activity["date"]  # Already datetime
            except (ValueError, KeyError):
                continue
            
            offset = (act_date - start_date).days
            if 0 <= offset < days:
                tss = activity.get("tss", 0)
                # Validate TSS
                if tss < 0:
                    tss = 0
                elif tss > 1000:
                    tss = 500  # Cap at reasonable max
                stress[offset] += tss
        
        # Calculate CTL and ATL using exponential moving average
        # Based on GoldenCheetah PMCData.cpp lines 341-367
        for day in range(days):
            last_ctl = ctl[day - 1] if day > 0 else 0.0
            last_atl = atl[day - 1] if day > 0 else 0.0
            
            # CTL (Fitness) - exponential moving average over 42 days
            # Formula: CTL_today = TSS_today * (1 - exp(-1/42)) + CTL_yesterday * exp(-1/42)
            ctl[day] = (stress[day] * (1.0 - self.lte)) + (last_ctl * self.lte)
            
            # ATL (Fatigue) - exponential moving average over 7 days
            # Formula: ATL_today = TSS_today * (1 - exp(-1/7)) + ATL_yesterday * exp(-1/7)
            atl[day] = (stress[day] * (1.0 - self.ste)) + (last_atl * self.ste)
            
            # TSB (Form) = CTL - ATL
            # Positive TSB = fresh/rested, Negative TSB = fatigued
            tsb[day] = ctl[day] - atl[day]
            
            # Ramp Rate - CORRECTED FORMULA
            # RR = CTL points per week over the last sts_days window
            # Formula: RR = (CTL_today - CTL_7days_ago) / 7 * 7 = CTL_change / sts_days * 7
            # TrainingPeaks considers RR > 5-8 as high risk for overtraining
            if day >= self.sts_days:
                ctl_change = ctl[day] - ctl[day - self.sts_days]
                rr[day] = (ctl_change / self.sts_days) * 7.0
            else:
                # Not enough history yet
                rr[day] = 0.0
        
        return {
            "dates": dates,
            "stress": stress,
            "ctl": ctl,
            "atl": atl,
            "tsb": tsb,
            "rr": rr
        }
    
    def get_current_metrics(self, activities: List[Dict]) -> Optional[Dict]:
        """
        Get current (latest) PMC metrics
        
        Returns:
            {
                "date": "2025-12-10",
                "ctl": 85.3,
                "atl": 72.1,
                "tsb": 13.2,
                "rr": 5.2,
                "form_status": "optimal"
            }
        """
        pmc = self.calculate_pmc(activities)
        
        if not pmc["dates"]:
            return None
        
        # Current metrics should be computed at the last activity date
        last_activity_date = max(a["date"] for a in activities)
        
        if isinstance(last_activity_date, datetime):
            last_activity_date_str = last_activity_date.strftime("%Y-%m-%d")
        else:
            last_activity_date_str = str(last_activity_date)
        
        latest_idx = pmc["dates"].index(last_activity_date_str)
        
        return {
            "date": pmc["dates"][latest_idx],
            "ctl": round(pmc["ctl"][latest_idx], 1),
            "atl": round(pmc["atl"][latest_idx], 1),
            "tsb": round(pmc["tsb"][latest_idx], 1),
            "rr": round(pmc["rr"][latest_idx], 1),
            "form_status": self._interpret_tsb(pmc["tsb"][latest_idx])
        }
    
    def _interpret_tsb(self, tsb: float) -> str:
        """
        Interpret TSB (Form) value
        
        TSB Guidelines (from TrainingPeaks):
        > 25: Race Ready (peaked, very fresh)
        10 to 25: Fresh (good for hard training)
        -10 to 10: Neutral (optimal training zone)
        -30 to -10: Optimal Overload (building fitness)
        < -30: High Risk (overreaching/overtraining)
        """
        if tsb > 25:
            return "peaked"
        elif tsb > 10:
            return "fresh"
        elif tsb > -10:
            return "neutral"
        elif tsb >= -30:
            return "optimal_overload"
        else:
            return "high_risk"

