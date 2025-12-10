# TSS Calculation Guide

## Overview

TSS (Training Stress Score) is now automatically calculated when activities are imported from Strava.

## How It Works

1. **Automatic Calculation**: When a Strava activity is imported via `crud.upsert_activity()`, TSS is automatically calculated using the user's training zones.

2. **Training Zones Required**: TSS calculation requires:
   - **Cycling**: FTP (Functional Threshold Power) from `training_zones_bike.ftp`
   - **Running**: Threshold pace from `training_zones_run.threshold_pace` or `threshold_pace_min_per_km`
   - **Swimming**: CSS pace from `training_zones_swim.css_pace_100m` or `css_pace_100m_seconds`

3. **Fallback**: If training zones are not set, TSS will be calculated using a duration-based estimate.

## Recalculating TSS for Existing Activities

If you have existing activities without TSS, use the recalculation script:

```bash
# Recalculate TSS only for activities without TSS
python scripts/recalculate_tss.py

# Force recalculate TSS for ALL activities (overwrites existing)
python scripts/recalculate_tss.py --force
```

## Checking Activities

To check if activities have TSS:

```python
from database import SessionLocal
from models import ActivityDB

db = SessionLocal()

# Count activities with TSS
with_tss = db.query(ActivityDB).filter(ActivityDB.tss.isnot(None)).count()
print(f"Activities with TSS: {with_tss}")

# Count activities without TSS
without_tss = db.query(ActivityDB).filter(ActivityDB.tss.is_(None)).count()
print(f"Activities without TSS: {without_tss}")

# Get first activity with TSS
activity = db.query(ActivityDB).filter(ActivityDB.tss.isnot(None)).first()
if activity:
    print(f"Activity: {activity.sport_type}, TSS: {activity.tss}")

db.close()
```

## Setting Training Zones

Training zones are stored in `AthleteProfileDB`:

- **Bike zones**: `training_zones_bike` JSON field should contain `{"ftp": 250}`
- **Run zones**: `training_zones_run` JSON field should contain `{"threshold_pace": 4.0}` or `{"threshold_pace_min_per_km": 4.0}`
- **Swim zones**: `training_zones_swim` JSON field should contain `{"css_pace_100m": 90}` or `{"css_pace_100m_seconds": 90}`

You can set zones via:
- API endpoint: `POST /coach/zones/auto_from_history` (auto-calculates from activities)
- API endpoint: `POST /coach/zones/manual` (manual input)
- Dashboard: Training Zones section

## Troubleshooting

**Problem**: Activities have `tss = None`

**Solutions**:
1. Check if user has training zones set
2. Run recalculation script: `python scripts/recalculate_tss.py`
3. Verify activity has required data (duration, distance for swim/run, power for bike)

**Problem**: TSS is always 0

**Solutions**:
1. Check training zones are correctly set in profile
2. Verify activity has valid duration and distance/power
3. Check logs for TSS calculation errors

