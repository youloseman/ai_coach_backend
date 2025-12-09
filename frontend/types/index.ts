// types/index.ts

// ===== USER & AUTH =====

export interface User {
  id: number;
  email: string;
  username: string;
  full_name: string | null;
  is_active: boolean;
  is_verified: boolean;
  strava_athlete_id: string | null;
  created_at: string;
}

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface RegisterData {
  email: string;
  username: string;
  password: string;
  full_name?: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

// ===== ATHLETE PROFILE =====

export interface AthleteProfile {
  id: number;
  user_id: number;
  age: number | null;
  gender: string | null;
  weight_kg: number | null;
  height_cm: number | null;
  years_of_experience: number;
  primary_discipline: string | null;
  training_zones_run: Record<string, unknown> | null;
  training_zones_bike: Record<string, unknown> | null;
  training_zones_swim: Record<string, unknown> | null;
  available_hours_per_week: number;
  auto_avg_hours_last_12_weeks: number;
  auto_current_weekly_streak_weeks: number;
  preferred_training_days: string[] | null;
  zones_last_updated: string | null;
  auto_weeks_analyzed: number;
  auto_longest_weekly_streak_weeks: number;
  auto_discipline_hours_per_week: Record<string, number> | null;
  created_at?: string;
  updated_at?: string;
}

export interface ProfileUpdate {
  age?: number;
  gender?: string;
  weight_kg?: number;
  height_cm?: number;
  years_of_experience?: number;
  primary_discipline?: string;
  available_hours_per_week?: number;
  preferred_training_days?: string[];
}

// ===== GOALS =====

export interface Goal {
  id: number;
  user_id: number;
  goal_type: string;  // "SPRINT", "OLYMPIC", "HALF_IRONMAN", "IRONMAN"
  target_time: string | null;  // "4:30" или "sub 5:00"
  race_date: string;  // ISO date
  race_name: string | null;
  race_location: string | null;
  is_primary: boolean;
  is_completed: boolean;
  created_at: string;
}

export interface GoalCreate {
  goal_type: string;
  target_time?: string;
  race_date: string;
  race_name?: string;
  race_location?: string;
  is_primary?: boolean;
}

// ===== COACH / PLANNING =====

export interface CoachGoalInput {
  main_goal_type: string; // e.g. "HALF_IRONMAN" / "MARATHON" / "10K"
  main_goal_target_time: string; // e.g. "4:30"
  main_goal_race_date: string; // ISO date "YYYY-MM-DD"
  secondary_goals?: string[];
  comments?: string;
}

export interface WeeklyPlanRequestPayload {
  goal: CoachGoalInput;
  week_start_date: string; // "YYYY-MM-DD"
  available_hours_per_week: number;
  notes?: string;
}

export interface WeeklyPlanDay {
  date: string;
  sport: string;
  session_type: string;
  duration_min: number;
  intensity: string;
  description: string;
  primary_goal: string;
  priority: string;
}

export interface WeeklyPlan {
  week_start_date: string;
  total_planned_hours: number;
  days: WeeklyPlanDay[];
  notes: {
    overall_focus: string;
    recovery_guidelines: string;
    nutrition_tips: string;
  };
}

export interface WeeklyPlanCalendarExportResponse {
  status: string;
  message: string;
  download_url: string;
  filename: string;
  week_start_date: string;
  total_workouts: number;
}

export interface MultiWeekPlanRequestPayload {
  goal: CoachGoalInput;
  start_date: string; // "YYYY-MM-DD"
  num_weeks: number; // 4-24
  base_hours_per_week: number;
  peak_hours_per_week: number;
  notes?: string;
}

export interface MultiWeekPlanEmailResponse {
  status: string;
  message: string;
  num_weeks: number;
  start_date: string;
  calendar_download_url: string | null;
  calendar_filename: string | null;
}

export interface WeeklyReportEmailRequestPayload {
  goal: CoachGoalInput;
  week_start_date: string;
  available_hours_per_week: number;
  notes?: string;
  progress_weeks?: number;
  subject?: string;
}

export interface WeeklyReportEmailResponse {
  status: string;
  message: string;
  week_start_date: string;
  planned_hours: number;
  progress_weeks: number;
  readiness_score: number;
  readiness_label: string;
}

// ===== COACH PROFILE & ZONES (JSON-backed) =====

export type CoachLevel =
  | 'beginner'
  | 'intermediate'
  | 'advanced'
  | 'high_performance';

export interface CoachProfile {
  level: CoachLevel;
  max_hours_per_week: number;
  height_cm: number | null;
  weight_kg: number | null;
  age: number | null;
  preferred_sport_days: Record<string, string[]>;
  injuries: string | null;
  constraints: string | null;
  equipment: string | null;
  notes: string | null;
  auto_weeks_analyzed: number | null;
  auto_current_weekly_streak_weeks: number | null;
  auto_longest_weekly_streak_weeks: number | null;
  auto_avg_hours_last_12_weeks: number | null;
  auto_avg_hours_last_52_weeks: number | null;
  auto_discipline_hours_per_week: Record<string, number> | null;
  training_zones_run: Record<string, unknown> | null;
  training_zones_bike: Record<string, unknown> | null;
  training_zones_swim: Record<string, unknown> | null;
  zones_last_updated: string | null;
}

export interface CoachZonesSummary {
  zones_last_updated: string | null;
  run: Record<string, unknown> | null;
  bike: Record<string, unknown> | null;
  swim: Record<string, unknown> | null;
}

export interface CoachZonesAutoFromActivitiesResponse {
  status: string;
  message: string;
  best_efforts: Record<string, unknown>;
  zones_calculated: {
    run: boolean;
    bike: boolean;
    swim: boolean;
  };
  profile: CoachProfile;
}

export interface CoachZonesManualInput {
  run_race_type?: string;
  run_race_time_seconds?: number;
  run_race_distance_km?: number;
  bike_ftp_watts?: number;
  swim_css_pace_per_100m?: number;
}

export interface CoachZonesManualResponse {
  status: string;
  message: string;
  zones_calculated: {
    run: boolean;
    bike: boolean;
    swim: boolean;
  };
  profile: CoachProfile;
}

// ===== STRAVA STATUS =====

export interface StravaStatus {
  connected: boolean;
  athlete_name?: string | null;
  athlete_id?: number | null;
  expires_at?: number | null;
}

export interface StravaActivity {
  id?: number;
  name: string;
  sport_type: string;
  start_date: string;
  distance_m?: number;
  distance_meters?: number;
  moving_time_s?: number;
  moving_time_seconds?: number;
  elapsed_time_seconds?: number;
  total_elevation_gain_m?: number;
  total_elevation_gain?: number;
  average_heartrate?: number;
  max_heartrate?: number;
  average_speed_m_s?: number;
  average_watts?: number;
  tss?: number;
}

// ===== ANALYTICS =====

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
  description?: string;
  details: Record<string, unknown>;
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

export interface AllRacePredictions {
  status: string;
  sport: string;
  predictions: Array<{
    race_type: string;
    predicted_time: string;
    predicted_time_seconds: number;
    confidence: string;
    pace_per_km?: string;
    based_on?: {
      effort_type: string;
      time: string;
      date: string;
    };
  }>;
  best_efforts?: Record<string, {
    time?: string;
    formatted_time?: string;
  }>;
}