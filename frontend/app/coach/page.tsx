'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { isAuthenticated, getAuthToken } from '@/lib/auth';
import { coachAPI, stravaAPI, API_URL } from '@/lib/api';
import { PageHeader } from '@/components/PageHeader';
import type { CoachProfile, CoachLevel, StravaStatus } from '@/types';

type Status = 'idle' | 'loading' | 'success' | 'error';

const LEVEL_OPTIONS: { value: CoachLevel; label: string }[] = [
  { value: 'beginner', label: 'Beginner' },
  { value: 'intermediate', label: 'Intermediate' },
  { value: 'advanced', label: 'Advanced' },
  { value: 'high_performance', label: 'High performance' },
];

export default function CoachProfilePage() {
  const router = useRouter();
  const [status, setStatus] = useState<Status>('idle');
  const [saveStatus, setSaveStatus] = useState<Status>('idle');
  const [error, setError] = useState<string | null>(null);
  const [coachProfile, setCoachProfile] = useState<CoachProfile | null>(null);
  const [stravaStatus, setStravaStatus] = useState<StravaStatus | null>(null);

  useEffect(() => {
    // Validate token on mount
    const token = getAuthToken();
    if (!token) {
      router.replace('/login');
      return;
    }

    // Clear stale state
    setCoachProfile(null);
    setStravaStatus(null);
    setError(null);
    setStatus('idle');

    let cancelled = false;

    const loadProfileAndStrava = async () => {
      try {
        setStatus('loading');
        setError(null);

        // Always fetch fresh data
        const [profileResult, stravaResult] = await Promise.allSettled([
          coachAPI.getProfile(),
          stravaAPI.getStatus(),
        ]);

        if (cancelled) return;

        if (profileResult.status === 'fulfilled') {
          setCoachProfile(profileResult.value);
        } else {
          console.error('Failed to load coach profile:', profileResult.reason);
          setError('Failed to load coach profile.');
        }

        if (stravaResult.status === 'fulfilled') {
          setStravaStatus(stravaResult.value);
        } else {
          console.error('Failed to load Strava status:', stravaResult.reason);
        }

        setStatus('success');
      } catch (err: unknown) {
        if (cancelled) return;
        console.error('Failed to load coach profile or Strava status:', err);
        setError('Failed to load coach profile.');
        setStatus('error');
      }
    };

    loadProfileAndStrava();

    return () => {
      cancelled = true;
      // Clear state on unmount
      setCoachProfile(null);
      setStravaStatus(null);
    };
  }, [router]);

  const handleFieldChange = (
    field: keyof CoachProfile,
    value: string | number | null
  ) => {
    setCoachProfile((prev) => {
      if (!prev) return prev;
      return { ...prev, [field]: value };
    });
  };

  const handleSave = async () => {
    if (!coachProfile) return;

    try {
      setSaveStatus('loading');
      setError(null);
      const updated = await coachAPI.updateProfile(coachProfile);
      setCoachProfile(updated);
      setSaveStatus('success');
    } catch (err: unknown) {
      console.error('Failed to save coach profile:', err);
      setError('Failed to save coach profile.');
      setSaveStatus('error');
    }
  };

  const handleAutoFromHistory = async () => {
    try {
      setSaveStatus('loading');
      setError(null);
      const updated = await coachAPI.autoUpdateProfileFromHistory();
      setCoachProfile(updated);
      setSaveStatus('success');
    } catch (err: unknown) {
      console.error('Failed to auto-update profile from history:', err);
      setError('Failed to auto-update profile from history.');
      setSaveStatus('error');
    }
  };

  if (status === 'loading' && !coachProfile) {
    return (
      <div className="min-h-screen bg-slate-950 text-slate-50 flex items-center justify-center">
        <div className="text-slate-400">Loading coach profile...</div>
      </div>
    );
  }

  if (status === 'error' && !coachProfile) {
    return (
      <div className="min-h-screen bg-slate-950 text-slate-50 flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <div className="text-red-400">{error}</div>
          <button
            type="button"
            onClick={() => router.refresh()}
            className="px-4 py-2 rounded-md bg-slate-800 hover:bg-slate-700 text-sm"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (!coachProfile) {
    return null;
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-50">
      <PageHeader
        sectionLabel="Coach"
        title="Coach profile"
        containerWidthClassName="max-w-4xl"
        rightSlot={
          <button
            type="button"
            onClick={() => router.push('/dashboard')}
            className="text-xs text-slate-400 hover:text-slate-100"
          >
            Back to dashboard
          </button>
        }
      />

      <main className="max-w-4xl mx-auto px-4 py-6 space-y-6">
        {error && (
          <div className="text-xs text-red-400 bg-red-950/40 border border-red-900 rounded-md px-3 py-2">
            {error}
          </div>
        )}

        {/* Strava connection overview */}
        <section className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 space-y-2 text-sm">
          <div className="flex items-center justify-between mb-1">
            <h2 className="text-sm font-semibold">Strava connection</h2>
            <a
              href={`${API_URL}/`}
              target="_blank"
              rel="noreferrer"
              className="px-3 py-1.5 rounded-md bg-slate-800 hover:bg-slate-700 text-[11px]"
            >
              {stravaStatus?.connected ? 'Reconnect Strava' : 'Connect Strava'}
            </a>
          </div>
          <p className="text-xs text-slate-400">
            Strava history is used to auto-fill your profile (streaks, average
            hours, discipline mix) and training zones. After connecting, use
            the buttons below and on the dashboard to refresh data.
          </p>
          <div className="text-xs text-slate-300">
            {stravaStatus?.connected ? (
              <>
                Connected
                {stravaStatus.athlete_name && (
                  <>
                    {' '}
                    as{' '}
                    <span className="text-slate-100">
                      {stravaStatus.athlete_name}
                    </span>
                  </>
                )}
                .
              </>
            ) : (
              'Not connected to Strava yet.'
            )}
          </div>
        </section>

        {/* Manual fields */}
        <section className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 space-y-3 text-sm">
          <div className="flex items-center justify-between mb-1">
            <h2 className="text-sm font-semibold">Manual settings</h2>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={handleAutoFromHistory}
                disabled={saveStatus === 'loading'}
                className="px-3 py-1.5 rounded-md bg-slate-800 hover:bg-slate-700 text-[11px]"
              >
                Auto-fill from Strava history
              </button>
              <button
                type="button"
                onClick={handleSave}
                disabled={saveStatus === 'loading'}
                className="px-4 py-1.5 rounded-md bg-sky-600 hover:bg-sky-500 disabled:opacity-50 text-[11px] font-medium"
              >
                {saveStatus === 'loading' ? 'Saving...' : 'Save'}
              </button>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="block text-xs text-slate-400 mb-1">
                Level
              </label>
              <select
                value={coachProfile.level}
                onChange={(e) =>
                  handleFieldChange('level', e.target.value as CoachLevel)
                }
                className="w-full rounded-md bg-slate-950 border border-slate-700 px-2 py-1.5 text-sm outline-none focus:border-sky-500"
              >
                {LEVEL_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs text-slate-400 mb-1">
                Max hours per week (peak)
              </label>
              <input
                type="number"
                value={coachProfile.max_hours_per_week}
                onChange={(e) =>
                  handleFieldChange(
                    'max_hours_per_week',
                    Number(e.target.value || 0)
                  )
                }
                min={0}
                step={0.5}
                className="w-full rounded-md bg-slate-950 border border-slate-700 px-2 py-1.5 text-sm outline-none focus:border-sky-500"
              />
            </div>

            <div>
              <label className="block text-xs text-slate-400 mb-1">
                Age
              </label>
              <input
                type="number"
                value={coachProfile.age ?? ''}
                onChange={(e) =>
                  handleFieldChange(
                    'age',
                    e.target.value === '' ? null : Number(e.target.value)
                  )
                }
                min={0}
                className="w-full rounded-md bg-slate-950 border border-slate-700 px-2 py-1.5 text-sm outline-none focus:border-sky-500"
              />
            </div>

            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="block text-xs text-slate-400 mb-1">
                  Height (cm)
                </label>
                <input
                  type="number"
                  value={coachProfile.height_cm ?? ''}
                  onChange={(e) =>
                    handleFieldChange(
                      'height_cm',
                      e.target.value === '' ? null : Number(e.target.value)
                    )
                  }
                  min={0}
                  className="w-full rounded-md bg-slate-950 border border-slate-700 px-2 py-1.5 text-sm outline-none focus:border-sky-500"
                />
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1">
                  Weight (kg)
                </label>
                <input
                  type="number"
                  value={coachProfile.weight_kg ?? ''}
                  onChange={(e) =>
                    handleFieldChange(
                      'weight_kg',
                      e.target.value === '' ? null : Number(e.target.value)
                    )
                  }
                  min={0}
                  step={0.1}
                  className="w-full rounded-md bg-slate-950 border border-slate-700 px-2 py-1.5 text-sm outline-none focus:border-sky-500"
                />
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="block text-xs text-slate-400 mb-1">
                Injuries / weak spots
              </label>
              <textarea
                value={coachProfile.injuries ?? ''}
                onChange={(e) => handleFieldChange('injuries', e.target.value)}
                rows={3}
                className="w-full rounded-md bg-slate-950 border border-slate-700 px-2 py-1.5 text-sm outline-none focus:border-sky-500"
              />
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">
                Constraints (pool, trainer, time, etc.)
              </label>
              <textarea
                value={coachProfile.constraints ?? ''}
                onChange={(e) =>
                  handleFieldChange('constraints', e.target.value)
                }
                rows={3}
                className="w-full rounded-md bg-slate-950 border border-slate-700 px-2 py-1.5 text-sm outline-none focus:border-sky-500"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="block text-xs text-slate-400 mb-1">
                Equipment
              </label>
              <textarea
                value={coachProfile.equipment ?? ''}
                onChange={(e) => handleFieldChange('equipment', e.target.value)}
                rows={2}
                className="w-full rounded-md bg-slate-950 border border-slate-700 px-2 py-1.5 text-sm outline-none focus:border-sky-500"
              />
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">
                Notes
              </label>
              <textarea
                value={coachProfile.notes ?? ''}
                onChange={(e) => handleFieldChange('notes', e.target.value)}
                rows={2}
                className="w-full rounded-md bg-slate-950 border border-slate-700 px-2 py-1.5 text-sm outline-none focus:border-sky-500"
              />
            </div>
          </div>
        </section>

        {/* Auto fields summary */}
        <section className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 text-xs text-slate-300 space-y-2">
          <h2 className="text-sm font-semibold mb-1">Auto data (from history)</h2>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
            <div>
              <div className="text-slate-500">Weeks analyzed</div>
              <div className="text-slate-100">
                {coachProfile.auto_weeks_analyzed ?? 0}
              </div>
            </div>
            <div>
              <div className="text-slate-500">Current weekly streak</div>
              <div className="text-slate-100">
                {coachProfile.auto_current_weekly_streak_weeks ?? 0} weeks
              </div>
            </div>
            <div>
              <div className="text-slate-500">Longest streak</div>
              <div className="text-slate-100">
                {coachProfile.auto_longest_weekly_streak_weeks ?? 0} weeks
              </div>
            </div>
            <div>
              <div className="text-slate-500">Avg hours (last 12w)</div>
              <div className="text-slate-100">
                {(coachProfile.auto_avg_hours_last_12_weeks ?? 0).toFixed(1)} h
              </div>
            </div>
            <div>
              <div className="text-slate-500">Avg hours (last 52w)</div>
              <div className="text-slate-100">
                {(coachProfile.auto_avg_hours_last_52_weeks ?? 0).toFixed(1)} h
              </div>
            </div>
          </div>

          {coachProfile.auto_discipline_hours_per_week && (
            <div className="mt-2">
              <div className="text-slate-500 mb-1">
                Avg discipline hours per week
              </div>
              <div className="flex flex-wrap gap-2">
                {Object.entries(coachProfile.auto_discipline_hours_per_week).map(
                  ([sport, hours]) => (
                    <span
                      key={sport}
                      className="px-2 py-0.5 rounded-full bg-slate-800 text-[11px]"
                    >
                      {sport}: {(hours as number).toFixed(1)} h
                    </span>
                  )
                )}
              </div>
            </div>
          )}
        </section>

        {/* Preferred sport days (read-only for now) */}
        <section className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 text-xs text-slate-300 space-y-2">
          <h2 className="text-sm font-semibold mb-1">Preferred sport days</h2>
          <div className="flex flex-wrap gap-2">
            {Object.entries(coachProfile.preferred_sport_days).map(
              ([sport, days]) => (
                <div
                  key={sport}
                  className="px-2 py-1 rounded-md bg-slate-950 border border-slate-700"
                >
                  <span className="font-semibold text-slate-100 mr-1">
                    {sport}:
                  </span>
                  <span className="text-slate-400">
                    {days.length > 0 ? days.join(', ') : '—'}
                  </span>
                </div>
              )
            )}
          </div>
        </section>
      </main>
    </div>
  );
}


