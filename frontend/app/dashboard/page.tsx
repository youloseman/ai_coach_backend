// app/dashboard/page.tsx
'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { isAuthenticated, logout, getAuthToken } from '@/lib/auth';
import { profileAPI, goalsAPI, coachAPI, stravaAPI, zonesAPI } from '@/lib/api';
import { PageHeader } from '@/components/PageHeader';
import type { AthleteProfile, Goal, WeeklyPlan, CoachZonesSummary, StravaActivity } from '@/types';
import { Activity, Calendar, HeartPulse, Target, ClipboardList, LogOut } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { ErrorAlert } from '@/components/ErrorAlert';
import { PerformanceChart } from '@/components/PerformanceChart';
import { ActivityCard } from '@/components/ActivityCard';
import { FormStatusCard } from '@/components/FormStatusCard';
import { RacePredictionCard } from '@/components/RacePredictionCard';
import { FatigueWarningBanner } from '@/components/FatigueWarningBanner';
import { InjuryRiskCard } from '@/components/InjuryRisk';
import { WeeklyPlanPreview } from '@/components/WeeklyPlanPreview';
import { WeeklyPlanCompact } from '@/components/WeeklyPlanCompact';
import { SegmentsSummary } from '@/components/SegmentsSummary';
import { NutritionQuickStats } from '@/components/NutritionQuickStats';
import { FitnessSummary } from '@/components/analytics/FitnessSummary';
import { PMCChart } from '@/components/charts/PMCChart';
import api from '@/lib/api';

type Status = 'idle' | 'loading' | 'success' | 'error';

type PMCDatapoint = {
  date: string;
  ctl: number;
  atl: number;
  tsb: number;
};

// Zone types removed - not used in current implementation

const getDaysToRace = (dateStr?: string | null): number | null => {
  if (!dateStr) return null;
  const race = new Date(dateStr);
  if (isNaN(race.getTime())) return null;

  const diff = Math.ceil((race.getTime() - Date.now()) / (1000 * 60 * 60 * 24));
  if (diff < 0) return 0;
  return diff;
};


export default function DashboardPage() {
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();
  const [status, setStatus] = useState<Status>('idle');
  const [profile, setProfile] = useState<AthleteProfile | null>(null);
  const [primaryGoal, setPrimaryGoal] = useState<Goal | null>(null);
  const [allGoals, setAllGoals] = useState<Goal[]>([]);

  // Состояния для быстрой обратной связи по действиям коуча
  const [planStatus, setPlanStatus] = useState<Status>('idle');
  const [currentAction, setCurrentAction] = useState<
    | 'weeklyPlan'
    | 'calendarExport'
    | 'multiWeekEmail'
    | 'weeklyReportEmail'
    | 'zonesAuto'
    | 'zonesManual'
    | null
  >(null);

  const [planSummary, setPlanSummary] = useState<{
    week_start_date: string;
    total_planned_hours: number;
  } | null>(null);
  const [planError, setPlanError] = useState<string | null>(null);
  const [calendarExport, setCalendarExport] = useState<{
    filename: string;
    total_workouts: number;
  } | null>(null);
  const [weeklyReportInfo, setWeeklyReportInfo] = useState<{
    week_start_date: string;
    readiness_score: number;
    readiness_label: string;
  } | null>(null);
  const [multiWeekEmailInfo, setMultiWeekEmailInfo] = useState<{
    num_weeks: number;
    start_date: string;
  } | null>(null);
  const [zones, setZones] = useState<CoachZonesSummary | null>(null);
  const [zonesMessage, setZonesMessage] = useState<string | null>(null);
  const [manualZones, setManualZones] = useState<{
    runType: string;
    runTime: string;
    bikeFtp: string;
    swimCss: string;
  }>({
    runType: '',
    runTime: '',
    bikeFtp: '',
    swimCss: '',
  });

  const queryClient = useQueryClient();

  const {
    data: timelineData = [],
    isLoading: timelineLoading,
  } = useQuery({
    queryKey: ['fitnessTimeline', 90],
    queryFn: async (): Promise<PMCDatapoint[]> => {
      const response = await api.get<{ timeline: PMCDatapoint[] | null }>(
        '/analytics/fitness_timeline?days=90'
      );
      return response.data.timeline || [];
    },
  });

  // Recent activities
  const {
    data: recentActivities,
  } = useQuery<StravaActivity[]>({
    queryKey: ['recentActivities'],
    queryFn: async () => {
      const response = await stravaAPI.getActivities(1, 5);
      return (response.activities || []) as StravaActivity[];
    },
    enabled: isAuthenticated(),
  });

  useEffect(() => {
    // Validate token on mount
    const token = getAuthToken();
    if (!token) {
      console.warn('No token found on dashboard mount - redirecting to login');
      router.replace('/login');
      return;
    }

    let isCancelled = false;

    const loadData = async () => {
      // Clear any stale state from previous user before loading
      setProfile(null);
      setPrimaryGoal(null);
      setAllGoals([]);
      setZones(null);
      setError(null);
      setStatus('idle');
      
      try {
        setStatus('loading');
        setError(null);

        // Always fetch fresh data from API
        const [profileData, primaryGoalData, goalsListData, zonesData] = await Promise.allSettled([
          profileAPI.get(),
          goalsAPI.getPrimary(),
          goalsAPI.list(false),
          coachAPI.getZones(),
        ]);

        if (isCancelled) return;

        if (profileData.status === 'fulfilled') {
          setProfile(profileData.value);
        } else {
          console.error('Failed to load profile:', profileData.reason);
        }

        if (primaryGoalData.status === 'fulfilled') {
          setPrimaryGoal(primaryGoalData.value);
        } else {
          console.warn('No primary goal yet or error loading it');
        }

        if (goalsListData.status === 'fulfilled') {
          setAllGoals(goalsListData.value);
        } else {
          console.error('Failed to load goals list:', goalsListData.reason);
        }

        if (zonesData.status === 'fulfilled') {
          setZones(zonesData.value as CoachZonesSummary);
        } else {
          console.warn('No training zones yet or error loading them');
        }

        setStatus('success');
      } catch (err: unknown) {
        if (isCancelled) return;
        console.error('Dashboard load error:', err);
        setError('Failed to load data. Please try again.');
        setStatus('error');
      }
    };

    loadData();

    return () => {
      isCancelled = true;
      // Clear state on unmount to prevent data leakage
      setProfile(null);
      setPrimaryGoal(null);
      setAllGoals([]);
      setZones(null);
    };
  }, [router]);

  const [daysToRace, setDaysToRace] = useState<number | null>(null);

  // Calculate days to race only on client side to avoid hydration mismatch
  useEffect(() => {
    if (primaryGoal?.race_date) {
      setDaysToRace(getDaysToRace(primaryGoal.race_date));
    } else {
      setDaysToRace(null);
    }
  }, [primaryGoal?.race_date]);

  const avgHours12w = profile?.auto_avg_hours_last_12_weeks;
  const availableHours = profile?.available_hours_per_week;

  const handleLogout = () => {
    logout();
  };

  const getCurrentWeekStartISO = (): string => {
    const today = new Date();
    const day = today.getDay(); // 0 (Sun) - 6 (Sat)
    const diffToMonday = day === 0 ? -6 : 1 - day;
    const monday = new Date(today);
    monday.setDate(today.getDate() + diffToMonday);
    return monday.toISOString().slice(0, 10);
  };

  const handleGenerateWeekPlan = async () => {
    if (!profile || !primaryGoal) {
      setPlanError('Please set profile and primary goal first.');
      return;
    }

    try {
      setPlanStatus('loading');
      setCurrentAction('weeklyPlan');
      setPlanError(null);
      setCalendarExport(null);
      setWeeklyReportInfo(null);
      setMultiWeekEmailInfo(null);

      const weekStart = getCurrentWeekStartISO();
      const availableHours =
        profile.available_hours_per_week > 0
          ? profile.available_hours_per_week
          : 8;

      const payload = {
        goal: {
          main_goal_type: primaryGoal.goal_type,
          main_goal_target_time: primaryGoal.target_time || '4:30',
          main_goal_race_date: primaryGoal.race_date,
          secondary_goals: [],
          comments: undefined,
        },
        week_start_date: weekStart,
        available_hours_per_week: availableHours,
        notes: undefined,
      };

      const plan: WeeklyPlan = await coachAPI.generateWeeklyPlan(payload);

      setPlanSummary({
        week_start_date: plan.week_start_date,
        total_planned_hours: plan.total_planned_hours,
      });
      // Refresh weekly plan previews on dashboard
      await queryClient.invalidateQueries({ queryKey: ['weeklyPlanPreview'] });
      setPlanStatus('success');
    } catch (err: unknown) {
      console.error('Failed to generate weekly plan:', err);
      setPlanError('Failed to generate weekly plan. Please try again.');
      setPlanStatus('error');
    } finally {
      setCurrentAction(null);
    }
  };

  const handleExportWeekPlanToCalendar = async () => {
    if (!profile || !primaryGoal) {
      setPlanError('Please set profile and primary goal first.');
      return;
    }

    try {
      setPlanStatus('loading');
      setCurrentAction('calendarExport');
      setPlanError(null);
      setWeeklyReportInfo(null);
      setMultiWeekEmailInfo(null);

      const weekStart = getCurrentWeekStartISO();
      const availableHours =
        profile.available_hours_per_week > 0
          ? profile.available_hours_per_week
          : 8;

      const payload = {
        goal: {
          main_goal_type: primaryGoal.goal_type,
          main_goal_target_time: primaryGoal.target_time || '4:30',
          main_goal_race_date: primaryGoal.race_date,
          secondary_goals: [],
          comments: undefined,
        },
        week_start_date: weekStart,
        available_hours_per_week: availableHours,
        notes: undefined,
      };

      const exportResult = await coachAPI.exportWeeklyPlanToCalendar(payload);

      setCalendarExport({
        filename: exportResult.filename,
        total_workouts: exportResult.total_workouts,
      });

      if (exportResult.download_url && typeof window !== 'undefined') {
        window.open(exportResult.download_url, '_blank');
      }

      // Weekly plan might be updated as part of export; refresh preview as well
      await queryClient.invalidateQueries({ queryKey: ['weeklyPlanPreview'] });

      setPlanStatus('success');
    } catch (err: unknown) {
      console.error('Failed to export weekly plan to calendar:', err);
      setPlanError('Failed to export weekly plan to calendar.');
      setPlanStatus('error');
    } finally {
      setCurrentAction(null);
    }
  };

  const handleSendMultiWeekPlanEmail = async () => {
    if (!profile || !primaryGoal) {
      setPlanError('Please set profile and primary goal first.');
      return;
    }

    try {
      setPlanStatus('loading');
      setCurrentAction('multiWeekEmail');
      setPlanError(null);
      setWeeklyReportInfo(null);
      setMultiWeekEmailInfo(null);

      const startDate = getCurrentWeekStartISO();
      const baseHours =
        profile.available_hours_per_week > 0
          ? profile.available_hours_per_week
          : 8;
      const peakHours = Math.max(baseHours + 2, baseHours * 1.3);

      const payload = {
        goal: {
          main_goal_type: primaryGoal.goal_type,
          main_goal_target_time: primaryGoal.target_time || '4:30',
          main_goal_race_date: primaryGoal.race_date,
          secondary_goals: [],
          comments: undefined,
        },
        start_date: startDate,
        num_weeks: 12,
        base_hours_per_week: baseHours,
        peak_hours_per_week: peakHours,
        notes: undefined,
      };

      const result = await coachAPI.sendMultiWeekPlanEmail(payload);

      if (result.calendar_download_url && typeof window !== 'undefined') {
        window.open(result.calendar_download_url, '_blank');
      }

      setMultiWeekEmailInfo({
        num_weeks: result.num_weeks,
        start_date: result.start_date,
      });

      setPlanStatus('success');
    } catch (err: unknown) {
      console.error('Failed to send multi-week plan email:', err);
      setPlanError('Failed to send multi-week plan email.');
      setPlanStatus('error');
    } finally {
      setCurrentAction(null);
    }
  };

  const handleSendWeeklyReportEmail = async () => {
    if (!profile || !primaryGoal) {
      setPlanError('Please set profile and primary goal first.');
      return;
    }

    try {
      setPlanStatus('loading');
      setCurrentAction('weeklyReportEmail');
      setPlanError(null);

      const weekStart = getCurrentWeekStartISO();
      const availableHours =
        profile.available_hours_per_week > 0
          ? profile.available_hours_per_week
          : 8;

      const payload = {
        goal: {
          main_goal_type: primaryGoal.goal_type,
          main_goal_target_time: primaryGoal.target_time || '4:30',
          main_goal_race_date: primaryGoal.race_date,
          secondary_goals: [],
          comments: undefined,
        },
        week_start_date: weekStart,
        available_hours_per_week: availableHours,
        notes: undefined,
        // progress_weeks и subject можно не указывать — есть дефолты на бэке
      };

      const result = await coachAPI.sendWeeklyReportEmail(payload);

      setWeeklyReportInfo({
        week_start_date: result.week_start_date,
        readiness_score: result.readiness_score,
        readiness_label: result.readiness_label,
      });

      // If email failed, surface backend message to the user
      if (result.email_sent === false && result.email_error) {
        setPlanError(
          `Weekly report generated, but email sending failed: ${result.email_error}`,
        );
      } else {
        setPlanError(null);
      }

      // Weekly report also generates and saves a plan; refresh preview
      await queryClient.invalidateQueries({ queryKey: ['weeklyPlanPreview'] });

      setPlanStatus('success');
    } catch (err: unknown) {
      console.error('Failed to send weekly report email:', err);
      setPlanError('Failed to send weekly report email.');
      setPlanStatus('error');
    } finally {
      setCurrentAction(null);
    }
  };

  const handleAutoCalcZone = async (sport: 'run' | 'bike' | 'swim') => {
    try {
      setPlanStatus('loading');
      setCurrentAction('zonesAuto');
      const result = await zonesAPI.calculate(sport);
      setZones({
        zones_last_updated: result.zones_last_updated,
        run: result.run,
        bike: result.bike,
        swim: result.swim,
      });
      setZonesMessage(`Updated ${sport} zones automatically.`);
    } catch (err: unknown) {
      console.error('Failed to auto-calc zones:', err);
      setPlanError('Failed to calculate zones. Please try again.');
      setPlanStatus('error');
    } finally {
      setCurrentAction(null);
    }
  };

  const parseTimeToSeconds = (timeStr: string): number | null => {
    const parts = timeStr.split(':').map((p) => p.trim());
    if (parts.length < 2 || parts.length > 3) {
      return null;
    }
    const nums = parts.map((p) => Number(p));
    if (nums.some((n) => Number.isNaN(n) || n < 0)) {
      return null;
    }
    if (nums.length === 2) {
      const [mm, ss] = nums;
      return mm * 60 + ss;
    }
    const [hh, mm, ss] = nums;
    return hh * 3600 + mm * 60 + ss;
  };

  const handleSaveManualZones = async () => {
    try {
      setPlanStatus('loading');
      setPlanError(null);
      setZonesMessage(null);
      setCurrentAction('zonesManual');

      let run_race_time_seconds: number | undefined;
      let run_race_distance_km: number | undefined;
      let run_race_type: string | undefined;

      if (manualZones.runType && manualZones.runTime) {
        const seconds = parseTimeToSeconds(manualZones.runTime);
        if (seconds == null) {
          setPlanError('Invalid run time format. Use MM:SS or HH:MM:SS.');
          setPlanStatus('error');
          return;
        }
        run_race_time_seconds = seconds;
        run_race_type = manualZones.runType;
        if (manualZones.runType === '5K') run_race_distance_km = 5;
        else if (manualZones.runType === '10K') run_race_distance_km = 10;
        else if (manualZones.runType === 'HM') run_race_distance_km = 21.1;
        else if (manualZones.runType === 'Marathon') run_race_distance_km = 42.2;
      }

      let bike_ftp_watts: number | undefined;
      if (manualZones.bikeFtp) {
        const ftp = Number(manualZones.bikeFtp);
        if (Number.isNaN(ftp) || ftp <= 0) {
          setPlanError('Bike FTP must be a positive number.');
          setPlanStatus('error');
          return;
        }
        bike_ftp_watts = ftp;
      }

      let swim_css_pace_per_100m: number | undefined;
      if (manualZones.swimCss) {
        const seconds = parseTimeToSeconds(manualZones.swimCss);
        if (seconds == null) {
          setPlanError('Invalid swim CSS format. Use MM:SS.');
          setPlanStatus('error');
          return;
        }
        swim_css_pace_per_100m = seconds;
      }

      const payload = {
        run_race_type,
        run_race_time_seconds,
        run_race_distance_km,
        bike_ftp_watts,
        swim_css_pace_per_100m,
      };

      const result = await coachAPI.calculateZonesManual(payload);

      setZones({
        zones_last_updated: result.profile.zones_last_updated,
        run: result.profile.training_zones_run,
        bike: result.profile.training_zones_bike,
        swim: result.profile.training_zones_swim,
      });

      setZonesMessage('Zones were updated from manual input.');

      setPlanStatus('success');
    } catch (err: unknown) {
      console.error('Failed to calculate training zones from manual input:', err);
      setPlanError('Failed to calculate training zones from manual input.');
      setPlanStatus('error');
    } finally {
      setCurrentAction(null);
    }
  };

  if (status === 'loading' && !profile && !primaryGoal) {
    return (
      <div className="min-h-screen bg-slate-950 text-slate-50 flex items-center justify-center">
        <div className="text-slate-400">Loading your dashboard...</div>
      </div>
    );
  }

  if (status === 'error' && !profile && !primaryGoal) {
    return (
      <div className="min-h-screen bg-slate-950 text-slate-50 flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <div className="text-red-400">{error}</div>
          <button
            onClick={() => router.refresh()}
            className="px-4 py-2 rounded-md bg-slate-800 hover:bg-slate-700 text-sm"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-50">
      <PageHeader
        sectionLabel="AI Triathlon Coach"
        title="Dashboard"
        rightSlot={
          <>
            {profile?.primary_discipline && (
              <span className="text-xs px-3 py-1 rounded-full bg-slate-900 border border-slate-700">
                {profile.primary_discipline}
              </span>
            )}
            <button
              type="button"
              onClick={() => router.push('/coach')}
              className="text-xs text-slate-400 hover:text-slate-100"
            >
              Coach profile
            </button>
            <button
              type="button"
              onClick={handleLogout}
              className="inline-flex items-center gap-1 text-xs text-slate-400 hover:text-slate-100"
            >
              <LogOut className="w-4 h-4" />
              Logout
            </button>
          </>
        }
      />

      <main className="max-w-6xl mx-auto px-4 py-6 space-y-6">
        <ErrorAlert error={error} onDismiss={() => setError(null)} />

        {/* Fatigue Warning */}
        <FatigueWarningBanner />

        {/* Performance chart */}
        <section className="bg-slate-900/60 border border-slate-800 rounded-xl p-4">
          <h2 className="text-sm font-semibold mb-2">
            Performance Management Chart
          </h2>
          <p className="text-xs text-slate-400 mb-3">
            Fitness (CTL), fatigue (ATL) and form (TSB) over time, based on your
            Strava history.
          </p>
          {timelineLoading ? (
            <div className="flex items-center justify-center h-64">
              <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-sky-500" />
            </div>
          ) : (
            <PerformanceChart data={timelineData} />
          )}
        </section>

        {/* Top stats */}
        <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatsCard
            title="Avg Hours (12w)"
            value={
              avgHours12w != null
                ? avgHours12w.toFixed(1)
                : '0.0'
            }
            subtitle="hours/week"
            icon={Activity}
            color="blue"
          />

          <StatsCard
            title="Available Hours"
            value={
              availableHours != null
                ? availableHours.toFixed(1)
                : '8.0'
            }
            subtitle="hours/week"
            icon={Calendar}
            color="purple"
          />

          <StatsCard
            title="Primary Race"
            value={primaryGoal?.race_name || 'Not set'}
            subtitle={primaryGoal?.goal_type || 'Tap to set in Goals'}
            icon={Target}
            color="amber"
          />

          <StatsCard
            title="Days to Race"
            value={
              typeof daysToRace === 'number'
                ? daysToRace.toString()
                : '--'
            }
            subtitle={
              typeof daysToRace === 'number'
                ? 'days to go'
                : 'no race date yet'
            }
            icon={HeartPulse}
            color="emerald"
          />
        </section>

        {/* Fitness Summary (PMC Metrics) */}
        <section className="grid grid-cols-1 gap-4">
          <FitnessSummary />
        </section>

        {/* Form Status, Injury Risk, Race Predictions & Weekly Plan */}
        <section className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-4 gap-4">
          <FormStatusCard />
          <InjuryRiskCard />
          <RacePredictionCard />
          <div className="lg:hidden xl:block">
            <WeeklyPlanCompact />
          </div>
        </section>

        {/* PMC Chart */}
        <section className="grid grid-cols-1 gap-4">
          <PMCChart />
        </section>

        {/* Weekly plan preview - full width on mobile/tablet */}
        <section className="grid grid-cols-1 gap-4 lg:hidden xl:hidden">
          <WeeklyPlanPreview />
        </section>

        {/* Primary race card */}
        <section className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <div className="lg:col-span-2 bg-slate-900/60 border border-slate-800 rounded-xl p-4">
            <div className="flex items-center gap-2 mb-3">
              <Target className="w-5 h-5 text-amber-400" />
              <h2 className="text-sm font-semibold">Primary Goal</h2>
            </div>

            {primaryGoal ? (
              <div className="space-y-2 text-sm text-slate-200">
                <div className="flex flex-wrap gap-2 items-center">
                  <span className="font-medium">{primaryGoal.race_name}</span>
                  {primaryGoal.goal_type && (
                    <span className="px-2 py-0.5 rounded-full bg-slate-800 text-xs text-slate-300">
                      {primaryGoal.goal_type}
                    </span>
                  )}
                  {primaryGoal.race_date && (
                    <span className="text-xs text-slate-400">
                      {new Date(primaryGoal.race_date).toLocaleDateString()}
                    </span>
                  )}
                </div>

                {primaryGoal.target_time && (
                  <div className="text-xs text-slate-400">
                    Target time:{' '}
                    <span className="text-slate-100">
                      {primaryGoal.target_time}
                    </span>
                  </div>
                )}

                {typeof daysToRace === 'number' && (
                  <div className="text-xs text-slate-400">
                    {daysToRace === 0
                      ? 'Race day is today or already passed'
                      : `${daysToRace} days to go`}
                  </div>
                )}
              </div>
            ) : (
              <div className="text-xs text-slate-400">
                You don&apos;t have a primary race yet. Set it up on the{' '}
                <button
                  onClick={() => router.push('/goals')}
                  className="text-amber-400 hover:underline"
                >
                  Goals
                </button>{' '}
                page.
              </div>
            )}
          </div>

          <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4">
            <div className="flex items-center gap-2 mb-3">
              <ClipboardList className="w-5 h-5 text-sky-400" />
              <h2 className="text-sm font-semibold">Quick Actions</h2>
            </div>
            <div className="flex flex-col gap-2 text-xs">
              <div className="flex flex-col gap-1">
                <button
                  className="w-full px-3 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-left"
                  onClick={handleGenerateWeekPlan}
                  disabled={planStatus === 'loading'}
                >
                  {planStatus === 'loading' && currentAction === 'weeklyPlan'
                    ? "Generating this week's plan..."
                    : "Generate this week's plan"}
                </button>
                <button
                  className="w-full px-3 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-left text-[11px]"
                  onClick={handleExportWeekPlanToCalendar}
                  disabled={planStatus === 'loading'}
                >
                  {planStatus === 'loading' && currentAction === 'calendarExport'
                    ? "Exporting this week's plan..."
                    : "Export this week's plan to calendar (.ics)"}
                </button>
                <button
                  className="w-full px-3 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-left text-[11px]"
                  onClick={handleSendMultiWeekPlanEmail}
                  disabled={planStatus === 'loading'}
                >
                  {planStatus === 'loading' && currentAction === 'multiWeekEmail'
                    ? 'Sending 12-week plan...'
                    : 'Send 12-week plan to email'}
                </button>
                <button
                  className="w-full px-3 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-left text-[11px]"
                  onClick={handleSendWeeklyReportEmail}
                  disabled={planStatus === 'loading'}
                >
                  {planStatus === 'loading' && currentAction === 'weeklyReportEmail'
                    ? 'Sending weekly report...'
                    : 'Send weekly report email'}
                </button>
              </div>
              <button
                className="w-full px-3 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-left"
                onClick={() => router.push('/goals')}
              >
                Update race goals
              </button>
              <NutritionQuickStats />
              {planError && (
                <div className="text-[11px] text-red-400">{planError}</div>
              )}
              {planSummary && (
                <div className="text-[11px] text-slate-400">
                  Plan for week starting{' '}
                  <span className="text-slate-200">
                    {planSummary.week_start_date}
                  </span>{' '}
                  with{' '}
                  <span className="text-slate-200">
                    {planSummary.total_planned_hours.toFixed(1)} h
                  </span>{' '}
                  generated.
                </div>
              )}
              {calendarExport && (
                <div className="text-[11px] text-slate-400">
                  Calendar file{' '}
                  <span className="text-slate-200">
                    {calendarExport.filename}
                  </span>{' '}
                  prepared (
                  <span className="text-slate-200">
                    {calendarExport.total_workouts}
                  </span>{' '}
                  workouts).
                </div>
              )}
              {multiWeekEmailInfo && (
                <div className="text-[11px] text-slate-400">
                  {multiWeekEmailInfo.num_weeks}-week plan starting{' '}
                  <span className="text-slate-200">
                    {multiWeekEmailInfo.start_date}
                  </span>{' '}
                  has been emailed.
                </div>
              )}
              {weeklyReportInfo && (
                <div className="text-[11px] text-slate-400">
                  Weekly report for{' '}
                  <span className="text-slate-200">
                    {weeklyReportInfo.week_start_date}
                  </span>{' '}
                  sent. Readiness:{' '}
                  <span className="text-slate-200">
                    {weeklyReportInfo.readiness_score.toFixed(1)} / 100 (
                    {weeklyReportInfo.readiness_label})
                  </span>
                  .
                </div>
              )}
            </div>
          </div>

          <SegmentsSummary />
        </section>

        {/* All goals overview */}
        {allGoals.length > 0 && (
          <section className="bg-slate-900/60 border border-slate-800 rounded-xl p-4">
            <div className="flex items-center gap-2 mb-3">
              <Target className="w-5 h-5 text-sky-400" />
              <h2 className="text-sm font-semibold">All goals</h2>
            </div>
            <div className="space-y-2 text-xs">
              {allGoals.map((g) => {
                const d = getDaysToRace(g.race_date);
                return (
                  <div
                    key={g.id}
                    className="flex flex-wrap justify-between gap-2 border border-slate-800 rounded-lg px-3 py-2 bg-slate-950/60"
                  >
                    <div>
                      <div className="font-medium text-slate-100">
                        {g.race_name || 'Unnamed race'}{' '}
                        {g.is_primary && (
                          <span className="ml-1 text-[10px] px-1.5 py-0.5 rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/40">
                            primary
                          </span>
                        )}
                      </div>
                      <div className="text-slate-400">
                        {g.goal_type && <span>{g.goal_type} · </span>}
                        {g.race_date && (
                          <span>{new Date(g.race_date).toLocaleDateString()}</span>
                        )}
                      </div>
                    </div>
                    <div className="text-right text-slate-400">
                      {g.target_time != null && (
                        <div>Target: {g.target_time}</div>
                      )}
                      {typeof d === 'number' && (
                        <div className="text-[11px]">
                          {d === 0 ? 'today / passed' : `${d} days to go`}
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </section>
        )}

        {/* Recent Activities */}
        {recentActivities && recentActivities.length > 0 && (
          <section className="bg-slate-900/60 border border-slate-800 rounded-xl p-4">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <Activity className="w-5 h-5 text-sky-400" />
                <h2 className="text-sm font-semibold">Recent Activities</h2>
              </div>
              <span className="text-xs text-slate-500">
                Last 5 workouts from Strava
              </span>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              {recentActivities.map((activity: StravaActivity) => (
                <ActivityCard key={activity.id} activity={activity} />
              ))}
            </div>
          </section>
        )}

        {/* Training zones summary + manual input */}
        <section className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <HeartPulse className="w-5 h-5 text-emerald-400" />
              <h2 className="text-sm font-semibold">Training Zones</h2>
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-2 text-xs">
            {(['run', 'bike', 'swim'] as const).map((sport) => (
              <button
                key={sport}
                className="px-3 py-2 rounded-md bg-slate-800 hover:bg-slate-700 text-left text-[11px] border border-slate-700"
                onClick={() => handleAutoCalcZone(sport)}
                disabled={planStatus === 'loading'}
              >
                {planStatus === 'loading' && currentAction === 'zonesAuto'
                  ? `Calculating ${sport} zones...`
                  : `🔄 Auto Calculate (${sport})`}
              </button>
            ))}
          </div>
          <div className="text-xs text-slate-400 space-y-2">
            <div>
              {zones?.zones_last_updated ? (
                <>
                  Last updated:{' '}
                  <span className="text-slate-200">
                    {new Date(zones.zones_last_updated).toLocaleDateString()}
                  </span>
                </>
              ) : (
                'No training zones calculated yet.'
              )}
            </div>
            {zonesMessage && (
              <div className="text-[11px] text-emerald-300">{zonesMessage}</div>
            )}
          </div>

          <div className="mt-2 grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
            {/* Run zones */}
            <div className="bg-slate-950 border border-slate-800 rounded-lg p-3 space-y-2">
              <div className="text-[11px] font-semibold text-emerald-300 flex items-center gap-1">
                🏃 Run zones
              </div>
              <table className="w-full text-[11px] text-slate-300 border-collapse">
                <tbody>
                  {[
                    ['Z1 (Recovery)', '5:30-6:00 min/km', '120-140 bpm'],
                    ['Z2 (Endurance)', '5:00-5:30 min/km', '140-155 bpm'],
                    ['Z3 (Tempo)', '4:30-5:00 min/km', '155-165 bpm'],
                    ['Z4 (Threshold)', '4:00-4:30 min/km', '165-175 bpm'],
                    ['Z5 (VO2max)', '3:30-4:00 min/km', '175+ bpm'],
                  ].map(([label, pace, hr]) => (
                    <tr key={label}>
                      <td className="pr-2 py-1 text-slate-500 uppercase">{label}</td>
                      <td className="pr-2 py-1">{pace}</td>
                      <td className="py-1 text-slate-500">{hr}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Bike zones */}
            <div className="bg-slate-950 border border-slate-800 rounded-lg p-3 space-y-2">
              <div className="text-[11px] font-semibold text-emerald-300 flex items-center gap-1">
                🚴 Bike zones (HR)
              </div>
              <table className="w-full text-[11px] text-slate-300 border-collapse">
                <tbody>
                  {[
                    ['Z1 (Recovery)', '120-140 bpm'],
                    ['Z2 (Endurance)', '140-155 bpm'],
                    ['Z3 (Tempo)', '155-165 bpm'],
                    ['Z4 (Threshold)', '165-175 bpm'],
                    ['Z5 (VO2max)', '175+ bpm'],
                  ].map(([label, hr]) => (
                    <tr key={label}>
                      <td className="pr-2 py-1 text-slate-500 uppercase">{label}</td>
                      <td className="py-1 text-slate-500">{hr}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Swim zones */}
            <div className="bg-slate-950 border border-slate-800 rounded-lg p-3 space-y-2">
              <div className="text-[11px] font-semibold text-emerald-300 flex items-center gap-1">
                🏊 Swim zones
              </div>
              <table className="w-full text-[11px] text-slate-300 border-collapse">
                <tbody>
                  {[
                    ['Z1 (Recovery)', '2:10 /100m'],
                    ['Z2 (Endurance)', '2:00 /100m'],
                    ['Z3 (Tempo)', '1:50 /100m'],
                    ['Z4 (Threshold)', '1:40 /100m'],
                    ['Z5 (VO2max)', '1:30 /100m'],
                  ].map(([label, pace]) => (
                    <tr key={label}>
                      <td className="pr-2 py-1 text-slate-500 uppercase">{label}</td>
                      <td className="py-1 text-slate-500">{pace}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="mt-3 border-t border-slate-800 pt-3 text-xs text-slate-300 space-y-2">
            <div className="flex items-center justify-between">
              <h3 className="text-[13px] font-semibold">Manual input</h3>
              <span className="text-[11px] text-slate-500">
                Use any subset (run / bike / swim)
              </span>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div className="space-y-1">
                <label className="block text-[11px] text-slate-400">
                  Run race type
                </label>
                <select
                  value={manualZones.runType}
                  onChange={(e) =>
                    setManualZones((prev) => ({
                      ...prev,
                      runType: e.target.value,
                    }))
                  }
                  className="w-full rounded-md bg-slate-950 border border-slate-700 px-2 py-1.5 text-xs outline-none focus:border-sky-500"
                >
                  <option value="">—</option>
                  <option value="5K">5K</option>
                  <option value="10K">10K</option>
                  <option value="HM">Half marathon</option>
                  <option value="Marathon">Marathon</option>
                </select>
                <label className="block text-[11px] text-slate-400 mt-1">
                  Run race time (MM:SS or HH:MM:SS)
                </label>
                <input
                  type="text"
                  value={manualZones.runTime}
                  onChange={(e) =>
                    setManualZones((prev) => ({
                      ...prev,
                      runTime: e.target.value,
                    }))
                  }
                  placeholder="00:40:00"
                  className="w-full rounded-md bg-slate-950 border border-slate-700 px-2 py-1.5 text-xs outline-none focus:border-sky-500"
                />
              </div>

              <div className="space-y-1">
                <label className="block text-[11px] text-slate-400">
                  Bike FTP (watts)
                </label>
                <input
                  type="number"
                  value={manualZones.bikeFtp}
                  onChange={(e) =>
                    setManualZones((prev) => ({
                      ...prev,
                      bikeFtp: e.target.value,
                    }))
                  }
                  placeholder="250"
                  className="w-full rounded-md bg-slate-950 border border-slate-700 px-2 py-1.5 text-xs outline-none focus:border-sky-500"
                />
              </div>

              <div className="space-y-1">
                <label className="block text-[11px] text-slate-400">
                  Swim CSS (MM:SS per 100m)
                </label>
                <input
                  type="text"
                  value={manualZones.swimCss}
                  onChange={(e) =>
                    setManualZones((prev) => ({
                      ...prev,
                      swimCss: e.target.value,
                    }))
                  }
                  placeholder="01:45"
                  className="w-full rounded-md bg-slate-950 border border-slate-700 px-2 py-1.5 text-xs outline-none focus:border-sky-500"
                />
              </div>
            </div>
            <div className="flex justify-end">
              <button
                type="button"
                onClick={handleSaveManualZones}
                disabled={planStatus === 'loading'}
                className="px-4 py-1.5 rounded-md bg-sky-600 hover:bg-sky-500 disabled:opacity-50 text-[11px] font-medium"
              >
                {planStatus === 'loading' && currentAction === 'zonesManual'
                  ? 'Saving zones...'
                  : 'Save zones from manual input'}
              </button>
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}

type StatsCardProps = {
  title: string;
  value: string;
  subtitle?: string;
  icon: LucideIcon;
  color?: 'blue' | 'purple' | 'amber' | 'emerald';
};

function StatsCard({ title, value, subtitle, icon: Icon, color = 'blue' }: StatsCardProps) {
  const colorClassMap: Record<NonNullable<StatsCardProps['color']>, string> = {
    blue: 'text-sky-400',
    purple: 'text-violet-400',
    amber: 'text-amber-400',
    emerald: 'text-emerald-400',
  };

  const iconColor = colorClassMap[color];

  return (
    <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 flex flex-col justify-between">
      <div className="flex items-center justify-between mb-2">
        <div className="text-xs font-medium text-slate-400">{title}</div>
        <Icon className={`w-4 h-4 ${iconColor}`} />
      </div>
      <div className="text-2xl font-semibold">{value}</div>
      {subtitle && <div className="mt-1 text-xs text-slate-500">{subtitle}</div>}
    </div>
  );
}
