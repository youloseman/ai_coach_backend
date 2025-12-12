"""
Unit tests for TSS calculations

"""
import pytest

from analytics.tss import (
    calculate_run_tss,
    calculate_bike_tss,
    calculate_swim_tss,
    auto_calculate_tss
)


class TestRunTSS:
    """Test Run TSS calculations"""
    
    def test_threshold_pace(self):
        """1 hour at threshold pace = 100 TSS"""
        tss = calculate_run_tss(60, 4.0, 4.0)
        assert tss == 100.0, f"Expected 100.0, got {tss}"
    
    def test_easy_pace(self):
        """1 hour at easy pace (5:00/km vs 4:00/km threshold) = 64 TSS"""
        tss = calculate_run_tss(60, 5.0, 4.0)
        assert tss == 64.0, f"Expected 64.0, got {tss}"
    
    def test_fast_pace(self):
        """1 hour faster than threshold (3:30/km vs 4:00/km) ≈ 130 TSS"""
        tss = calculate_run_tss(60, 3.5, 4.0)
        assert 129 < tss < 132, f"Expected ~130, got {tss}"
    
    def test_30min_threshold(self):
        """30 minutes at threshold = 50 TSS"""
        tss = calculate_run_tss(30, 4.0, 4.0)
        assert tss == 50.0, f"Expected 50.0, got {tss}"
    
    def test_zero_pace(self):
        """Zero pace = 0 TSS"""
        tss = calculate_run_tss(60, 0, 4.0)
        assert tss == 0.0
    
    def test_negative_duration(self):
        """Negative duration = 0 TSS"""
        tss = calculate_run_tss(-60, 4.0, 4.0)
        assert tss == 0.0


class TestBikeTSS:
    """Test Bike TSS calculations"""
    
    def test_at_ftp(self):
        """1 hour at FTP = 100 TSS"""
        tss = calculate_bike_tss(3600, 250, 250)
        assert tss == 100.0, f"Expected 100.0, got {tss}"
    
    def test_85_percent_ftp(self):
        """1 hour at 85% FTP ≈ 72 TSS"""
        tss = calculate_bike_tss(3600, 212.5, 250)
        assert 71 < tss < 73, f"Expected ~72, got {tss}"
    
    def test_30min_at_ftp(self):
        """30 minutes at FTP = 50 TSS"""
        tss = calculate_bike_tss(1800, 250, 250)
        assert tss == 50.0, f"Expected 50.0, got {tss}"
    
    def test_zero_ftp(self):
        """Zero FTP = 0 TSS"""
        tss = calculate_bike_tss(3600, 250, 0)
        assert tss == 0.0


class TestSwimTSS:
    """Test Swim TSS calculations"""
    
    def test_at_css_pace(self):
        """30min at CSS pace = 50 TSS (0.5 hour × 1.0² × 100)"""
        # CSS = 90s/100m, distance = 2000m, time = 1800s (30 min)
        # avg pace = 1800/2000 * 100 = 90s/100m = CSS pace
        # IF = 90/90 = 1.0, duration = 0.5h, TSS = 0.5 × 1.0² × 100 = 50.0
        tss = calculate_swim_tss(2000, 1800, 90)
        assert tss == 50.0, f"Expected 50.0, got {tss}"
    
    def test_slower_than_css(self):
        """2km slower than CSS ≈ 45 TSS"""
        # Same distance but 2000s (slower)
        # avg pace = 2000/2000 * 100 = 100s/100m, CSS = 90s/100m
        # IF = 90/100 = 0.9, duration = 2000/3600 = 0.556h
        # TSS = 0.556 × 0.9² × 100 = 45.0
        tss = calculate_swim_tss(2000, 2000, 90)
        assert tss == 45.0, f"Expected 45.0, got {tss}"
    
    def test_zero_distance(self):
        """Zero distance = 0 TSS"""
        tss = calculate_swim_tss(0, 1800, 90)
        assert tss == 0.0


class TestAutoCalculateTSS:
    """Test auto_calculate_tss function"""
    
    def test_run_with_pace(self):
        """Auto calculate for run with pace data"""
        activity = {
            "sport_type": "run",
            "duration_s": 3600,
            "avg_pace_min_per_km": 5.0
        }
        profile = {
            "threshold_pace": 4.0
        }
        tss = auto_calculate_tss(activity, profile)
        assert tss == 64.0
    
    def test_bike_with_power(self):
        """Auto calculate for bike with power"""
        activity = {
            "sport_type": "ride",
            "duration_s": 3600,
            "normalized_power": 250
        }
        profile = {
            "ftp": 250
        }
        tss = auto_calculate_tss(activity, profile)
        assert tss == 100.0
    
    def test_no_data_fallback(self):
        """Fallback to duration-based when no data"""
        activity = {
            "sport_type": "workout",
            "duration_s": 3600
        }
        profile = {}
        tss = auto_calculate_tss(activity, profile)
        # 1 hour × 50 TSS/hour fallback
        assert tss == 50.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
