# Frontend Implementation Status

## ✅ Уже реализовано

### Страницы
- ✅ `/` - Home/Router page
- ✅ `/login` - Login page
- ✅ `/register` - Register page
- ✅ `/onboarding` - Onboarding flow
- ✅ `/dashboard` - Main dashboard
- ✅ `/goals` - Goals management
- ✅ `/coach` - Coach profile

### API Integration (lib/api.ts)
- ✅ Auth API (`authAPI`):
  - register, login, getCurrentUser
- ✅ Profile API (`profileAPI`):
  - get, update
- ✅ Goals API (`goalsAPI`):
  - list, create, getPrimary
- ✅ Coach API (`coachAPI`):
  - generateWeeklyPlan
  - exportWeeklyPlanToCalendar
  - sendMultiWeekPlanEmail
  - sendWeeklyReportEmail
  - getZones
  - autoCalculateZonesFromActivities
  - calculateZonesManual
  - getProfile
  - updateProfile
  - autoUpdateProfileFromHistory
- ✅ Strava API (`stravaAPI`):
  - getStatus

### Components
- ✅ ErrorAlert
- ✅ Header
- ✅ PageHeader
- ✅ PerformanceChart (CTL/ATL/TSB timeline)
- ✅ StatsCard

### Dashboard Features
- ✅ Performance Management Chart (90 days CTL/ATL/TSB)
- ✅ Top stats cards (Avg Hours, Available Hours, Primary Race, Days to Race)
- ✅ Primary Goal card
- ✅ Quick Actions:
  - Generate weekly plan
  - Export to calendar (.ics)
  - Send 12-week plan to email
  - Send weekly report email
- ✅ All goals overview
- ✅ Training zones (auto-calc from Strava + manual input)
- ✅ Training zones display (Run/Bike/Swim zones with details)

---

## ❌ НЕ реализовано (Backend готов, Frontend нет)

### 1. Analytics API (main.py)
Backend endpoints готовы, НЕ подключены к frontend:

```
GET /analytics/training_load
  - Current CTL/ATL/TSB
  - Ramp rate
  - Load analysis
  
GET /analytics/form_status
  - Current form interpretation (Fresh/Fatigued/Optimal)
  - Recommendations
  
GET /analytics/fatigue
  - HR drift detection
  - Chronic high HR
  - Pace decline
  - Days since rest
  - Fatigue score & recommendations
  
GET /analytics/predict_race
  - Race time prediction
  - Probability of success
  - Pace recommendations
  
GET /analytics/all_predictions
  - Predictions for all distances (5K, 10K, HM, Marathon)
  - Best efforts
  - Form-adjusted predictions
```

### 2. Strava Activities (main.py)
```
GET /strava/activities
  - List activities with pagination
  - NOT shown on dashboard
```

### 3. Nutrition API (api_nutrition.py)
Backend готов, Frontend СОВСЕМ НЕТ:

```
POST /nutrition/targets/calculate
  - Calculate daily nutrition targets
  
GET /nutrition/targets
  - Get saved nutrition targets
  
POST /nutrition/race-fueling
  - Generate race day fueling plan
  
GET /nutrition/race-fueling/{race_type}
  - Get saved fueling plan
  
GET /nutrition/race-fueling
  - List all fueling plans
```

### 4. Segments API (api_segments.py)
Backend готов, Frontend СОВСЕМ НЕТ:

```
GET /segments
  - List user segments
  
GET /segment-efforts
  - List segment efforts with filters
  
GET /segment-prs
  - Personal records on segments
  
GET /personal-records
  - All personal records
  
GET /personal-records/{sport_type}/{distance_category}
  - Specific PRs
  
GET /injury-risks
  - Active injury risk warnings
  
POST /injury-risks/{risk_id}/acknowledge
POST /injury-risks/{risk_id}/resolve
  
GET /performance-summary
  - Overall performance metrics
  
POST /sync-segments
  - Sync segment data from Strava
  
POST /scan-prs
  - Scan for new personal records
  
POST /analyze-injury-risk
  - Analyze injury risks
```

### 5. Settings Page
СОВСЕМ НЕТ (критично для плана):

Должна включать:
- Profile editing (age, gender, weight, height)
- Training preferences
- Training zones management
- Goals management
- Strava connection status
- Email preferences
- Account settings

### 6. Recent Activities на Dashboard
Backend готов (`/strava/activities`), но:
- НЕ отображаются на dashboard
- Нет компонента ActivityCard/ActivityList

---

## 📋 План реализации (по приоритетам)

### Priority 1: Доработка Dashboard (2 дня)

#### Day 1: Recent Activities
```typescript
// 1. Add to lib/api.ts
export const stravaAPI = {
  getActivities: async (page = 1, perPage = 10) => {
    const response = await api.get('/strava/activities', {
      params: { page, per_page: perPage }
    });
    return response.data;
  },
  // ... existing getStatus
};

// 2. Create component: components/ActivityCard.tsx
// 3. Add to dashboard: Recent Activities section
```

#### Day 2: Analytics Enhancement
```typescript
// 1. Add to lib/api.ts
export const analyticsAPI = {
  getTrainingLoad: async () => {...},
  getFormStatus: async () => {...},
  getFatigueAnalysis: async () => {...},
  predictRace: async (goalType, goalTime) => {...},
  getAllPredictions: async () => {...},
};

// 2. Add to dashboard:
//    - Current Form card
//    - Fatigue warning banner
//    - Race predictions section
```

### Priority 2: Settings Page (1 день)

```bash
frontend/app/settings/page.tsx
  - Profile section
  - Training zones
  - Goals quick access
  - Strava connection
  - Preferences
```

### Priority 3: Nutrition Section (1 день)

```bash
frontend/app/nutrition/page.tsx
  - Daily targets calculator
  - Race fueling planner
  - Saved plans list
```

### Priority 4: Performance & Segments (1 день)

```bash
frontend/app/performance/page.tsx
  - Segments list
  - Personal records
  - Injury risk warnings
  - Performance summary
```

---

## 🎯 Immediate Next Steps

### Step 1: Add Analytics API to frontend
```typescript
// frontend/lib/api.ts - add:
export const analyticsAPI = {
  getTrainingLoad: async (weeks = 12) => {
    const response = await api.get('/analytics/training_load', { params: { weeks } });
    return response.data;
  },
  
  getFormStatus: async () => {
    const response = await api.get('/analytics/form_status');
    return response.data;
  },
  
  getFatigueAnalysis: async (weeks = 4) => {
    const response = await api.get('/analytics/fatigue', { params: { weeks } });
    return response.data;
  },
  
  predictRace: async (goalRaceType: string, goalTime: string, sport = 'run', weeks = 12) => {
    const response = await api.get('/analytics/predict_race', {
      params: { goal_race_type: goalRaceType, goal_time: goalTime, sport, weeks }
    });
    return response.data;
  },
  
  getAllPredictions: async (sport = 'run', weeks = 12) => {
    const response = await api.get('/analytics/all_predictions', {
      params: { sport, weeks }
    });
    return response.data;
  },
};
```

### Step 2: Add Nutrition API
```typescript
// frontend/lib/api.ts - add:
export const nutritionAPI = {
  calculateTargets: async (payload) => {
    const response = await api.post('/nutrition/targets/calculate', payload);
    return response.data;
  },
  
  getTargets: async () => {
    const response = await api.get('/nutrition/targets');
    return response.data;
  },
  
  generateRaceFueling: async (payload) => {
    const response = await api.post('/nutrition/race-fueling', payload);
    return response.data;
  },
  
  getRaceFueling: async (raceType?: string) => {
    const url = raceType ? `/nutrition/race-fueling/${raceType}` : '/nutrition/race-fueling';
    const response = await api.get(url);
    return response.data;
  },
};
```

### Step 3: Add Segments/Performance API
```typescript
// frontend/lib/api.ts - add:
export const performanceAPI = {
  getSegments: async (limit = 50) => {
    const response = await api.get('/segments', { params: { limit } });
    return response.data;
  },
  
  getSegmentEfforts: async (filters) => {
    const response = await api.get('/segment-efforts', { params: filters });
    return response.data;
  },
  
  getPersonalRecords: async (sportType?: string) => {
    const response = await api.get('/personal-records', {
      params: sportType ? { sport_type: sportType } : {}
    });
    return response.data;
  },
  
  getInjuryRisks: async () => {
    const response = await api.get('/injury-risks');
    return response.data;
  },
  
  getPerformanceSummary: async () => {
    const response = await api.get('/performance-summary');
    return response.data;
  },
  
  syncSegments: async () => {
    const response = await api.post('/sync-segments');
    return response.data;
  },
  
  scanPersonalRecords: async () => {
    const response = await api.post('/scan-prs');
    return response.data;
  },
};
```

### Step 4: Extend types
```typescript
// frontend/types/index.ts - add missing types
export interface TrainingLoadAnalysis {
  current_ctl: number;
  current_atl: number;
  current_tsb: number;
  ramp_rate: number;
  // ... etc
}

export interface FormStatus {
  status: string;
  date: string;
  ctl: number;
  atl: number;
  tsb: number;
  form: {
    label: string;
    description: string;
    recommendation: string;
  };
}

export interface FatigueReport {
  overall_fatigue_level: string;
  fatigue_score: number;
  signals: any[];
  recommendations: string[];
}

// ... etc for all new types
```

---

## 📊 Coverage Summary

| Category | Backend Ready | Frontend Integrated | Status |
|----------|---------------|---------------------|--------|
| Auth | ✅ | ✅ | 100% |
| Profile | ✅ | ✅ | 100% |
| Goals | ✅ | ✅ | 100% |
| Coach Plans | ✅ | ✅ | 100% |
| Training Zones | ✅ | ✅ | 100% |
| Strava OAuth | ✅ | ✅ | 100% |
| **Analytics** | ✅ | ⚠️ | **20%** (только timeline) |
| **Strava Activities** | ✅ | ❌ | **0%** |
| **Nutrition** | ✅ | ❌ | **0%** |
| **Segments/PRs** | ✅ | ❌ | **0%** |
| **Settings Page** | N/A | ❌ | **0%** |

**Overall Coverage: ~60%**

