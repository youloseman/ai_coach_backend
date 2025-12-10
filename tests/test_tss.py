# tests/test_tss.py

import pytest
from analytics.tss import (
    calculate_bike_tss,
    calculate_run_tss,
    calculate_swim_tss,
    auto_calculate_tss
)

def test_bike_tss_basic():
    """Test bike TSS calculation"""
    # 1 hour at FTP (IF=1.0) should give ~100 TSS
    duration_s = 3600  # 1 hour
    np = 250  # Normalized Power
    ftp = 250  # FTP
    
    tss = calculate_bike_tss(duration_s, np, ftp)
    
    # TSS = 1 hour × 1.0² × 100 = 100
    assert abs(tss - 100.0) < 1.0


def test_bike_tss_hard_ride():
    """Test bike TSS for hard ride (above FTP)"""
    duration_s = 1800  # 30 minutes
    np = 300  # 120% of FTP
    ftp = 250
    
    tss = calculate_bike_tss(duration_s, np, ftp)
    
    # IF = 300/250 = 1.2
    # TSS = 0.5 × 1.2² × 100 = 72
    assert tss > 70
    assert tss < 75


def test_bike_tss_zero_ftp():
    """Test bike TSS with zero FTP"""
    tss = calculate_bike_tss(3600, 250, 0)
    assert tss == 0.0


def test_run_tss_basic():
    """Test run TSS calculation"""
    duration_min = 60  # 1 hour
    avg_pace = 5.0  # 5:00/km
    threshold_pace = 4.0  # 4:00/km
    
    tss = calculate_run_tss(duration_min, avg_pace, threshold_pace)
    
    # Pace ratio = 4/5 = 0.8 (slower than threshold)
    # Should give lower TSS
    assert tss > 0
    assert tss < 100  # Less than threshold pace


def test_run_tss_at_threshold():
    """Test run TSS at threshold pace"""
    duration_min = 60
    avg_pace = 4.0
    threshold_pace = 4.0
    
    tss = calculate_run_tss(duration_min, avg_pace, threshold_pace)
    
    # At threshold, should give moderate TSS
    assert tss > 0


def test_swim_tss_basic():
    """Test swim TSS calculation"""
    distance_m = 2000  # 2km
    duration_s = 2400  # 40 minutes
    css_pace = 90  # 1:30/100m
    
    tss = calculate_swim_tss(distance_m, duration_s, css_pace)
    
    assert tss > 0


def test_swim_tss_at_css():
    """Test swim TSS at CSS pace"""
    distance_m = 2000
    css_pace = 90  # 1:30/100m
    duration_s = 1800  # 30 minutes (exactly at CSS)
    
    tss = calculate_swim_tss(distance_m, duration_s, css_pace)
    
    assert tss > 0


def test_auto_calculate_bike():
    """Test auto TSS calculation for cycling"""
    activity = {
        "sport_type": "cycling",
        "duration_s": 3600,
        "normalized_power": 250,
    }
    profile = {"ftp": 250}
    
    tss = auto_calculate_tss(activity, profile)
    
    assert tss > 0
    assert abs(tss - 100.0) < 10.0  # Should be around 100 for 1h at FTP


def test_auto_calculate_run():
    """Test auto TSS calculation for running"""
    activity = {
        "sport_type": "running",
        "duration_s": 3600,
        "avg_pace_min_per_km": 5.0,
    }
    profile = {"threshold_pace": 4.0}
    
    tss = auto_calculate_tss(activity, profile)
    
    assert tss > 0


def test_auto_calculate_swim():
    """Test auto TSS calculation for swimming"""
    activity = {
        "sport_type": "swimming",
        "duration_s": 2400,
        "distance_m": 2000,
    }
    profile = {"css_pace_100m": 90}
    
    tss = auto_calculate_tss(activity, profile)
    
    assert tss > 0


def test_auto_calculate_fallback():
    """Test auto TSS fallback when profile missing"""
    activity = {
        "sport_type": "running",
        "duration_s": 3600,
    }
    profile = {}  # Missing threshold_pace
    
    tss = auto_calculate_tss(activity, profile)
    
    # Should use fallback calculation
    assert tss > 0


def test_auto_calculate_from_speed():
    """Test auto TSS calculation from speed (not pace)"""
    activity = {
        "sport_type": "running",
        "duration_s": 3600,
        "avg_speed_m_s": 3.33,  # ~5:00/km pace
    }
    profile = {"threshold_pace": 4.0}
    
    tss = auto_calculate_tss(activity, profile)
    
    assert tss > 0

