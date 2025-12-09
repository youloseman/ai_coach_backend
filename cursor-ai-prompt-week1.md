# 🎯 Cursor AI Prompt: Week 1 - Analytics + Quick Wins

## 📋 Project Context

You are working on **AI Triathlon Coach** - a Next.js 16 + FastAPI application that helps triathletes train with AI-generated plans.

**Current Stack:**
- Frontend: Next.js 16 (App Router), TypeScript, Tailwind CSS, Axios
- Backend: FastAPI, PostgreSQL, SQLAlchemy
- State: localStorage for auth, React hooks for UI state
- API Base URL: Configured in `frontend/lib/api.ts`

**Project Structure:**
```
ai-coach/
├── frontend/
│   ├── app/
│   │   ├── dashboard/page.tsx    # Main dashboard
│   │   ├── coach/page.tsx
│   │   ├── goals/page.tsx
│   │   └── ...
│   ├── components/               # React components
│   ├── lib/
│   │   ├── api.ts               # API client functions
│   │   └── auth.ts              # Auth helpers
│   └── types/index.ts           # TypeScript types
├── main.py                      # FastAPI entry point
├── api_*.py                     # API route modules
└── models.py                    # SQLAlchemy models
```

**Important Files:**
- `frontend/lib/api.ts` - All API calls (authAPI, profileAPI, coachAPI, etc.)
- `frontend/app/dashboard/page.tsx` - Main dashboard (900+ lines)
- `frontend/components/` - Reusable UI components
- `main.py` - Backend routes including `/analytics/*` endpoints

---

## 🎯 Week 1 Goals

**Mission:** Connect existing backend analytics endpoints to frontend and add quick wins for better UX.

**Success Criteria:**
- ✅ Dashboard shows Form Status (Fresh/Optimal/Fatigued)
- ✅ Dashboard shows Fatigue Warning (if detected)
- ✅ Dashboard shows Race Predictions
- ✅ Dashboard shows Recent Activities (last 10)
- ✅ Dark mode toggle works throughout app
- ✅ Activity maps display on activity details
- ✅ No console errors, all TypeScript types correct

---

## 📅 DAY 1-2: Analytics Integration

### TASK 1.1: Extend API Client (frontend/lib/api.ts)

**Goal:** Add analytics API functions that call existing backend endpoints.

**Backend Endpoints (already exist in main.py):**
```python
GET /analytics/training_load?weeks=12
GET /analytics/form_status
GET /analytics/fatigue?weeks=4
GET /analytics/predict_race?goal_race_type=HALF_IRONMAN&goal_time=5:00&sport=run&weeks=12
GET /analytics/all_predictions?sport=run&weeks=12
GET /strava/activities?page=1&per_page=10
```

**Action:** Add this code to `frontend/lib/api.ts`:

```typescript
// Add this section after existing exports, before the final export

// ===== ANALYTICS API =====
export const analyticsAPI = {
  /**
   * Get comprehensive training load analysis (CTL, ATL, TSB, ramp rate)
   */
  getTrainingLoad: async (weeks: number = 12) => {
    try {
      const response = await api.get('/analytics/training_load', { 
        params: { weeks } 
      });
      return response.data;
    } catch (error) {
      console.error('Failed to fetch training load:', error);
      throw error;
    }
  },

  /**
   * Get current form status interpretation
   */
  getFormStatus: async () => {
    try {
      const response = await api.get('/analytics/form_status');
      return response.data;
    } catch (error) {
      console.error('Failed to fetch form status:', error);
      throw error;
    }
  },

  /**
   * Get fatigue analysis with signals and recommendations
   */
  getFatigueAnalysis: async (weeks: number = 4) => {
    try {
      const response = await api.get('/analytics/fatigue', { 
        params: { weeks } 
      });
      return response.data;
    } catch (error) {
      console.error('Failed to fetch fatigue analysis:', error);
      throw error;
    }
  },

  /**
   * Get race time prediction for specific goal
   */
  predictRace: async (params: {
    goalRaceType: string;
    goalTime: string;
    sport?: string;
    weeks?: number;
  }) => {
    try {
      const response = await api.get('/analytics/predict_race', {
        params: {
          goal_race_type: params.goalRaceType,
          goal_time: params.goalTime,
          sport: params.sport || 'run',
          weeks: params.weeks || 12
        }
      });
      return response.data;
    } catch (error) {
      console.error('Failed to predict race:', error);
      throw error;
    }
  },

  /**
   * Get predictions for all distances
   */
  getAllPredictions: async (sport: string = 'run', weeks: number = 12) => {
    try {
      const response = await api.get('/analytics/all_predictions', {
        params: { sport, weeks }
      });
      return response.data;
    } catch (error) {
      console.error('Failed to fetch all predictions:', error);
      throw error;
    }
  }
};

// Extend stravaAPI with activities endpoint
export const stravaAPI = {
  // ... existing methods (getStatus)
  
  /**
   * Get recent Strava activities with pagination
   */
  getActivities: async (page: number = 1, perPage: number = 10) => {
    try {
      const response = await api.get('/strava/activities', {
        params: { 
          page, 
          per_page: perPage 
        }
      });
      return response.data;
    } catch (error) {
      console.error('Failed to fetch activities:', error);
      throw error;
    }
  },
};
```

**Acceptance Criteria:**
- [ ] All analytics functions added to `frontend/lib/api.ts`
- [ ] Functions have TypeScript types
- [ ] Error handling implemented
- [ ] No TypeScript errors in api.ts

---

### TASK 1.2: Add TypeScript Types (frontend/types/index.ts)

**Goal:** Define types for all analytics responses.

**Action:** Add these interfaces to `frontend/types/index.ts`:

```typescript
// ===== ANALYTICS TYPES =====

export interface TrainingLoadAnalysis {
  status: string;
  analysis: {
    current_ctl: number;
    current_atl: number;
    current_tsb: number;
    current_ramp_rate: number;
    ctl_trend: string;
    atl_trend: string;
    tsb_trend: string;
    ramp_rate_status: string;
    weekly_tss: Array<{
      week_start: string;
      total_tss: number;
      run_tss: number;
      bike_tss: number;
      swim_tss: number;
    }>;
    timeline?: Array<{
      date: string;
      ctl: number;
      atl: number;
      tsb: number;
    }>;
  };
}

export interface FormStatus {
  status: string;
  current_date: string;
  current_ctl: number;
  current_atl: number;
  current_tsb: number;
  form: {
    label: string;
    color: string;
    description: string;
    recommendation: string;
  };
}

export interface FatigueSignal {
  type: string;
  severity: string;
  message: string;
  details: Record<string, any>;
}

export interface FatigueAnalysis {
  status: string;
  overall_fatigue_level: string;
  fatigue_score: number;
  signals: FatigueSignal[];
  recommendations: string[];
  metrics: {
    avg_hr_drift?: number;
    chronic_high_hr_days?: number;
    pace_decline?: number;
    days_since_rest?: number;
  };
}

export interface RacePrediction {
  status: string;
  prediction: {
    goal_race_type: string;
    goal_time: string;
    predicted_time: string;
    predicted_seconds: number;
    goal_seconds: number;
    probability_of_success: number;
    current_fitness_level: string;
    recommendations: string[];
    pacing_strategy?: {
      split_type: string;
      splits: Array<{
        segment: string;
        target_pace: string;
        target_time: string;
      }>;
    };
  };
}

export interface DistancePrediction {
  distance: string;
  predicted_time: string;
  pace_per_km?: string;
  form_adjusted_time?: string;
  confidence_level?: string;
}

export interface AllPredictions {
  status: string;
  sport: string;
  weeks_analyzed: number;
  best_efforts: Record<string, any>;
  predictions: DistancePrediction[];
  current_form: {
    ctl: number;
    atl: number;
    tsb: number;
    form_label: string;
  };
}

export interface StravaActivity {
  id: string;
  name: string;
  sport_type: string;
  start_date: string;
  distance_meters: number;
  moving_time_seconds: number;
  elapsed_time_seconds: number;
  total_elevation_gain: number;
  average_heartrate?: number;
  max_heartrate?: number;
  average_watts?: number;
  tss?: number;
}
```

**Acceptance Criteria:**
- [ ] All types added to types/index.ts
- [ ] Types match backend response structure
- [ ] No TypeScript errors

---

### TASK 1.3: Create Form Status Card Component

**Goal:** Display current form (Fresh/Optimal/Fatigued) with color coding.

**Action:** Create `frontend/components/FormStatusCard.tsx`:

```typescript
'use client';

import { useEffect, useState } from 'react';
import { analyticsAPI } from '@/lib/api';
import type { FormStatus } from '@/types';

export default function FormStatusCard() {
  const [formStatus, setFormStatus] = useState<FormStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadFormStatus();
  }, []);

  const loadFormStatus = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await analyticsAPI.getFormStatus();
      setFormStatus(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load form status');
      console.error('Form status error:', err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow p-6 animate-pulse">
        <div className="h-4 bg-gray-200 rounded w-1/3 mb-4"></div>
        <div className="h-8 bg-gray-200 rounded w-1/2 mb-2"></div>
        <div className="h-4 bg-gray-200 rounded w-full"></div>
      </div>
    );
  }

  if (error || !formStatus) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-2">Current Form</h3>
        <p className="text-sm text-gray-500">
          {error || 'Unable to load form status. Connect Strava and sync activities.'}
        </p>
      </div>
    );
  }

  const { form, current_tsb, current_ctl, current_atl } = formStatus;

  // Color mapping
  const colorClasses = {
    green: 'bg-green-100 text-green-800 border-green-300',
    yellow: 'bg-yellow-100 text-yellow-800 border-yellow-300',
    orange: 'bg-orange-100 text-orange-800 border-orange-300',
    red: 'bg-red-100 text-red-800 border-red-300',
  };

  const badgeColor = colorClasses[form.color as keyof typeof colorClasses] || colorClasses.yellow;

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">Current Form</h3>
      
      {/* Form Badge */}
      <div className={`inline-flex items-center px-4 py-2 rounded-full border-2 ${badgeColor} text-lg font-semibold mb-4`}>
        {form.label}
      </div>

      {/* Metrics */}
      <div className="grid grid-cols-3 gap-4 mb-4">
        <div>
          <p className="text-xs text-gray-500 uppercase">Fitness (CTL)</p>
          <p className="text-xl font-bold text-gray-900">{current_ctl.toFixed(1)}</p>
        </div>
        <div>
          <p className="text-xs text-gray-500 uppercase">Fatigue (ATL)</p>
          <p className="text-xl font-bold text-gray-900">{current_atl.toFixed(1)}</p>
        </div>
        <div>
          <p className="text-xs text-gray-500 uppercase">Form (TSB)</p>
          <p className={`text-xl font-bold ${
            current_tsb > 5 ? 'text-green-600' : 
            current_tsb < -10 ? 'text-red-600' : 
            'text-yellow-600'
          }`}>
            {current_tsb > 0 ? '+' : ''}{current_tsb.toFixed(1)}
          </p>
        </div>
      </div>

      {/* Description */}
      <p className="text-sm text-gray-700 mb-3">
        {form.description}
      </p>

      {/* Recommendation */}
      <div className="bg-blue-50 border-l-4 border-blue-400 p-3 rounded">
        <p className="text-sm text-blue-800">
          <strong>Recommendation:</strong> {form.recommendation}
        </p>
      </div>

      {/* Refresh button */}
      <button
        onClick={loadFormStatus}
        className="mt-4 text-sm text-blue-600 hover:text-blue-800 font-medium"
      >
        ↻ Refresh
      </button>
    </div>
  );
}
```

**Acceptance Criteria:**
- [ ] Component created and compiles without errors
- [ ] Shows loading state (skeleton)
- [ ] Shows error state gracefully
- [ ] Displays form badge with correct color
- [ ] Shows CTL/ATL/TSB metrics
- [ ] Shows description and recommendation
- [ ] Refresh button works

---

### TASK 1.4: Create Fatigue Warning Banner Component

**Goal:** Display warning banner if high fatigue detected.

**Action:** Create `frontend/components/FatigueWarningBanner.tsx`:

```typescript
'use client';

import { useEffect, useState } from 'react';
import { analyticsAPI } from '@/lib/api';
import type { FatigueAnalysis } from '@/types';

export default function FatigueWarningBanner() {
  const [fatigue, setFatigue] = useState<FatigueAnalysis | null>(null);
  const [loading, setLoading] = useState(true);
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => {
    loadFatigue();
  }, []);

  const loadFatigue = async () => {
    try {
      setLoading(true);
      const data = await analyticsAPI.getFatigueAnalysis(4);
      setFatigue(data);
    } catch (err) {
      console.error('Fatigue analysis error:', err);
    } finally {
      setLoading(false);
    }
  };

  // Don't show if dismissed or no high fatigue
  if (loading || dismissed || !fatigue) return null;
  
  const isHighFatigue = fatigue.overall_fatigue_level === 'HIGH' || 
                        fatigue.overall_fatigue_level === 'CRITICAL';
  
  if (!isHighFatigue) return null;

  const severityColors = {
    HIGH: 'bg-orange-100 border-orange-400 text-orange-800',
    CRITICAL: 'bg-red-100 border-red-400 text-red-800'
  };

  const bgColor = severityColors[fatigue.overall_fatigue_level as keyof typeof severityColors] || severityColors.HIGH;

  return (
    <div className={`${bgColor} border-l-4 p-4 rounded-lg mb-6 relative`}>
      {/* Dismiss button */}
      <button
        onClick={() => setDismissed(true)}
        className="absolute top-2 right-2 text-gray-500 hover:text-gray-700"
        aria-label="Dismiss"
      >
        ✕
      </button>

      {/* Warning icon and title */}
      <div className="flex items-start">
        <div className="flex-shrink-0 mr-3">
          <span className="text-2xl">⚠️</span>
        </div>
        <div className="flex-1">
          <h3 className="font-bold text-lg mb-2">
            {fatigue.overall_fatigue_level === 'CRITICAL' ? 'Critical Fatigue Detected' : 'High Fatigue Warning'}
          </h3>
          
          <p className="text-sm mb-3">
            Fatigue Score: <strong>{fatigue.fatigue_score.toFixed(1)}/100</strong>
          </p>

          {/* Fatigue Signals */}
          {fatigue.signals && fatigue.signals.length > 0 && (
            <div className="mb-3">
              <p className="text-sm font-semibold mb-1">Detected Issues:</p>
              <ul className="text-sm space-y-1">
                {fatigue.signals.map((signal, idx) => (
                  <li key={idx} className="flex items-start">
                    <span className="mr-2">•</span>
                    <span>{signal.message}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Recommendations */}
          {fatigue.recommendations && fatigue.recommendations.length > 0 && (
            <div className="bg-white bg-opacity-50 rounded p-3 mt-3">
              <p className="text-sm font-semibold mb-1">Recommendations:</p>
              <ul className="text-sm space-y-1">
                {fatigue.recommendations.map((rec, idx) => (
                  <li key={idx} className="flex items-start">
                    <span className="mr-2">→</span>
                    <span>{rec}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
```

**Acceptance Criteria:**
- [ ] Component created and compiles
- [ ] Only shows for HIGH or CRITICAL fatigue
- [ ] Can be dismissed
- [ ] Shows fatigue score
- [ ] Lists detected signals
- [ ] Shows recommendations
- [ ] Good visual hierarchy

---

### TASK 1.5: Create Race Prediction Card Component

**Goal:** Show race time prediction with probability and pacing.

**Action:** Update existing `frontend/components/RacePredictionCard.tsx` or create if missing:

```typescript
'use client';

import { useEffect, useState } from 'react';
import { analyticsAPI, goalsAPI } from '@/lib/api';
import type { RacePrediction, Goal } from '@/types';

export default function RacePredictionCard() {
  const [prediction, setPrediction] = useState<RacePrediction | null>(null);
  const [primaryGoal, setPrimaryGoal] = useState<Goal | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadPrediction();
  }, []);

  const loadPrediction = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Get primary goal first
      const goal = await goalsAPI.getPrimary();
      setPrimaryGoal(goal);

      if (!goal) {
        setError('No primary goal set');
        return;
      }

      // Get prediction for this goal
      const data = await analyticsAPI.predictRace({
        goalRaceType: goal.goal_type,
        goalTime: goal.target_time || '5:00:00',
        sport: 'run',
        weeks: 12
      });
      
      setPrediction(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load prediction');
      console.error('Prediction error:', err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow p-6 animate-pulse">
        <div className="h-4 bg-gray-200 rounded w-1/2 mb-4"></div>
        <div className="h-8 bg-gray-200 rounded w-2/3"></div>
      </div>
    );
  }

  if (error || !prediction) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-2">Race Prediction</h3>
        <p className="text-sm text-gray-500">
          {error || 'Set a goal and sync activities to see predictions'}
        </p>
      </div>
    );
  }

  const { prediction: pred } = prediction;
  const successProbability = pred.probability_of_success;
  
  // Color based on probability
  const probabilityColor = 
    successProbability >= 70 ? 'text-green-600' :
    successProbability >= 40 ? 'text-yellow-600' :
    'text-red-600';

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">
        Race Prediction: {pred.goal_race_type.replace(/_/g, ' ')}
      </h3>

      {/* Prediction vs Goal */}
      <div className="grid grid-cols-2 gap-4 mb-4">
        <div>
          <p className="text-xs text-gray-500 uppercase mb-1">Your Goal</p>
          <p className="text-2xl font-bold text-gray-900">{pred.goal_time}</p>
        </div>
        <div>
          <p className="text-xs text-gray-500 uppercase mb-1">Predicted</p>
          <p className="text-2xl font-bold text-blue-600">{pred.predicted_time}</p>
        </div>
      </div>

      {/* Probability */}
      <div className="mb-4">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium text-gray-700">Success Probability</span>
          <span className={`text-xl font-bold ${probabilityColor}`}>
            {successProbability.toFixed(0)}%
          </span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-3">
          <div
            className={`h-3 rounded-full transition-all ${
              successProbability >= 70 ? 'bg-green-500' :
              successProbability >= 40 ? 'bg-yellow-500' :
              'bg-red-500'
            }`}
            style={{ width: `${successProbability}%` }}
          />
        </div>
      </div>

      {/* Fitness Level */}
      <div className="bg-gray-50 rounded p-3 mb-4">
        <p className="text-sm text-gray-700">
          <strong>Current Fitness:</strong> {pred.current_fitness_level}
        </p>
      </div>

      {/* Recommendations */}
      {pred.recommendations && pred.recommendations.length > 0 && (
        <div className="border-t pt-4">
          <p className="text-sm font-semibold text-gray-900 mb-2">Recommendations:</p>
          <ul className="text-sm text-gray-700 space-y-1">
            {pred.recommendations.map((rec, idx) => (
              <li key={idx} className="flex items-start">
                <span className="mr-2 text-blue-500">→</span>
                <span>{rec}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Pacing Strategy (if available) */}
      {pred.pacing_strategy && (
        <div className="mt-4 border-t pt-4">
          <p className="text-sm font-semibold text-gray-900 mb-2">Pacing Strategy:</p>
          <div className="text-sm space-y-1">
            {pred.pacing_strategy.splits.map((split, idx) => (
              <div key={idx} className="flex justify-between">
                <span className="text-gray-700">{split.segment}</span>
                <span className="font-mono text-gray-900">{split.target_pace}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
```

**Acceptance Criteria:**
- [ ] Component displays race prediction
- [ ] Shows goal vs predicted time
- [ ] Success probability with color coding
- [ ] Progress bar visualization
- [ ] Shows recommendations
- [ ] Shows pacing strategy if available

---

### TASK 1.6: Create Recent Activities Component

**Goal:** Display last 10 activities from Strava.

**Action:** Update existing `frontend/components/ActivityCard.tsx`:

```typescript
'use client';

import type { StravaActivity } from '@/types';

interface ActivityCardProps {
  activity: StravaActivity;
}

export default function ActivityCard({ activity }: ActivityCardProps) {
  // Format duration
  const formatDuration = (seconds: number) => {
    const hours = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    if (hours > 0) {
      return `${hours}h ${mins}m`;
    }
    return `${mins}m`;
  };

  // Format distance
  const formatDistance = (meters: number) => {
    const km = meters / 1000;
    return `${km.toFixed(2)} km`;
  };

  // Format pace (min/km)
  const formatPace = (meters: number, seconds: number) => {
    if (meters === 0) return '-';
    const kmPerSec = meters / 1000 / seconds;
    const minPerKm = 1 / kmPerSec / 60;
    const mins = Math.floor(minPerKm);
    const secs = Math.floor((minPerKm - mins) * 60);
    return `${mins}:${secs.toString().padStart(2, '0')} /km`;
  };

  // Sport icon
  const getSportIcon = (sportType: string) => {
    const type = sportType.toLowerCase();
    if (type.includes('run')) return '🏃';
    if (type.includes('ride') || type.includes('bike')) return '🚴';
    if (type.includes('swim')) return '🏊';
    return '💪';
  };

  // Sport color
  const getSportColor = (sportType: string) => {
    const type = sportType.toLowerCase();
    if (type.includes('run')) return 'bg-orange-100 text-orange-800';
    if (type.includes('ride') || type.includes('bike')) return 'bg-purple-100 text-purple-800';
    if (type.includes('swim')) return 'bg-cyan-100 text-cyan-800';
    return 'bg-gray-100 text-gray-800';
  };

  const date = new Date(activity.start_date);
  const dateStr = date.toLocaleDateString('en-US', { 
    month: 'short', 
    day: 'numeric',
    year: 'numeric'
  });

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4 hover:shadow-md transition-shadow">
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xl">{getSportIcon(activity.sport_type)}</span>
            <span className={`px-2 py-0.5 rounded text-xs font-medium ${getSportColor(activity.sport_type)}`}>
              {activity.sport_type}
            </span>
          </div>
          <h4 className="font-semibold text-gray-900 line-clamp-1">
            {activity.name}
          </h4>
          <p className="text-xs text-gray-500 mt-1">{dateStr}</p>
        </div>
      </div>

      {/* Metrics */}
      <div className="grid grid-cols-2 gap-3 text-sm">
        <div>
          <p className="text-gray-500 text-xs">Distance</p>
          <p className="font-semibold text-gray-900">
            {formatDistance(activity.distance_meters)}
          </p>
        </div>
        <div>
          <p className="text-gray-500 text-xs">Duration</p>
          <p className="font-semibold text-gray-900">
            {formatDuration(activity.moving_time_seconds)}
          </p>
        </div>
        <div>
          <p className="text-gray-500 text-xs">Pace</p>
          <p className="font-semibold text-gray-900">
            {formatPace(activity.distance_meters, activity.moving_time_seconds)}
          </p>
        </div>
        {activity.total_elevation_gain > 0 && (
          <div>
            <p className="text-gray-500 text-xs">Elevation</p>
            <p className="font-semibold text-gray-900">
              {Math.round(activity.total_elevation_gain)}m
            </p>
          </div>
        )}
        {activity.average_heartrate && (
          <div>
            <p className="text-gray-500 text-xs">Avg HR</p>
            <p className="font-semibold text-gray-900">
              {Math.round(activity.average_heartrate)} bpm
            </p>
          </div>
        )}
        {activity.tss && (
          <div>
            <p className="text-gray-500 text-xs">TSS</p>
            <p className="font-semibold text-gray-900">
              {Math.round(activity.tss)}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
```

Now create a container component `frontend/components/RecentActivitiesList.tsx`:

```typescript
'use client';

import { useEffect, useState } from 'react';
import { stravaAPI } from '@/lib/api';
import type { StravaActivity } from '@/types';
import ActivityCard from './ActivityCard';

export default function RecentActivitiesList() {
  const [activities, setActivities] = useState<StravaActivity[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadActivities();
  }, []);

  const loadActivities = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await stravaAPI.getActivities(1, 10);
      setActivities(data.activities || data || []);
    } catch (err: any) {
      setError(err.message || 'Failed to load activities');
      console.error('Activities error:', err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="space-y-4">
        {[1, 2, 3].map((i) => (
          <div key={i} className="bg-white rounded-lg border p-4 animate-pulse">
            <div className="h-4 bg-gray-200 rounded w-2/3 mb-3"></div>
            <div className="grid grid-cols-2 gap-3">
              <div className="h-4 bg-gray-200 rounded"></div>
              <div className="h-4 bg-gray-200 rounded"></div>
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white rounded-lg border p-6 text-center">
        <p className="text-sm text-gray-500 mb-3">{error}</p>
        <button
          onClick={loadActivities}
          className="text-sm text-blue-600 hover:text-blue-800 font-medium"
        >
          Try Again
        </button>
      </div>
    );
  }

  if (activities.length === 0) {
    return (
      <div className="bg-white rounded-lg border p-6 text-center">
        <p className="text-gray-500 mb-2">No activities yet</p>
        <p className="text-sm text-gray-400">
          Connect Strava and sync your workouts to see them here
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {activities.map((activity) => (
        <ActivityCard key={activity.id} activity={activity} />
      ))}
    </div>
  );
}
```

**Acceptance Criteria:**
- [ ] ActivityCard displays correctly
- [ ] Shows sport icon and badge
- [ ] Formats metrics properly
- [ ] RecentActivitiesList loads activities
- [ ] Shows loading skeletons
- [ ] Handles empty state

---

### TASK 1.7: Integrate Components into Dashboard

**Goal:** Add all new components to the main dashboard.

**Action:** Modify `frontend/app/dashboard/page.tsx`:

Find the location after the Performance Chart section and add:

```typescript
{/* NEW: Analytics Cards Row */}
<div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
  <FormStatusCard />
  <RacePredictionCard />
  <div className="bg-white rounded-lg shadow p-6">
    {/* Placeholder for future analytics */}
    <h3 className="text-lg font-semibold text-gray-900 mb-2">Training Load</h3>
    <p className="text-sm text-gray-500">Coming soon: Detailed load analysis</p>
  </div>
</div>

{/* NEW: Fatigue Warning (only shows if high fatigue) */}
<FatigueWarningBanner />

{/* NEW: Recent Activities Section */}
<div className="bg-white rounded-lg shadow p-6 mb-8">
  <div className="flex items-center justify-between mb-6">
    <h2 className="text-xl font-bold text-gray-900">Recent Activities</h2>
    <button
      onClick={() => window.location.reload()}
      className="text-sm text-blue-600 hover:text-blue-800 font-medium"
    >
      ↻ Sync
    </button>
  </div>
  <RecentActivitiesList />
</div>
```

Add imports at the top:

```typescript
import FormStatusCard from '@/components/FormStatusCard';
import FatigueWarningBanner from '@/components/FatigueWarningBanner';
import RacePredictionCard from '@/components/RacePredictionCard';
import RecentActivitiesList from '@/components/RecentActivitiesList';
```

**Acceptance Criteria:**
- [ ] All components appear on dashboard
- [ ] Components load in parallel
- [ ] No layout breaks
- [ ] Responsive on mobile
- [ ] No console errors

---

## 📅 DAY 3: Dark Mode

### TASK 3.1: Setup Dark Mode Provider

**Goal:** Add theme toggle that works throughout the app.

**Action 1:** Install dependencies (if not already):

```bash
cd frontend
npm install next-themes
```

**Action 2:** Create theme provider `frontend/app/providers.tsx` (update if exists):

```typescript
'use client';

import { ThemeProvider } from 'next-themes';

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <ThemeProvider attribute="class" defaultTheme="light" enableSystem>
      {children}
    </ThemeProvider>
  );
}
```

**Action 3:** Wrap app in provider in `frontend/app/layout.tsx`:

```typescript
import { Providers } from './providers';

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body>
        <Providers>
          {children}
        </Providers>
      </body>
    </html>
  );
}
```

**Action 4:** Create theme toggle button `frontend/components/ThemeToggle.tsx`:

```typescript
'use client';

import { useTheme } from 'next-themes';
import { useEffect, useState } from 'react';

export default function ThemeToggle() {
  const [mounted, setMounted] = useState(false);
  const { theme, setTheme } = useTheme();

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) {
    return (
      <button className="w-10 h-10 rounded-lg bg-gray-200 animate-pulse" />
    );
  }

  return (
    <button
      onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
      className="w-10 h-10 rounded-lg bg-gray-200 dark:bg-gray-700 flex items-center justify-center hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors"
      aria-label="Toggle theme"
    >
      {theme === 'dark' ? (
        <span className="text-xl">☀️</span>
      ) : (
        <span className="text-xl">🌙</span>
      )}
    </button>
  );
}
```

**Action 5:** Add toggle to Header component `frontend/components/Header.tsx`:

```typescript
import ThemeToggle from './ThemeToggle';

// In the header's right side, add:
<ThemeToggle />
```

**Action 6:** Update Tailwind config `frontend/tailwind.config.js`:

```javascript
module.exports = {
  darkMode: 'class',
  // ... rest of config
}
```

**Action 7:** Add dark mode classes to all components:

```typescript
// Example pattern for each component:
<div className="bg-white dark:bg-gray-800 rounded-lg shadow dark:shadow-gray-700">
  <h3 className="text-gray-900 dark:text-gray-100">Title</h3>
  <p className="text-gray-600 dark:text-gray-400">Description</p>
</div>
```

Apply to:
- Dashboard page
- All cards and components
- Forms and inputs
- Buttons

**Acceptance Criteria:**
- [ ] Theme toggle appears in header
- [ ] Toggle works (light ↔ dark)
- [ ] Theme persists on page reload
- [ ] All text is readable in both themes
- [ ] No flashing on page load
- [ ] System theme detection works

---

## 📅 DAY 4: Activity Maps (Bonus)

### TASK 4.1: Add Map to Activity Details

**Goal:** Show activity route on a map using polyline from Strava.

**Action 1:** Install Leaflet:

```bash
cd frontend
npm install leaflet react-leaflet
npm install -D @types/leaflet
```

**Action 2:** Create map component `frontend/components/ActivityMap.tsx`:

```typescript
'use client';

import { MapContainer, TileLayer, Polyline } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import { useEffect, useState } from 'react';

interface ActivityMapProps {
  polyline?: string;
}

export default function ActivityMap({ polyline }: ActivityMapProps) {
  const [coordinates, setCoordinates] = useState<[number, number][]>([]);

  useEffect(() => {
    if (!polyline) return;

    // Decode polyline (Google's encoded polyline format)
    // This is a simplified version - you may need a library like @mapbox/polyline
    try {
      const decoded = decodePolyline(polyline);
      setCoordinates(decoded);
    } catch (err) {
      console.error('Failed to decode polyline:', err);
    }
  }, [polyline]);

  if (!polyline || coordinates.length === 0) {
    return (
      <div className="bg-gray-100 dark:bg-gray-700 rounded-lg h-64 flex items-center justify-center">
        <p className="text-gray-500 dark:text-gray-400">No map data available</p>
      </div>
    );
  }

  // Calculate center and bounds
  const center: [number, number] = [
    coordinates[Math.floor(coordinates.length / 2)][0],
    coordinates[Math.floor(coordinates.length / 2)][1]
  ];

  return (
    <MapContainer
      center={center}
      zoom={13}
      className="h-64 rounded-lg z-0"
    >
      <TileLayer
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
      />
      <Polyline 
        positions={coordinates} 
        color="#2563eb"
        weight={3}
      />
    </MapContainer>
  );
}

// Simplified polyline decoder (you may want to use a library)
function decodePolyline(encoded: string): [number, number][] {
  // This is a placeholder - implement full decoder or use @mapbox/polyline
  // For now, return empty array
  return [];
  
  // TODO: Install @mapbox/polyline and use:
  // import polyline from '@mapbox/polyline';
  // return polyline.decode(encoded);
}
```

**Action 3:** Add map to ActivityCard (make it clickable to expand):

```typescript
// In ActivityCard.tsx, add state for expanded view
const [expanded, setExpanded] = useState(false);

// Add click handler
<div 
  className="... cursor-pointer" 
  onClick={() => setExpanded(!expanded)}
>
  {/* existing card content */}
</div>

{/* Add expanded view */}
{expanded && activity.map?.polyline && (
  <div className="mt-4">
    <ActivityMap polyline={activity.map.polyline} />
  </div>
)}
```

**Acceptance Criteria:**
- [ ] Map component renders without errors
- [ ] Shows OpenStreetMap tiles
- [ ] Displays activity route if polyline available
- [ ] Gracefully handles missing map data
- [ ] Works in dark mode

---

## 📅 DAY 5-7: Testing & Polish

### TASK 5.1: End-to-End Testing

**Goal:** Ensure everything works together.

**Test Scenarios:**

1. **Fresh User Journey:**
   - [ ] Register new account
   - [ ] Complete onboarding
   - [ ] Connect Strava
   - [ ] Set primary goal
   - [ ] View dashboard - all analytics load
   - [ ] Generate weekly plan
   - [ ] Toggle dark mode

2. **Analytics Display:**
   - [ ] Form Status Card shows correct data
   - [ ] Fatigue Warning appears when should
   - [ ] Race Predictions load
   - [ ] Recent Activities display
   - [ ] All components handle loading state
   - [ ] All components handle errors

3. **Performance:**
   - [ ] Dashboard loads in < 3 seconds
   - [ ] No console errors
   - [ ] No memory leaks
   - [ ] Smooth scrolling

4. **Mobile:**
   - [ ] Dashboard responsive on phone
   - [ ] All cards readable
   - [ ] Forms work on mobile
   - [ ] Dark mode toggle accessible

---

### TASK 5.2: Bug Fixes

**Common Issues to Check:**

```typescript
// 1. Check all API calls have error handling
try {
  const data = await api.get(...);
} catch (error) {
  console.error('Error:', error);
  // Show user-friendly message
}

// 2. Check all useState hooks are typed
const [data, setData] = useState<MyType | null>(null);

// 3. Check all useEffect dependencies
useEffect(() => {
  loadData();
}, [/* include all dependencies */]);

// 4. Check all async functions in useEffect
useEffect(() => {
  const load = async () => {
    // async code
  };
  load();
}, []);

// 5. Check conditional rendering
{data ? (
  <Component data={data} />
) : (
  <EmptyState />
)}
```

---

### TASK 5.3: Code Quality

**Action:** Run these commands and fix issues:

```bash
cd frontend

# TypeScript check
npx tsc --noEmit

# ESLint
npm run lint

# Format code
npx prettier --write "**/*.{ts,tsx}"

# Build test
npm run build
```

**Acceptance Criteria:**
- [ ] No TypeScript errors
- [ ] No ESLint errors
- [ ] Code formatted consistently
- [ ] Build succeeds
- [ ] All imports resolve

---

## ✅ Week 1 Completion Checklist

### Analytics Integration
- [ ] analyticsAPI added to lib/api.ts
- [ ] All TypeScript types defined
- [ ] FormStatusCard component working
- [ ] FatigueWarningBanner component working
- [ ] RacePredictionCard component working
- [ ] RecentActivitiesList component working
- [ ] All components integrated into dashboard

### Dark Mode
- [ ] next-themes installed
- [ ] ThemeProvider setup
- [ ] ThemeToggle component works
- [ ] All components have dark mode styles
- [ ] Theme persists on reload

### Activity Maps
- [ ] Leaflet installed
- [ ] ActivityMap component created
- [ ] Maps display activity routes
- [ ] Handles missing map data

### Quality
- [ ] No console errors
- [ ] No TypeScript errors
- [ ] All components tested manually
- [ ] Mobile responsive
- [ ] Performance acceptable

---

## 🚨 IMPORTANT NOTES

1. **Always test after each task** - Don't move forward if something is broken
2. **Use existing components** - Check `frontend/components/` before creating new
3. **Follow TypeScript strictly** - No `any` types
4. **Match existing style** - Look at current components for patterns
5. **Handle errors gracefully** - Never let app crash
6. **Test dark mode** - After styling each component
7. **Check mobile** - Use Chrome DevTools mobile view

---

## 💬 If You Get Stuck

**Problem:** TypeScript errors
**Solution:** Check types/index.ts, ensure all interfaces match backend

**Problem:** API calls fail
**Solution:** Check network tab, verify endpoint exists in main.py

**Problem:** Component not rendering
**Solution:** Check React DevTools, look for errors in console

**Problem:** Dark mode not working
**Solution:** Check Tailwind config has `darkMode: 'class'`

**Problem:** Build fails
**Solution:** Run `npx tsc --noEmit` to see TypeScript errors first

---

## 🎯 Success Criteria

At the end of Week 1, you should have:

✅ Dashboard with 4 new analytics components
✅ Fatigue warnings that actually help users
✅ Race predictions that motivate
✅ Recent activities that show progress
✅ Beautiful dark mode throughout app
✅ Activity maps (bonus)
✅ Zero console errors
✅ Smooth, polished experience

**This will make your app immediately more valuable to users!**

---

Good luck! Start with Task 1.1 and work through methodically. 🚀
