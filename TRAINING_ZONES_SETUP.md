# Training Zones Setup Guide

## Overview

Training zones are required for accurate TSS (Training Stress Score) calculation. Without proper zones, TSS will be 0 or inaccurate.

## Setting Training Zones

### Via API

```bash
PATCH /profile/training-zones

{
  "ftp": 250,                          # Cycling FTP (watts)
  "threshold_pace_min_per_km": 4.0,    # Running threshold pace (min/km)
  "css_pace_100m_seconds": 90,        # Swimming CSS (seconds/100m)
  "max_hr": 190,                       # Maximum heart rate (bpm)
  "rest_hr": 50                        # Resting heart rate (bpm)
}
```

### Via Frontend Component

Import and use the `TrainingZones` component:

```tsx
import { TrainingZones } from '@/components/settings/TrainingZones';

// In your settings page
<TrainingZones />
```

## Required Zones by Sport

### Cycling
- **FTP (Functional Threshold Power)**: Required for bike TSS
- **How to determine**: Run a 20-minute FTP test or use your best 1-hour power

### Running
- **Threshold Pace**: Required for run TSS
- **How to determine**: Your 1-hour race pace (e.g., 4:00/km for 4 min/km)
- **Format**: Minutes per kilometer (e.g., 4.0 for 4:00/km)

### Swimming
- **CSS (Critical Swim Speed)**: Required for swim TSS
- **How to determine**: Average pace from 400m and 200m time trials
- **Format**: Seconds per 100 meters (e.g., 90 for 1:30/100m)

## Storage

Training zones are stored in `AthleteProfileDB` as JSON fields:
- `training_zones_bike`: `{"ftp": 250, "max_hr": 190, "rest_hr": 50}`
- `training_zones_run`: `{"threshold_pace_min_per_km": 4.0, "max_hr": 190, "rest_hr": 50}`
- `training_zones_swim`: `{"css_pace_100m_seconds": 90, "max_hr": 190, "rest_hr": 50}`

## Checking Current Zones

```python
from database import SessionLocal
from models import AthleteProfileDB

db = SessionLocal()
profile = db.query(AthleteProfileDB).filter(
    AthleteProfileDB.user_id == user_id
).first()

if profile:
    print("Bike zones:", profile.training_zones_bike)
    print("Run zones:", profile.training_zones_run)
    print("Swim zones:", profile.training_zones_swim)

db.close()
```

## Troubleshooting

**Problem**: TSS is always 0

**Solutions**:
1. Check if training zones are set: `GET /profile`
2. Set zones via `PATCH /profile/training-zones`
3. Recalculate TSS: `python scripts/recalculate_tss.py`

**Problem**: Activities table doesn't exist

**Solution**: Run database migrations:
```bash
alembic upgrade head
```

Or create the table manually if using SQLite:
```bash
python -c "from database import init_db; init_db()"
```

