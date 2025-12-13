# 🚀 ACTION PLAN: Next 4 Weeks
## Пошаговый план внедрения аналитики из Open Source проектов

**Start Date:** Сегодня  
**Target MVP:** 4 недели  
**Daily Time:** 4-6 hours

---

## 📅 WEEK 1: CORE ANALYTICS (5-7 дней)

### Day 1: PMC Calculator Backend ⏱️ 6-8 часов

**Goal:** Реализовать формулы CTL/ATL/TSB из GoldenCheetah

**Step 1: Создай файл аналитики**

```bash
# Backend
cd backend/app
mkdir -p analytics
touch analytics/__init__.py
touch analytics/pmc.py
```

**Step 2: Скопируй PMCCalculator class**

```python
# backend/app/analytics/pmc.py

import math
from datetime import datetime, timedelta
from typing import List, Dict

class PMCCalculator:
    """
    Performance Management Chart Calculator
    Based on GoldenCheetah PMCData.cpp
    """
    
    def __init__(self, lts_days: int = 42, sts_days: int = 7):
        """
        Args:
            lts_days: Long Term Stress период (default: 42)
            sts_days: Short Term Stress период (default: 7)
        """
        self.lts_days = lts_days
        self.sts_days = sts_days
        
        # Exponential decay constants
        self.lte = math.exp(-1.0 / lts_days)  # ~0.9764
        self.ste = math.exp(-1.0 / sts_days)  # ~0.8670
    
    def calculate_pmc(self, activities: List[Dict]) -> Dict:
        """
        Calculate PMC from activities
        
        Args:
            activities: [
                {"date": "2025-01-01", "tss": 100},
                ...
            ]
        
        Returns:
            {
                "dates": [...],
                "stress": [...],
                "ctl": [...],
                "atl": [...],
                "tsb": [...],
                "rr": [...]
            }
        """
        if not activities:
            return {}
        
        # Sort by date
        activities = sorted(activities, key=lambda x: x["date"])
        
        # Date range
        start_date = datetime.strptime(activities[0]["date"], "%Y-%m-%d")
        end_date = datetime.strptime(activities[-1]["date"], "%Y-%m-%d")
        
        # Extend 365 days for decay
        end_date += timedelta(days=365)
        
        # Create arrays
        days = (end_date - start_date).days + 1
        dates = [(start_date + timedelta(days=i)).strftime("%Y-%m-%d") 
                 for i in range(days)]
        
        stress = [0.0] * days
        ctl = [0.0] * days
        atl = [0.0] * days
        tsb = [0.0] * days
        rr = [0.0] * days
        
        # Fill stress array
        for activity in activities:
            act_date = datetime.strptime(activity["date"], "%Y-%m-%d")
            offset = (act_date - start_date).days
            if 0 <= offset < days:
                stress[offset] += activity.get("tss", 0)
        
        # Calculate CTL and ATL
        for day in range(days):
            last_ctl = ctl[day - 1] if day > 0 else 0.0
            last_atl = atl[day - 1] if day > 0 else 0.0
            
            # CTL (Fitness) - строка 341 из PMCData.cpp
            ctl[day] = (stress[day] * (1.0 - self.lte)) + (last_ctl * self.lte)
            
            # ATL (Fatigue) - строка 345 из PMCData.cpp
            atl[day] = (stress[day] * (1.0 - self.ste)) + (last_atl * self.ste)
            
            # TSB (Form) - строка 367 из PMCData.cpp
            tsb[day] = ctl[day] - atl[day]
            
            # Ramp Rate - строки 354-362 из PMCData.cpp
            if day > 0 and day <= self.sts_days:
                rr[day] = sum(ctl[i] - ctl[i-1] for i in range(1, day + 1))
            elif day > self.sts_days:
                rr[day] = sum(ctl[i] - ctl[i-1] 
                             for i in range(day - self.sts_days, day + 1))
        
        return {
            "dates": dates,
            "stress": stress,
            "ctl": ctl,
            "atl": atl,
            "tsb": tsb,
            "rr": rr
        }
```

**Step 3: Создай тесты**

```bash
touch tests/test_pmc.py
```

```python
# tests/test_pmc.py

import pytest
from app.analytics.pmc import PMCCalculator

def test_pmc_basic():
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
    assert len(pmc["ctl"]) > 0

def test_ctl_increases():
    """CTL should increase with consistent training"""
    calculator = PMCCalculator()
    
    activities = [
        {"date": f"2025-01-{i:02d}", "tss": 100}
        for i in range(1, 15)  # 14 days of 100 TSS
    ]
    
    pmc = calculator.calculate_pmc(activities)
    
    # CTL at day 14 should be higher than day 1
    assert pmc["ctl"][13] > pmc["ctl"][0]

def test_tsb_calculation():
    """TSB = CTL - ATL"""
    calculator = PMCCalculator()
    
    activities = [{"date": "2025-01-01", "tss": 100}]
    pmc = calculator.calculate_pmc(activities)
    
    # Check formula
    for i in range(len(pmc["dates"])):
        assert abs(pmc["tsb"][i] - (pmc["ctl"][i] - pmc["atl"][i])) < 0.01
```

**Step 4: Запусти тесты**

```bash
pytest tests/test_pmc.py -v
```

**✅ Success Criteria:**
- Все тесты проходят
- PMC calculator работает
- Формулы совпадают с GoldenCheetah

---

### Day 2: TSS Calculation ⏱️ 6 часов

**Goal:** Добавить TSS calculation для 3 видов спорта

**Step 1: Создай tss.py**

```python
# backend/app/analytics/tss.py

import math

def calculate_bike_tss(duration_seconds: float, 
                      normalized_power: float, 
                      ftp: float) -> float:
    """
    Calculate Bike TSS (Training Stress Score)
    Based on GoldenCheetah BasicRideMetrics.cpp
    
    Args:
        duration_seconds: Total ride time
        normalized_power: NP for the ride
        ftp: Functional Threshold Power
    
    Returns:
        TSS score
    """
    if ftp <= 0:
        return 0.0
    
    duration_hours = duration_seconds / 3600.0
    intensity_factor = normalized_power / ftp
    
    # TSS = (duration × NP × IF) / (FTP × 3600) × 100
    tss = (duration_hours * normalized_power * intensity_factor) / (ftp * 3600) * 100
    
    return round(tss, 1)


def calculate_run_tss(duration_minutes: float,
                     avg_pace_min_per_km: float,
                     threshold_pace_min_per_km: float) -> float:
    """
    Calculate Run TSS
    Based on pace ratio to threshold
    
    Args:
        duration_minutes: Total run time
        avg_pace_min_per_km: Average pace (e.g. 5.0 for 5:00/km)
        threshold_pace_min_per_km: Threshold pace (e.g. 4.0 for 4:00/km)
    
    Returns:
        TSS score
    """
    if avg_pace_min_per_km <= 0 or threshold_pace_min_per_km <= 0:
        return 0.0
    
    # Pace ratio (slower pace = lower ratio)
    pace_ratio = threshold_pace_min_per_km / avg_pace_min_per_km
    
    # TSS calculation based on intensity
    if pace_ratio < 0.85:  # Very easy
        tss = duration_minutes * 0.5
    elif pace_ratio > 1.05:  # Faster than threshold
        tss = duration_minutes * (pace_ratio ** 3)
    else:  # Around threshold
        tss = duration_minutes * (pace_ratio ** 2)
    
    return round(tss, 1)


def calculate_swim_tss(distance_meters: float,
                      duration_seconds: float,
                      css_pace_100m_seconds: float) -> float:
    """
    Calculate Swim TSS
    Based on CSS (Critical Swim Speed)
    
    Args:
        distance_meters: Total distance
        duration_seconds: Total time
        css_pace_100m_seconds: CSS pace per 100m (e.g. 90 for 1:30/100m)
    
    Returns:
        TSS score
    """
    if distance_meters <= 0 or css_pace_100m_seconds <= 0:
        return 0.0
    
    # Calculate average pace per 100m
    avg_pace_100m = (duration_seconds / 60.0) / (distance_meters / 100.0)
    
    # Pace ratio (faster = higher)
    pace_ratio = css_pace_100m / avg_pace_100m
    
    duration_minutes = duration_seconds / 60.0
    
    # Similar to run TSS
    if pace_ratio < 0.85:
        tss = duration_minutes * 0.5
    elif pace_ratio > 1.05:
        tss = duration_minutes * (pace_ratio ** 3)
    else:
        tss = duration_minutes * (pace_ratio ** 2)
    
    return round(tss, 1)


def auto_calculate_tss(activity_data: dict, user_profile: dict) -> float:
    """
    Auto-calculate TSS based on sport type and available data
    
    Args:
        activity_data: {
            "sport_type": "running",
            "duration_s": 3600,
            "distance_m": 10000,
            "avg_power": 200,  # optional
            "avg_pace_min_per_km": 5.0,  # optional
        }
        user_profile: {
            "ftp": 250,
            "threshold_pace": 4.0,
            "css_pace_100m": 90
        }
    
    Returns:
        TSS score or 0 if can't calculate
    """
    sport = activity_data.get("sport_type", "").lower()
    
    if sport == "cycling":
        if "avg_power" in activity_data and "ftp" in user_profile:
            return calculate_bike_tss(
                activity_data["duration_s"],
                activity_data["avg_power"],
                user_profile["ftp"]
            )
    
    elif sport == "running":
        if "avg_pace_min_per_km" in activity_data and "threshold_pace" in user_profile:
            duration_min = activity_data["duration_s"] / 60.0
            return calculate_run_tss(
                duration_min,
                activity_data["avg_pace_min_per_km"],
                user_profile["threshold_pace"]
            )
    
    elif sport == "swimming":
        if "distance_m" in activity_data and "css_pace_100m" in user_profile:
            return calculate_swim_tss(
                activity_data["distance_m"],
                activity_data["duration_s"],
                user_profile["css_pace_100m"]
            )
    
    return 0.0
```

**Step 2: Обнови Activity model**

```python
# backend/app/models/activity.py

from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey
from app.db.base_class import Base

class Activity(Base):
    __tablename__ = "activities"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    
    # Basic info
    sport_type = Column(String(50))  # running, cycling, swimming
    start_time = Column(DateTime(timezone=True))
    duration_s = Column(Integer)
    distance_m = Column(Float)
    
    # Sensor data
    avg_hr = Column(Float)
    avg_power = Column(Float)
    avg_pace_min_per_km = Column(Float)
    
    # Calculated metrics (NEW!)
    tss = Column(Float)  # Training Stress Score
    trimp = Column(Float)  # Training Impulse
    
    # External IDs
    strava_id = Column(String(50), unique=True)
```

**Step 3: Миграция**

```bash
cd backend
alembic revision --autogenerate -m "Add TSS and TRIMP columns"
alembic upgrade head
```

**✅ Success Criteria:**
- TSS функции работают
- Activity model обновлена
- Миграция применена

---

### Day 3: API Endpoints ⏱️ 4 часа

**Goal:** Создать FastAPI endpoints для аналитики

**Step 1: Создай api_analytics.py**

```python
# backend/app/api/api_analytics.py

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional

from app.db.session import get_db
from app.models.user import User
from app.models.activity import Activity
from app.analytics.pmc import PMCCalculator
from app.api.deps import get_current_user

router = APIRouter()

@router.get("/analytics/pmc")
async def get_pmc_data(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    lts_days: int = Query(42, ge=7, le=84),
    sts_days: int = Query(7, ge=3, le=21),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get Performance Management Chart data
    
    Returns CTL/ATL/TSB/RR arrays
    """
    # Parse dates
    if not end_date:
        end_dt = datetime.now()
    else:
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
    
    if not start_date:
        start_dt = end_dt - timedelta(days=90)
    else:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    
    # Fetch activities
    activities = db.query(Activity).filter(
        Activity.user_id == current_user.id,
        Activity.start_time >= start_dt,
        Activity.start_time <= end_dt,
        Activity.tss.isnot(None)
    ).all()
    
    # Prepare data
    activity_data = [
        {
            "date": act.start_time.strftime("%Y-%m-%d"),
            "tss": act.tss
        }
        for act in activities
    ]
    
    # Calculate PMC
    calculator = PMCCalculator(lts_days=lts_days, sts_days=sts_days)
    pmc_data = calculator.calculate_pmc(activity_data)
    
    return pmc_data


@router.get("/analytics/summary")
async def get_analytics_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get current fitness summary
    
    Returns:
    {
        "ctl": 85.3,
        "atl": 72.1,
        "tsb": 13.2,
        "rr": 5.2,
        "status": "optimal",
        "message": "Ready to race!"
    }
    """
    # Get last 90 days
    end_date = datetime.now()
    start_date = end_date - timedelta(days=90)
    
    activities = db.query(Activity).filter(
        Activity.user_id == current_user.id,
        Activity.start_time >= start_date,
        Activity.tss.isnot(None)
    ).all()
    
    if not activities:
        return {
            "ctl": 0.0,
            "atl": 0.0,
            "tsb": 0.0,
            "rr": 0.0,
            "status": "no_data",
            "message": "No training data yet. Connect Strava to get started!"
        }
    
    activity_data = [
        {
            "date": act.start_time.strftime("%Y-%m-%d"),
            "tss": act.tss
        }
        for act in activities
    ]
    
    calculator = PMCCalculator()
    pmc = calculator.calculate_pmc(activity_data)
    
    # Get latest values
    latest = {
        "ctl": round(pmc["ctl"][-1], 1),
        "atl": round(pmc["atl"][-1], 1),
        "tsb": round(pmc["tsb"][-1], 1),
        "rr": round(pmc["rr"][-1], 1)
    }
    
    # Determine status
    tsb = latest["tsb"]
    rr = latest["rr"]
    
    if tsb < -30:
        status = "overtrained"
        message = "⚠️ High fatigue! Consider rest days."
    elif -5 <= tsb <= 5:
        status = "optimal"
        message = "✅ Optimal training zone. Keep it up!"
    elif 5 < tsb < 15:
        status = "race_ready"
        message = "🎯 You're race ready!"
    elif tsb > 15:
        status = "detraining"
        message = "⚠️ Fitness declining. Increase load."
    else:
        status = "fresh"
        message = "💪 Fresh and ready for hard training!"
    
    if rr > 8:
        message += " ⚠️ Warning: Ramp rate too high!"
    
    return {
        **latest,
        "status": status,
        "message": message
    }
```

**Step 2: Регистрируй router в main.py**

```python
# backend/app/main.py

from app.api import api_analytics

app.include_router(api_analytics.router, prefix="/api", tags=["analytics"])
```

**Step 3: Тест в Swagger**

```bash
# Запусти сервер
uvicorn app.main:app --reload

# Открой браузер
http://localhost:8000/docs

# Попробуй endpoints:
# GET /api/analytics/pmc
# GET /api/analytics/summary
```

**✅ Success Criteria:**
- Endpoints работают в Swagger
- Возвращают корректные данные
- Обрабатывают ошибки

---

### Days 4-5: Frontend PMC Chart ⏱️ 8-10 часов

**Goal:** Создать красивый PMC chart с Recharts

**Step 1: Setup API client**

```typescript
// frontend/lib/api.ts

export const analyticsAPI = {
  async getPMC(params?: {
    startDate?: string;
    endDate?: string;
    ltsDays?: number;
    stsDays?: number;
  }) {
    const query = new URLSearchParams(params as any).toString();
    const response = await fetch(`/api/analytics/pmc?${query}`, {
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('token')}`
      }
    });
    return response.json();
  },

  async getSummary() {
    const response = await fetch('/api/analytics/summary', {
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('token')}`
      }
    });
    return response.json();
  }
};
```

**Step 2: PMC Chart Component**

```typescript
// frontend/components/charts/PMCChart.tsx

import React, { useEffect, useState } from 'react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer, ReferenceLine
} from 'recharts';
import { analyticsAPI } from '@/lib/api';

interface PMCData {
  dates: string[];
  ctl: number[];
  atl: number[];
  tsb: number[];
}

export const PMCChart: React.FC = () => {
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const pmc: PMCData = await analyticsAPI.getPMC();
      
      // Transform for Recharts
      const chartData = pmc.dates.map((date, i) => ({
        date: new Date(date).toLocaleDateString('en-US', {
          month: 'short',
          day: 'numeric'
        }),
        fullDate: date,
        CTL: Math.round(pmc.ctl[i]),
        ATL: Math.round(pmc.atl[i]),
        TSB: Math.round(pmc.tsb[i])
      }));
      
      setData(chartData);
    } catch (error) {
      console.error('Failed to fetch PMC:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-gray-500">Loading PMC Chart...</div>
      </div>
    );
  }

  return (
    <div className="w-full">
      <h2 className="text-2xl font-bold mb-4">Performance Management Chart</h2>
      <div className="h-96 bg-white rounded-lg p-4 shadow-sm">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            
            <XAxis
              dataKey="date"
              tick={{ fontSize: 12 }}
              stroke="#6b7280"
            />
            
            <YAxis stroke="#6b7280" />
            
            <Tooltip
              contentStyle={{
                backgroundColor: '#1f2937',
                border: '1px solid #374151',
                borderRadius: '8px',
                color: '#f9fafb'
              }}
              labelStyle={{ color: '#9ca3af' }}
            />
            
            <Legend
              wrapperStyle={{ paddingTop: '20px' }}
            />
            
            {/* TSB Reference Lines */}
            <ReferenceLine
              y={-30}
              stroke="#ef4444"
              strokeDasharray="3 3"
              label={{ value: 'Overtraining Risk', position: 'right', fill: '#ef4444' }}
            />
            <ReferenceLine
              y={-5}
              stroke="#10b981"
              strokeDasharray="3 3"
            />
            <ReferenceLine
              y={15}
              stroke="#f59e0b"
              strokeDasharray="3 3"
              label={{ value: 'Detraining Risk', position: 'right', fill: '#f59e0b' }}
            />
            
            {/* Lines */}
            <Line
              type="monotone"
              dataKey="CTL"
              stroke="#3b82f6"
              strokeWidth={2}
              dot={false}
              name="CTL (Fitness)"
            />
            <Line
              type="monotone"
              dataKey="ATL"
              stroke="#ef4444"
              strokeWidth={2}
              dot={false}
              name="ATL (Fatigue)"
            />
            <Line
              type="monotone"
              dataKey="TSB"
              stroke="#10b981"
              strokeWidth={2}
              dot={false}
              name="TSB (Form)"
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};
```

**Step 3: Fitness Summary Card**

```typescript
// frontend/components/analytics/FitnessSummary.tsx

import React, { useEffect, useState } from 'react';
import { analyticsAPI } from '@/lib/api';

interface Summary {
  ctl: number;
  atl: number;
  tsb: number;
  rr: number;
  status: string;
  message: string;
}

export const FitnessSummary: React.FC = () => {
  const [summary, setSummary] = useState<Summary | null>(null);

  useEffect(() => {
    fetchSummary();
  }, []);

  const fetchSummary = async () => {
    const data = await analyticsAPI.getSummary();
    setSummary(data);
  };

  if (!summary) return null;

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'optimal': return 'bg-green-500';
      case 'race_ready': return 'bg-blue-500';
      case 'overtrained': return 'bg-red-500';
      case 'detraining': return 'bg-yellow-500';
      default: return 'bg-gray-500';
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-sm p-6">
      <h3 className="text-lg font-semibold mb-4">Current Fitness</h3>
      
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
        <div>
          <div className="text-sm text-gray-500">CTL (Fitness)</div>
          <div className="text-2xl font-bold text-blue-600">{summary.ctl}</div>
        </div>
        <div>
          <div className="text-sm text-gray-500">ATL (Fatigue)</div>
          <div className="text-2xl font-bold text-red-600">{summary.atl}</div>
        </div>
        <div>
          <div className="text-sm text-gray-500">TSB (Form)</div>
          <div className="text-2xl font-bold text-green-600">{summary.tsb}</div>
        </div>
        <div>
          <div className="text-sm text-gray-500">Ramp Rate</div>
          <div className="text-2xl font-bold">{summary.rr}</div>
        </div>
      </div>
      
      <div className={`${getStatusColor(summary.status)} text-white px-4 py-3 rounded-lg`}>
        {summary.message}
      </div>
    </div>
  );
};
```

**Step 4: Dashboard Page**

```typescript
// frontend/pages/dashboard.tsx

import React from 'react';
import { PMCChart } from '@/components/charts/PMCChart';
import { FitnessSummary } from '@/components/analytics/FitnessSummary';

export default function Dashboard() {
  return (
    <div className="container mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold mb-8">Dashboard</h1>
      
      <div className="space-y-6">
        <FitnessSummary />
        <PMCChart />
      </div>
    </div>
  );
}
```

**✅ Success Criteria:**
- PMC chart отображается
- Данные обновляются
- Reference lines видны
- Responsive design

---

## 📅 WEEK 2-4: STRAVA, UI, AI

*(Сокращённо - детали в COMPREHENSIVE-ANALYSIS.md)*

### Week 2: Strava Integration
- OAuth flow
- Activity import
- Webhook subscription
- Auto-calculate TSS

### Week 3: UI Polish
- Training calendar
- Activity cards
- Settings page
- Responsive mobile

### Week 4: AI Integration
- Daily suggestions
- Training plan generation
- Form analysis

---

## 🎯 DAILY WORKFLOW

### Morning (2 hours):
1. Review previous day's work
2. Plan today's tasks
3. Start coding

### Afternoon (2 hours):
1. Continue coding
2. Write tests
3. Deploy to Railway (if needed)

### Evening (2 hours):
1. Test features
2. Fix bugs
3. Commit & push
4. Update progress

---

## ✅ PROGRESS TRACKING

**Week 1 Checklist:**

- [ ] Day 1: PMCCalculator working ✅
- [ ] Day 2: TSS calculation done ✅
- [ ] Day 3: API endpoints ready ✅
- [ ] Day 4-5: Frontend chart done ✅
- [ ] Day 6: Testing & fixes
- [ ] Day 7: Buffer / documentation

**After Week 1, you should have:**
✅ Working PMC analytics  
✅ TSS auto-calculation  
✅ Beautiful PMC chart  
✅ Fitness summary card  

**Then you're ready for Week 2: Strava! 🚀**

---

## 🔧 DEBUGGING CHECKLIST

### If PMC not working:
- [ ] Check activity dates are correct format
- [ ] Verify TSS values are not null
- [ ] Console log PMC calculation output
- [ ] Test with sample data first

### If Chart not displaying:
- [ ] Check API returns data (Network tab)
- [ ] Verify data transformation
- [ ] Check Recharts installed: `npm list recharts`
- [ ] Look for console errors

### If Calculations wrong:
- [ ] Compare with GoldenCheetah formulas
- [ ] Test with known examples
- [ ] Check decay constants (lte, ste)
- [ ] Verify date arithmetic

---

## 📱 COMMUNICATION

### Daily standup (with yourself):
- What did I complete yesterday?
- What am I working on today?
- Any blockers?

### Weekly review:
- What features are done?
- What's left for MVP?
- Any architecture changes needed?

---

**START TODAY! 🚀**

```bash
# First commands to run:
cd backend/app
mkdir analytics
touch analytics/__init__.py
code analytics/pmc.py  # Paste PMCCalculator class

# Then test it:
pytest tests/test_pmc.py -v
```

**You got this! 💪**
