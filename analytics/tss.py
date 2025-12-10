# analytics/tss.py

import math

def calculate_bike_tss(duration_seconds: float, 
                      normalized_power: float, 
                      ftp: float) -> float:
    """
    Calculate Bike TSS (Training Stress Score)
    Based on GoldenCheetah BasicRideMetrics.cpp
    
    Formula: TSS = (duration_hours × NP × IF) / (FTP × 3600) × 100
    Where IF (Intensity Factor) = NP / FTP
    
    Args:
        duration_seconds: Total ride time in seconds
        normalized_power: NP (Normalized Power) for the ride
        ftp: Functional Threshold Power (watts)
    
    Returns:
        TSS score (typically 0-200+)
    """
    if ftp <= 0 or duration_seconds <= 0:
        return 0.0
    
    duration_hours = duration_seconds / 3600.0
    intensity_factor = normalized_power / ftp
    
    # TSS = (duration × NP × IF) / (FTP × 3600) × 100
    # Simplified: TSS = duration_hours × IF² × 100
    tss = duration_hours * (intensity_factor ** 2) * 100
    
    return round(tss, 1)


def calculate_run_tss(duration_minutes: float,
                     avg_pace_min_per_km: float,
                     threshold_pace_min_per_km: float) -> float:
    """
    Calculate Run TSS
    Based on pace ratio to threshold pace
    
    Args:
        duration_minutes: Total run time in minutes
        avg_pace_min_per_km: Average pace (e.g. 5.0 for 5:00/km)
        threshold_pace_min_per_km: Threshold pace (e.g. 4.0 for 4:00/km)
    
    Returns:
        TSS score
    """
    if avg_pace_min_per_km <= 0 or threshold_pace_min_per_km <= 0:
        return 0.0
    
    # Pace ratio (slower pace = lower ratio)
    # If threshold is 4:00/km and you run 5:00/km, ratio = 4/5 = 0.8
    pace_ratio = threshold_pace_min_per_km / avg_pace_min_per_km
    
    # TSS calculation based on intensity
    # Similar to bike TSS: TSS = duration × IF² × 100
    if pace_ratio < 0.85:  # Very easy (much slower than threshold)
        intensity_factor = 0.5
        tss = duration_minutes * (intensity_factor ** 2) * 100 / 60.0
    elif pace_ratio > 1.05:  # Faster than threshold (hard intervals)
        intensity_factor = pace_ratio ** 1.5
        tss = duration_minutes * (intensity_factor ** 2) * 100 / 60.0
    else:  # Around threshold
        intensity_factor = pace_ratio
        tss = duration_minutes * (intensity_factor ** 2) * 100 / 60.0
    
    return round(tss, 1)


def calculate_swim_tss(distance_meters: float,
                      duration_seconds: float,
                      css_pace_100m_seconds: float) -> float:
    """
    Calculate Swim TSS
    Based on CSS (Critical Swim Speed)
    
    Args:
        distance_meters: Total distance in meters
        duration_seconds: Total time in seconds
        css_pace_100m_seconds: CSS pace per 100m (e.g. 90 for 1:30/100m)
    
    Returns:
        TSS score
    """
    if distance_meters <= 0 or css_pace_100m_seconds <= 0 or duration_seconds <= 0:
        return 0.0
    
    # Calculate average pace per 100m in seconds
    avg_pace_100m = (duration_seconds / distance_meters) * 100.0
    
    # Pace ratio (faster = higher ratio)
    # If CSS is 90s/100m and you swim 100s/100m, ratio = 90/100 = 0.9
    pace_ratio = css_pace_100m_seconds / avg_pace_100m
    
    duration_minutes = duration_seconds / 60.0
    
    # Similar to run TSS
    if pace_ratio < 0.85:  # Very easy
        intensity_factor = 0.5
        tss = duration_minutes * (intensity_factor ** 2) * 100 / 60.0
    elif pace_ratio > 1.05:  # Faster than CSS (hard intervals)
        intensity_factor = pace_ratio ** 1.5
        tss = duration_minutes * (intensity_factor ** 2) * 100 / 60.0
    else:  # Around CSS
        intensity_factor = pace_ratio
        tss = duration_minutes * (intensity_factor ** 2) * 100 / 60.0
    
    return round(tss, 1)


def auto_calculate_tss(activity_data: dict, user_profile: dict) -> float:
    """
    Auto-calculate TSS based on sport type and available data
    
    Args:
        activity_data: {
            "sport_type": "running" | "cycling" | "swimming",
            "duration_s": 3600,
            "distance_m": 10000,
            "avg_power": 200,  # optional for cycling
            "normalized_power": 210,  # optional for cycling
            "avg_pace_min_per_km": 5.0,  # optional for running
            "avg_speed_m_s": 3.33,  # optional (will calculate pace)
        }
        user_profile: {
            "ftp": 250,  # for cycling
            "threshold_pace": 4.0,  # for running (min/km)
            "css_pace_100m": 90  # for swimming (seconds per 100m)
        }
    
    Returns:
        TSS score or 0 if can't calculate
    """
    sport = activity_data.get("sport_type", "").lower()
    duration_s = activity_data.get("duration_s", 0)
    
    if duration_s <= 0:
        return 0.0
    
    # Cycling TSS
    if sport in ["cycling", "bike", "ride"]:
        # Prefer normalized_power, fallback to avg_power
        np = activity_data.get("normalized_power") or activity_data.get("avg_power")
        ftp = user_profile.get("ftp")
        
        if np and ftp and ftp > 0:
            return calculate_bike_tss(duration_s, np, ftp)
    
    # Running TSS
    elif sport in ["running", "run"]:
        # Get pace from avg_pace_min_per_km or calculate from speed
        pace = activity_data.get("avg_pace_min_per_km")
        
        if not pace:
            # Calculate from speed if available
            speed_m_s = activity_data.get("avg_speed_m_s")
            if speed_m_s and speed_m_s > 0:
                pace = (1000.0 / speed_m_s) / 60.0  # Convert m/s to min/km
        
        threshold_pace = user_profile.get("threshold_pace")
        
        if pace and threshold_pace and threshold_pace > 0:
            duration_min = duration_s / 60.0
            return calculate_run_tss(duration_min, pace, threshold_pace)
    
    # Swimming TSS
    elif sport in ["swimming", "swim"]:
        distance_m = activity_data.get("distance_m", 0)
        css_pace = user_profile.get("css_pace_100m")
        
        if distance_m > 0 and css_pace and css_pace > 0:
            return calculate_swim_tss(distance_m, duration_s, css_pace)
    
    # Fallback: Simple duration-based estimate
    # 1 hour at moderate intensity ≈ 50-70 TSS
    duration_hours = duration_s / 3600.0
    return round(duration_hours * 60, 1)

