'use client';

import { useEffect, useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import { isAuthenticated, getAuthToken } from '@/lib/auth';
import { profileAPI, goalsAPI } from '@/lib/api';
import { PageHeader } from '@/components/PageHeader';
import type { AthleteProfile, GoalCreate } from '@/types';

type Status = 'idle' | 'loading' | 'success' | 'error';

type Step = 1 | 2;

const defaultGoalForm: GoalCreate = {
  race_name: '',
  goal_type: '',
  race_date: '',
  target_time: '',
  is_primary: true,
};

type SportCategory = 'triathlon' | 'run' | 'bike' | 'swim';

const RACE_DISTANCE_OPTIONS: Record<SportCategory, string[]> = {
  triathlon: ['Sprint', 'Olympic', 'Half Ironman 70.3', 'Full Ironman 140.6'],
  run: ['5K', '10K', 'Half marathon', 'Marathon'],
  bike: ['40K TT', '70K TT', '100K', '180K'],
  swim: ['1500m', '1900m', '3800m'],
};

export default function OnboardingPage() {
  const router = useRouter();
  const [status, setStatus] = useState<Status>('idle');
  const [step, setStep] = useState<Step>(1);
  const [error, setError] = useState<string | null>(null);
  const [profile, setProfile] = useState<AthleteProfile | null>(null);
  const [profileSaving, setProfileSaving] = useState(false);
  const [goalForm, setGoalForm] = useState<GoalCreate>(defaultGoalForm);
  const [goalSaving, setGoalSaving] = useState(false);
  const [sportCategory, setSportCategory] = useState<SportCategory>('triathlon');

  useEffect(() => {
    // Validate token on mount
    const token = getAuthToken();
    if (!token) {
      router.replace('/login');
      return;
    }

    // Clear stale state
    setProfile(null);
    setError(null);
    setStatus('idle');

    let cancelled = false;

    const init = async () => {
      try {
        setStatus('loading');
        setError(null);

        // Always fetch fresh data
        const [profileData, primaryGoalResult] = await Promise.allSettled([
          profileAPI.get(),
          goalsAPI.getPrimary(),
        ]);

        if (cancelled) return;

        if (profileData.status === 'fulfilled') {
          setProfile(profileData.value);
        }

        if (primaryGoalResult.status === 'fulfilled') {
          // Уже есть primary goal — онбординг не нужен
          router.replace('/dashboard');
          return;
        }

        setStatus('success');
      } catch (err: unknown) {
        if (cancelled) return;
        console.error('Onboarding init error:', err);
        setError('Failed to initialize onboarding. Please try again.');
        setStatus('error');
      }
    };

    void init();

    return () => {
      cancelled = true;
      // Clear state on unmount
      setProfile(null);
    };
  }, [router]);

  const handleProfileChange = (
    field: keyof AthleteProfile,
    value: string | number | null
  ) => {
    setProfile((prev) => {
      if (!prev) return prev;
      return { ...prev, [field]: value };
    });
  };

  const handleSaveProfileStep = async () => {
    if (!profile) {
      setStep(2);
      return;
    }
    try {
      setProfileSaving(true);
      setError(null);

      const payload: Partial<AthleteProfile> = {
        available_hours_per_week: profile.available_hours_per_week,
        primary_discipline: profile.primary_discipline,
        years_of_experience: profile.years_of_experience,
      };

      const updated = await profileAPI.update(payload);
      setProfile(updated);
      setStep(2);
    } catch (err: unknown) {
      console.error('Failed to save profile in onboarding:', err);
      setError('Failed to save profile. Please try again.');
    } finally {
      setProfileSaving(false);
    }
  };

  const handleGoalFormChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>
  ) => {
    const { name, value } = e.target;

    if (name === 'target_time') {
      setGoalForm((prev) => ({ ...prev, target_time: value }));
      return;
    }

    setGoalForm((prev) => ({ ...prev, [name]: value }));
  };

  const handleSaveGoalStep = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!goalForm.race_name || !goalForm.race_date) {
      setError('Race name and date are required');
      return;
    }

    try {
      setGoalSaving(true);
      setError(null);
      await goalsAPI.create({ ...goalForm, is_primary: true });
      router.replace('/dashboard');
    } catch (err: unknown) {
      console.error('Failed to save primary goal in onboarding:', err);
      setError('Failed to save primary goal. Please try again.');
    } finally {
      setGoalSaving(false);
    }
  };

  const canSkipProfile = useMemo(() => {
    if (!profile) return true;
    return (
      profile.available_hours_per_week > 0 &&
      !!profile.primary_discipline &&
      profile.years_of_experience >= 0
    );
  }, [profile]);

  if (status === 'loading' && !profile) {
    return (
      <div className="min-h-screen bg-slate-950 text-slate-50 flex items-center justify-center">
        <div className="text-slate-400">Preparing your coach...</div>
      </div>
    );
  }

  if (status === 'error') {
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

  return (
    <div className="min-h-screen bg-slate-950 text-slate-50">
      <PageHeader
        sectionLabel="Welcome"
        title="Let's set up your AI coach"
        containerWidthClassName="max-w-4xl"
      />

      <main className="max-w-4xl mx-auto px-4 py-6 space-y-6">
        {error && (
          <div className="text-xs text-red-400 bg-red-950/40 border border-red-900 rounded-md px-3 py-2">
            {error}
          </div>
        )}

        <div className="flex gap-2 text-xs text-slate-400">
          <div
            className={`px-3 py-1.5 rounded-full border ${
              step === 1
                ? 'border-sky-500 text-sky-300 bg-sky-950/40'
                : 'border-slate-700'
            }`}
          >
            1. Training profile
          </div>
          <div
            className={`px-3 py-1.5 rounded-full border ${
              step === 2
                ? 'border-sky-500 text-sky-300 bg-sky-950/40'
                : 'border-slate-700'
            }`}
          >
            2. Primary race
          </div>
        </div>

        {step === 1 && profile && (
          <section className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 space-y-3 text-sm">
            <div className="flex items-center justify-between mb-1">
              <div>
                <h2 className="text-sm font-semibold">Training profile</h2>
                <p className="text-xs text-slate-400">
                  This helps the coach build realistic plans for your week.
                </p>
              </div>
              {canSkipProfile && (
                <button
                  type="button"
                  onClick={() => setStep(2)}
                  className="text-[11px] text-slate-400 hover:text-slate-100"
                >
                  Skip for now
                </button>
              )}
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="block text-xs text-slate-400 mb-1">
                  Available hours per week
                </label>
                <input
                  type="number"
                  value={profile.available_hours_per_week}
                  onChange={(e) =>
                    handleProfileChange(
                      'available_hours_per_week',
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
                  Primary discipline
                </label>
                <select
                  value={profile.primary_discipline ?? ''}
                  onChange={(e) =>
                    handleProfileChange(
                      'primary_discipline',
                      e.target.value || null
                    )
                  }
                  className="w-full rounded-md bg-slate-950 border border-slate-700 px-2 py-1.5 text-sm outline-none focus:border-sky-500"
                >
                  <option value="">—</option>
                  <option value="triathlon">Triathlon</option>
                  <option value="run">Run</option>
                  <option value="bike">Bike</option>
                  <option value="swim">Swim</option>
                </select>
              </div>

              <div>
                <label className="block text-xs text-slate-400 mb-1">
                  Years of experience
                </label>
                <input
                  type="number"
                  value={profile.years_of_experience}
                  onChange={(e) =>
                    handleProfileChange(
                      'years_of_experience',
                      Number(e.target.value || 0)
                    )
                  }
                  min={0}
                  className="w-full rounded-md bg-slate-950 border border-slate-700 px-2 py-1.5 text-sm outline-none focus:border-sky-500"
                />
              </div>
            </div>

            <div className="flex justify-end gap-2 pt-2">
              {canSkipProfile && (
                <button
                  type="button"
                  onClick={() => setStep(2)}
                  className="px-4 py-1.5 rounded-md bg-slate-800 hover:bg-slate-700 text-[11px]"
                >
                  Skip
                </button>
              )}
              <button
                type="button"
                onClick={handleSaveProfileStep}
                disabled={profileSaving}
                className="px-4 py-1.5 rounded-md bg-sky-600 hover:bg-sky-500 disabled:opacity-50 text-[11px] font-medium"
              >
                {profileSaving ? 'Saving...' : 'Save & continue'}
              </button>
            </div>
          </section>
        )}

        {step === 2 && (
          <section className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 space-y-3 text-sm">
            <div className="mb-1">
              <h2 className="text-sm font-semibold">Primary race</h2>
              <p className="text-xs text-slate-400">
                Define your main race so the coach can work backwards from the
                target date.
              </p>
            </div>
            <form className="space-y-3 text-sm" onSubmit={handleSaveGoalStep}>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs text-slate-400 mb-1">
                    Sport
                  </label>
                  <select
                    value={sportCategory}
                    onChange={(e) =>
                      setSportCategory(e.target.value as SportCategory)
                    }
                    className="w-full rounded-md bg-slate-950 border border-slate-700 px-2 py-1.5 text-sm outline-none focus:border-sky-500"
                  >
                    <option value="triathlon">Triathlon</option>
                    <option value="run">Run</option>
                    <option value="bike">Bike</option>
                    <option value="swim">Swim</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs text-slate-400 mb-1">
                    Race name *
                  </label>
                  <input
                    type="text"
                    name="race_name"
                    value={goalForm.race_name}
                    onChange={handleGoalFormChange}
                    className="w-full rounded-md bg-slate-950 border border-slate-700 px-2 py-1.5 text-sm outline-none focus:border-sky-500"
                    placeholder="Ironman 70.3 Victoria"
                    required
                  />
                </div>

                <div>
                  <label className="block text-xs text-slate-400 mb-1">
                    Race distance
                  </label>
                  <select
                    name="goal_type"
                    value={goalForm.goal_type ?? ''}
                    onChange={handleGoalFormChange}
                    className="w-full rounded-md bg-slate-950 border border-slate-700 px-2 py-1.5 text-sm outline-none focus:border-sky-500"
                  >
                    <option value="">Select distance</option>
                    {RACE_DISTANCE_OPTIONS[sportCategory].map((opt) => (
                      <option key={opt} value={opt}>
                        {opt}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-xs text-slate-400 mb-1">
                    Race date *
                  </label>
                  <input
                    type="date"
                    name="race_date"
                    value={goalForm.race_date}
                    onChange={handleGoalFormChange}
                    className="w-full rounded-md bg-slate-950 border border-slate-700 px-2 py-1.5 text-sm outline-none focus:border-sky-500"
                    required
                  />
                </div>

                <div>
                  <label className="block text-xs text-slate-400 mb-1">
                    Target time (HH:MM:SS)
                  </label>
                  <input
                    type="time"
                    name="target_time"
                    value={goalForm.target_time ?? ''}
                    onChange={handleGoalFormChange}
                    step={1}
                    className="w-full rounded-md bg-slate-950 border border-slate-700 px-2 py-1.5 text-sm outline-none focus:border-sky-500"
                    placeholder="04:30:00"
                  />
                </div>
              </div>

              <div className="flex justify-between items-center pt-2">
                <button
                  type="button"
                  onClick={() => setStep(1)}
                  className="text-[11px] text-slate-400 hover:text-slate-100"
                >
                  ← Back to training profile
                </button>
                <button
                  type="submit"
                  disabled={goalSaving}
                  className="px-4 py-1.5 rounded-md bg-sky-600 hover:bg-sky-500 disabled:opacity-50 text-[11px] font-medium"
                >
                  {goalSaving ? 'Saving...' : 'Save & go to dashboard'}
                </button>
              </div>
            </form>
          </section>
        )}
      </main>
    </div>
  );
}


