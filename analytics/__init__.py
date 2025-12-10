"""
Analytics Module
PMC (Performance Management Chart) and TSS calculations
Based on GoldenCheetah algorithms
"""

# New PMC and TSS functions
from analytics.pmc import PMCCalculator
from analytics.tss import (
    calculate_bike_tss,
    calculate_run_tss,
    calculate_swim_tss,
    auto_calculate_tss
)

# Legacy functions from old analytics.py (for backward compatibility)
# Import directly from the file to avoid name conflict
import importlib.util
import os

# Get parent directory (project root)
_current_dir = os.path.dirname(os.path.abspath(__file__))
_parent_dir = os.path.dirname(_current_dir)
_legacy_path = os.path.join(_parent_dir, 'analytics.py')

if os.path.exists(_legacy_path):
    spec = importlib.util.spec_from_file_location("_legacy_analytics", _legacy_path)
    _legacy_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(_legacy_module)
    
    # Re-export all legacy functions and classes
    TrainingMetrics = _legacy_module.TrainingMetrics
    calculate_tss_run = _legacy_module.calculate_tss_run
    calculate_tss_bike = _legacy_module.calculate_tss_bike
    calculate_tss_swim = _legacy_module.calculate_tss_swim
    estimate_intensity_from_activity = _legacy_module.estimate_intensity_from_activity
    calculate_tss_for_activity = _legacy_module.calculate_tss_for_activity
    calculate_training_metrics = _legacy_module.calculate_training_metrics
    calculate_ramp_rate = _legacy_module.calculate_ramp_rate
    get_form_interpretation = _legacy_module.get_form_interpretation
    analyze_training_load = _legacy_module.analyze_training_load
    get_ramp_rate_status = _legacy_module.get_ramp_rate_status
else:
    raise ImportError(f"Cannot find legacy analytics.py file at {_legacy_path}")

__all__ = [
    # New functions
    'PMCCalculator',
    'calculate_bike_tss',
    'calculate_run_tss',
    'calculate_swim_tss',
    'auto_calculate_tss',
    # Legacy functions
    'TrainingMetrics',
    'calculate_tss_run',
    'calculate_tss_bike',
    'calculate_tss_swim',
    'estimate_intensity_from_activity',
    'calculate_tss_for_activity',
    'calculate_training_metrics',
    'calculate_ramp_rate',
    'get_form_interpretation',
    'analyze_training_load',
    'get_ramp_rate_status',
]

