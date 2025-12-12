"""
Unit tests for PMC calculations

"""
import pytest

from analytics.pmc import PMCCalculator


class TestPMCCalculator:
    """Test PMC calculations"""
    
    def test_empty_activities(self):
        """Empty activities list returns empty data"""
        calc = PMCCalculator()
        pmc = calc.calculate_pmc([])
        
        assert pmc["dates"] == []
        assert pmc["ctl"] == []
        assert pmc["atl"] == []
        assert pmc["tsb"] == []
        assert pmc["rr"] == []
    
    def test_single_activity(self):
        """Single activity calculates CTL/ATL"""
        calc = PMCCalculator()
        activities = [{"date": "2025-01-01", "tss": 100}]
        pmc = calc.calculate_pmc(activities)
        
        # First day CTL should be TSS × (1 - exp(-1/42))
        # ≈ 100 × 0.0236 ≈ 2.36
        assert 2.3 < pmc["ctl"][0] < 2.4
        
        # First day ATL should be TSS × (1 - exp(-1/7))
        # ≈ 100 × 0.133 ≈ 13.3
        assert 13.2 < pmc["atl"][0] < 13.4
    
    def test_ramp_rate_calculation(self):
        """Ramp Rate = (CTL_today - CTL_7days_ago) / 7"""
        calc = PMCCalculator()
        
        # 14 days of consistent training
        activities = [
            {"date": f"2025-01-{d:02d}", "tss": 100}
            for d in range(1, 15)
        ]
        pmc = calc.calculate_pmc(activities)
        
        # Check day 14 (index 13)
        day_14_idx = 13
        day_7_idx = 6
        
        # Manual calculation
        # RR is now in "per week" units (multiplied by 7)
        expected_rr_per_day = (pmc["ctl"][day_14_idx] - pmc["ctl"][day_7_idx]) / 7
        expected_rr_per_week = expected_rr_per_day * 7.0
        actual_rr = pmc["rr"][day_14_idx]
        
        assert abs(actual_rr - expected_rr_per_week) < 0.1, \
            f"RR mismatch: expected {expected_rr_per_week:.2f}, got {actual_rr:.2f}"
        
        # RR should be reasonable (0-70 range for per week)
        assert 0 <= actual_rr <= 70, \
            f"RR out of range: {actual_rr}"
    
    def test_ramp_rate_not_negative(self):
        """Ramp Rate should handle decreasing fitness"""
        calc = PMCCalculator()
        
        # 7 days training, then 7 days rest
        activities = [
            {"date": f"2025-01-{d:02d}", "tss": 100}
            for d in range(1, 8)
        ]
        # No activities from day 8-14
        
        pmc = calc.calculate_pmc(activities)
        
        # After rest, RR should be negative (CTL declining)
        # This is expected and valid
        day_14_idx = 13
        if len(pmc["rr"]) > day_14_idx:
            assert pmc["rr"][day_14_idx] < 0, "RR should be negative during rest"
    
    def test_tsb_calculation(self):
        """TSB = CTL - ATL"""
        calc = PMCCalculator()
        activities = [
            {"date": "2025-01-01", "tss": 100},
            {"date": "2025-01-02", "tss": 100}
        ]
        pmc = calc.calculate_pmc(activities)
        
        for i in range(len(pmc["dates"])):
            expected_tsb = pmc["ctl"][i] - pmc["atl"][i]
            actual_tsb = pmc["tsb"][i]
            assert abs(actual_tsb - expected_tsb) < 0.01, \
                f"TSB mismatch at index {i}"
    
    def test_tsb_interpretation(self):
        """Test TSB status categories"""
        calc = PMCCalculator()
        
        assert calc._interpret_tsb(30) == "peaked"
        assert calc._interpret_tsb(25.1) == "peaked"
        assert calc._interpret_tsb(15) == "fresh"
        assert calc._interpret_tsb(10.1) == "fresh"
        assert calc._interpret_tsb(0) == "neutral"
        assert calc._interpret_tsb(-5) == "neutral"
        assert calc._interpret_tsb(-20) == "optimal_overload"
        assert calc._interpret_tsb(-30) == "optimal_overload"
        assert calc._interpret_tsb(-40) == "high_risk"
        assert calc._interpret_tsb(-50) == "high_risk"
    
    def test_get_current_metrics(self):
        """Test getting current metrics"""
        calc = PMCCalculator()
        activities = [
            {"date": f"2025-01-{d:02d}", "tss": 100}
            for d in range(1, 8)
        ]
        
        metrics = calc.get_current_metrics(activities)
        
        assert metrics is not None
        assert "ctl" in metrics
        assert "atl" in metrics
        assert "tsb" in metrics
        assert "rr" in metrics
        assert "form_status" in metrics
        assert metrics["ctl"] > 0
        assert metrics["atl"] > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
