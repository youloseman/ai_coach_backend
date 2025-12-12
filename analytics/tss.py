# analytics/tss.py

def calculate_bike_tss(duration_seconds: float, 
                      normalized_power: float, 
                      ftp: float) -> float:
    """
    Calculate Bike TSS (Training Stress Score)
    Based on GoldenCheetah BasicRideMetrics.cpp
    
    Formula: TSS = duration_hours × (NP/FTP)² × 100 (algebraic simplification of the standard TP/GC formula)
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
    
    # TSS = duration_hours × (NP/FTP)² × 100
    tss = duration_hours * (intensity_factor ** 2) * 100
    
    return round(tss, 1)


def calculate_run_tss(duration_minutes: float,
                     avg_pace_min_per_km: float,
                     threshold_pace_min_per_km: float) -> float:
    """
    Calculate Run TSS based on pace
    Based on TrainingPeaks standard formula
    
    Formula: TSS = (duration_hours × IF²) × 100
    Where IF (Intensity Factor) = threshold_pace / avg_pace
    
    Args:
        duration_minutes: Total run time in minutes
        avg_pace_min_per_km: Average pace (e.g. 5.0 for 5:00/km)
        threshold_pace_min_per_km: Threshold pace (e.g. 4.0 for 4:00/km)
    
    Returns:
        TSS score
    
    Examples:
        >>> calculate_run_tss(60, 4.0, 4.0)  # 1 hour at threshold = 100 TSS
        100.0
        >>> calculate_run_tss(60, 5.0, 4.0)  # 1 hour easy (5:00 vs 4:00) = 64 TSS
        64.0
        >>> calculate_run_tss(60, 3.5, 4.0)  # 1 hour fast (3:30 vs 4:00) = 130 TSS
        130.6
    
    Reference:
        https://www.trainingpeaks.com/blog/what-is-tss/
    """
    # Validate inputs
    try:
        duration_minutes = float(duration_minutes)
        avg_pace_min_per_km = float(avg_pace_min_per_km)
        threshold_pace_min_per_km = float(threshold_pace_min_per_km)
    except (TypeError, ValueError):
        return 0.0
    
    if avg_pace_min_per_km <= 0 or threshold_pace_min_per_km <= 0:
        return 0.0
    
    if duration_minutes <= 0:
        return 0.0
    
    # Calculate Intensity Factor
    # IF = threshold_pace / avg_pace
    # Slower pace (5:00/km) / threshold (4:00/km) = 4/5 = 0.8 = easier
    # Faster pace (3:30/km) / threshold (4:00/km) = 4/3.5 = 1.14 = harder
    intensity_factor = threshold_pace_min_per_km / avg_pace_min_per_km
    intensity_factor = max(0.0, min(intensity_factor, 2.0))
    
    # Calculate TSS
    # TSS = duration_hours × IF² × 100
    duration_hours = duration_minutes / 60.0
    tss = duration_hours * (intensity_factor ** 2) * 100
    
    return round(tss, 1)


def calculate_swim_tss(distance_meters: float,
                      duration_seconds: float,
                      css_pace_100m_seconds: float) -> float:
    """
    Calculate Swim TSS
    Based on CSS (Critical Swim Speed)
    
    Formula: sTSS = duration_hours × (CSS_pace / avg_pace)² × 100
    
    Args:
        distance_meters: Total distance in meters
        duration_seconds: Total time in seconds
        css_pace_100m_seconds: CSS pace per 100m in seconds (e.g. 90 for 1:30/100m)
    
    Returns:
        TSS score
    """
    # Validate inputs
    try:
        distance_meters = float(distance_meters)
        duration_seconds = float(duration_seconds)
        css_pace_100m_seconds = float(css_pace_100m_seconds)
    except (TypeError, ValueError):
        return 0.0
    
    if distance_meters <= 0 or css_pace_100m_seconds <= 0 or duration_seconds <= 0:
        return 0.0
    
    # Calculate average pace per 100m in seconds
    avg_pace_100m = (duration_seconds / distance_meters) * 100.0
    
    # Calculate Intensity Factor
    # IF = CSS_pace / avg_pace (both in seconds per 100m)
    intensity_factor = css_pace_100m_seconds / avg_pace_100m
    intensity_factor = max(0.0, min(intensity_factor, 2.0))
    
    # Calculate TSS
    # TSS = duration_hours × IF² × 100
    duration_hours = duration_seconds / 3600.0
    tss = duration_hours * (intensity_factor ** 2) * 100
    
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
    
    # Fallback estimate when sport-specific inputs are missing.
    # Assumes ~50 TSS per 1 hour (moderate).
    duration_hours = duration_s / 3600.0
    return round(duration_hours * 50.0, 1)

