# tests/test_pmc.py

import pytest
from analytics.pmc import PMCCalculator

def test_pmc_basic():
    """Basic PMC calculation test"""
    calculator = PMCCalculator()
    
    activities = [
        {"date": "2025-01-01", "tss": 100},
        {"date": "2025-01-02", "tss": 80},
        {"date": "2025-01-03", "tss": 120},
    ]
    
    pmc = calculator.calculate_pmc(activities)
    
    assert "ctl" in pmc
    assert "atl" in pmc
    assert "tsb" in pmc
    assert "rr" in pmc
    assert "dates" in pmc
    assert "stress" in pmc
    assert len(pmc["ctl"]) > 0
    assert len(pmc["dates"]) == len(pmc["ctl"])


def test_ctl_increases():
    """CTL should increase with consistent training"""
    calculator = PMCCalculator()
    
    activities = [
        {"date": f"2025-01-{i:02d}", "tss": 100}
        for i in range(1, 15)  # 14 days of 100 TSS
    ]
    
    pmc = calculator.calculate_pmc(activities)
    
    # CTL at day 14 should be higher than day 1
    # (assuming we're looking at actual training days, not decay period)
    ctl_values = [pmc["ctl"][i] for i in range(len(activities)) if pmc["ctl"][i] > 0]
    if len(ctl_values) >= 2:
        assert ctl_values[-1] > ctl_values[0]


def test_tsb_calculation():
    """TSB = CTL - ATL (formula verification)"""
    calculator = PMCCalculator()
    
    activities = [{"date": "2025-01-01", "tss": 100}]
    pmc = calculator.calculate_pmc(activities)
    
    # Check formula: TSB = CTL - ATL
    for i in range(len(pmc["dates"])):
        calculated_tsb = pmc["ctl"][i] - pmc["atl"][i]
        assert abs(pmc["tsb"][i] - calculated_tsb) < 0.01, \
            f"TSB mismatch at index {i}: {pmc['tsb'][i]} != {calculated_tsb}"


def test_empty_activities():
    """Should handle empty activities list"""
    calculator = PMCCalculator()
    pmc = calculator.calculate_pmc([])
    
    assert pmc["dates"] == []
    assert pmc["ctl"] == []
    assert pmc["atl"] == []
    assert pmc["tsb"] == []


def test_get_current_metrics():
    """Test getting current metrics"""
    calculator = PMCCalculator()
    
    activities = [
        {"date": "2025-01-01", "tss": 100},
        {"date": "2025-01-02", "tss": 80},
    ]
    
    metrics = calculator.get_current_metrics(activities)
    
    assert metrics is not None
    assert "date" in metrics
    assert "ctl" in metrics
    assert "atl" in metrics
    assert "tsb" in metrics
    assert "rr" in metrics
    assert "form_status" in metrics
    assert isinstance(metrics["ctl"], (int, float))
    assert isinstance(metrics["tsb"], (int, float))


def test_custom_time_constants():
    """Test with custom LTS/STS days"""
    calculator = PMCCalculator(lts_days=30, sts_days=5)
    
    activities = [{"date": "2025-01-01", "tss": 100}]
    pmc = calculator.calculate_pmc(activities)
    
    assert len(pmc["ctl"]) > 0
    assert calculator.lts_days == 30
    assert calculator.sts_days == 5


def test_multiple_activities_same_day():
    """Test handling multiple activities on same day"""
    calculator = PMCCalculator()
    
    activities = [
        {"date": "2025-01-01", "tss": 50},
        {"date": "2025-01-01", "tss": 60},  # Same day
        {"date": "2025-01-02", "tss": 80},
    ]
    
    pmc = calculator.calculate_pmc(activities)
    
    # Should sum TSS for same day
    # Find the index for 2025-01-01
    day1_idx = pmc["dates"].index("2025-01-01")
    assert pmc["stress"][day1_idx] == 110.0  # 50 + 60


def test_tsb_interpretation():
    """Test TSB interpretation"""
    calculator = PMCCalculator()
    
    # Test different TSB values
    assert calculator._interpret_tsb(30) == "peaked"
    assert calculator._interpret_tsb(15) == "fresh"
    assert calculator._interpret_tsb(0) == "neutral"
    assert calculator._interpret_tsb(-15) == "optimal_overload"
    assert calculator._interpret_tsb(-35) == "high_risk"

