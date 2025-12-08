// lib/api.ts
import axios from 'axios';
import { QueryClient } from '@tanstack/react-query';
import type {
  AuthResponse,
  LoginCredentials,
  RegisterData,
  User,
  AthleteProfile,
  Goal,
  GoalCreate,
  WeeklyPlan,
  WeeklyPlanRequestPayload,
  WeeklyPlanCalendarExportResponse,
  MultiWeekPlanRequestPayload,
  MultiWeekPlanEmailResponse,
  WeeklyReportEmailRequestPayload,
  WeeklyReportEmailResponse,
  CoachZonesSummary,
  CoachZonesAutoFromActivitiesResponse,
  CoachProfile,
  CoachZonesManualInput,
  CoachZonesManualResponse,
  StravaStatus,
} from '@/types';

export const API_URL =
  process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Shared React Query client for the app
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5, // 5 minutes
      // In React Query v5, cacheTime was renamed to gcTime
      gcTime: 1000 * 60 * 30, // 30 minutes
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// ---------- REQUEST INTERCEPTOR ----------
api.interceptors.request.use((config) => {
  if (typeof window !== 'undefined') {
    const token = localStorage.getItem('token');

    if (token) {
      config.headers = config.headers ?? {};
      config.headers.Authorization = `Bearer ${token}`;
    }

    if (process.env.NODE_ENV === 'development') {
      console.log('🚀 Request:', {
        url: config.url,
        method: config.method,
        hasToken: !!token,
        headers: config.headers,
      });
    }
  }

  return config;
});

// Response interceptor - обработка ошибок
api.interceptors.response.use(
  (response) => response,
  (error) => {
    // Network error
    if (!error.response) {
      console.error('Network error:', error.message);
      return Promise.reject(new Error('Network error. Please check your connection.'));
    }

    const status = error.response?.status;
    const data = error.response?.data;
    const requestUrl: string | undefined = error.config?.url;

    // 401 - Unauthorized
    if (status === 401) {
      const isAuthRequest =
        requestUrl?.includes('/auth/login') || requestUrl?.includes('/auth/register');

      // Для /auth/login и /auth/register не считаем это "просроченной сессией",
      // просто пробрасываем нормальное сообщение об ошибке дальше.
      if (isAuthRequest) {
        const message = data?.detail || 'Incorrect email or password';
        return Promise.reject(new Error(message));
      }

      // Для всех остальных запросов 401 трактуем как истёкший/некорректный токен.
      console.error('Token expired - logging out');
      localStorage.removeItem('token');
      localStorage.removeItem('user');

      // Redirect to login only if not already on login page
      if (!window.location.pathname.includes('/login')) {
        window.location.href = '/login';
      }

      return Promise.reject(new Error('Session expired. Please login again.'));
    }

    // 403 - Forbidden
    if (status === 403) {
      return Promise.reject(new Error('Access denied.'));
    }

    // 404 - Not Found
    if (status === 404) {
      const message = data?.detail || 'Resource not found.';
      return Promise.reject(new Error(message));
    }

    // 422 - Validation Error
    if (status === 422) {
      const validationErrors = data?.detail || [];
      const items: { msg?: string }[] = Array.isArray(validationErrors)
        ? (validationErrors as { msg?: string }[])
        : [];
      const message =
        items.length > 0
          ? items
              .map((e) => e.msg)
              .filter((m): m is string => Boolean(m))
              .join(', ')
          : 'Validation error';
      return Promise.reject(new Error(message));
    }

    // 500 - Server Error
    if (status === 500) {
      const message = data?.detail || 'Server error. Please try again later.';
      return Promise.reject(new Error(message));
    }

    // Generic error
    const message = data?.detail || error.message || 'An error occurred';
    return Promise.reject(new Error(message));
  }
);

// ---------- AUTH ----------
export const authAPI = {
  register: async (data: RegisterData): Promise<AuthResponse> => {
    const response = await api.post<AuthResponse>('/auth/register', data);
    return response.data;
  },

  login: async (data: LoginCredentials): Promise<AuthResponse> => {
    // FastAPI OAuth2 требует URLSearchParams
    const params = new URLSearchParams();
    params.append('username', data.email); // OAuth2 использует "username"
    params.append('password', data.password);
    
    const response = await api.post<AuthResponse>('/auth/login', params, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
    });
    return response.data;
  },

  getCurrentUser: async (): Promise<User> => {
    const response = await api.get<User>('/auth/me');
    return response.data;
  },
};

// ---------- PROFILE ----------
export const profileAPI = {
  get: async (): Promise<AthleteProfile> => {
    const response = await api.get<AthleteProfile>('/profile');
    return response.data;
  },

  update: async (data: Partial<AthleteProfile>): Promise<AthleteProfile> => {
    const response = await api.patch<AthleteProfile>('/profile', data);
    return response.data;
  },
};

// ---------- GOALS ----------
export const goalsAPI = {
  list: async (includeCompleted = false): Promise<Goal[]> => {
    const response = await api.get<Goal[]>('/goals', {
      params: { include_completed: includeCompleted },
    });
    return response.data;
  },

  create: async (data: GoalCreate): Promise<Goal> => {
    const response = await api.post<Goal>('/goals', data);
    return response.data;
  },

  getPrimary: async (): Promise<Goal> => {
    const response = await api.get<Goal>('/goals/primary');
    return response.data;
  },
};

// ---------- COACH / PLANNING ----------
export const coachAPI = {
  generateWeeklyPlan: async (
    payload: WeeklyPlanRequestPayload
  ): Promise<WeeklyPlan> => {
    const response = await api.post<WeeklyPlan>('/coach/plan', payload);
    return response.data;
  },

  exportWeeklyPlanToCalendar: async (
    payload: WeeklyPlanRequestPayload
  ): Promise<WeeklyPlanCalendarExportResponse> => {
    const response = await api.post<WeeklyPlanCalendarExportResponse>(
      '/coach/plan/export_calendar',
      payload
    );
    return response.data;
  },

  sendMultiWeekPlanEmail: async (
    payload: MultiWeekPlanRequestPayload
  ): Promise<MultiWeekPlanEmailResponse> => {
    const response = await api.post<MultiWeekPlanEmailResponse>(
      '/coach/multi_week_plan_email',
      payload
    );
    return response.data;
  },

  sendWeeklyReportEmail: async (
    payload: WeeklyReportEmailRequestPayload
  ): Promise<WeeklyReportEmailResponse> => {
    const response = await api.post<WeeklyReportEmailResponse>(
      '/coach/weekly_report_email',
      payload
    );
    return response.data;
  },

  getZones: async (): Promise<CoachZonesSummary> => {
    const response = await api.get<CoachZonesSummary>('/coach/zones');
    return response.data;
  },

  autoCalculateZonesFromActivities: async (
    weeks = 260
  ): Promise<CoachZonesAutoFromActivitiesResponse> => {
    const response = await api.post<CoachZonesAutoFromActivitiesResponse>(
      '/coach/zones/auto_from_activities',
      null,
      { params: { weeks } }
    );
    return response.data;
  },

  calculateZonesManual: async (
    payload: CoachZonesManualInput
  ): Promise<CoachZonesManualResponse> => {
    const response = await api.post<CoachZonesManualResponse>(
      '/coach/zones/manual',
      payload
    );
    return response.data;
  },

  getProfile: async (): Promise<CoachProfile> => {
    const response = await api.get<CoachProfile>('/coach/profile');
    return response.data;
  },

  updateProfile: async (profile: CoachProfile): Promise<CoachProfile> => {
    const response = await api.post<CoachProfile>('/coach/profile', profile);
    return response.data;
  },

  autoUpdateProfileFromHistory: async (
    weeks = 200
  ): Promise<CoachProfile> => {
    const response = await api.post<CoachProfile>(
      '/coach/profile/auto_from_history',
      null,
      { params: { weeks } }
    );
    return response.data;
  },
};

// ---------- STRAVA ----------
export const stravaAPI = {
  getStatus: async (): Promise<StravaStatus> => {
    const response = await api.get<StravaStatus>('/strava/status');
    return response.data;
  },
  
  getActivities: async (page = 1, perPage = 10) => {
    const response = await api.get('/strava/activities', {
      params: { page, per_page: perPage }
    });
    return response.data;
  },
};

// ---------- ANALYTICS ----------
export const analyticsAPI = {
  getTrainingLoad: async (weeks = 12) => {
    const response = await api.get('/analytics/training_load', {
      params: { weeks }
    });
    return response.data;
  },
  
  getFormStatus: async () => {
    const response = await api.get('/analytics/form_status');
    return response.data;
  },
  
  getFatigueAnalysis: async (weeks = 4) => {
    const response = await api.get('/analytics/fatigue', {
      params: { weeks }
    });
    return response.data;
  },
  
  predictRace: async (
    goalRaceType: string,
    goalTime: string,
    sport = 'run',
    weeks = 12
  ) => {
    const response = await api.get('/analytics/predict_race', {
      params: {
        goal_race_type: goalRaceType,
        goal_time: goalTime,
        sport,
        weeks
      }
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

// ---------- NUTRITION ----------
export const nutritionAPI = {
  calculateTargets: async (payload: {
    weight_kg: number;
    goal: string;
    activity_level?: string;
  }) => {
    const response = await api.post('/nutrition/targets/calculate', payload);
    return response.data;
  },
  
  getTargets: async () => {
    const response = await api.get('/nutrition/targets');
    return response.data;
  },
  
  generateRaceFueling: async (payload: {
    race_type: string;
    estimated_duration_hours: number;
    weight_kg: number;
    experience_level?: string;
  }) => {
    const response = await api.post('/nutrition/race-fueling', payload);
    return response.data;
  },
  
  getRaceFueling: async (raceType?: string) => {
    const url = raceType
      ? `/nutrition/race-fueling/${raceType}`
      : '/nutrition/race-fueling';
    const response = await api.get(url);
    return response.data;
  },
};

// ---------- PERFORMANCE / SEGMENTS ----------
export const performanceAPI = {
  getSegments: async (limit = 50) => {
    const response = await api.get('/segments', {
      params: { limit }
    });
    return response.data;
  },
  
  getSegmentEfforts: async (filters?: {
    segment_id?: number;
    limit?: number;
    only_prs?: boolean;
  }) => {
    const response = await api.get('/segment-efforts', {
      params: filters
    });
    return response.data;
  },
  
  getSegmentPRs: async (limit = 50) => {
    const response = await api.get('/segment-prs', {
      params: { limit }
    });
    return response.data;
  },
  
  getPersonalRecords: async (sportType?: string) => {
    const response = await api.get('/personal-records', {
      params: sportType ? { sport_type: sportType } : {}
    });
    return response.data;
  },
  
  getPersonalRecord: async (sportType: string, distanceCategory: string) => {
    const response = await api.get(
      `/personal-records/${sportType}/${distanceCategory}`
    );
    return response.data;
  },
  
  getInjuryRisks: async () => {
    const response = await api.get('/injury-risks');
    return response.data;
  },
  
  acknowledgeRisk: async (riskId: number) => {
    const response = await api.post(`/injury-risks/${riskId}/acknowledge`);
    return response.data;
  },
  
  resolveRisk: async (riskId: number) => {
    const response = await api.post(`/injury-risks/${riskId}/resolve`);
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
  
  analyzeInjuryRisk: async () => {
    const response = await api.post('/analyze-injury-risk');
    return response.data;
  },
};

export default api;

// lib/api.ts (в самый низ файла)

type ErrorDetailItem = {
  msg?: string;
};

type ErrorResponseData =
  | string
  | {
      message?: string;
      detail?: string | ErrorDetailItem[];
    };

export const extractErrorMessage = (error: unknown): string => {
  const data = (error as { response?: { data?: ErrorResponseData } }).response
    ?.data;

  if (!data) {
    return 'Network error. Please try again.';
  }

  if (typeof data === 'string') {
    return data;
  }

  if (typeof data.message === 'string') {
    return data.message;
  }

  const detail = data.detail;

  if (typeof detail === 'string') {
    return detail;
  }

  if (Array.isArray(detail)) {
    const messages = detail
      .map((d) => d.msg)
      .filter((msg): msg is string => Boolean(msg));

    if (messages.length > 0) {
      return messages.join('; ');
    }
  }

  return 'Request failed. Please check your data.';
};
