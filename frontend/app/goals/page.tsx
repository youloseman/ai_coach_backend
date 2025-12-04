// app/goals/page.tsx
'use client';

import { useEffect, useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import { isAuthenticated } from '@/lib/auth';
import { goalsAPI } from '@/lib/api';
import { PageHeader } from '@/components/PageHeader';
import type { Goal, GoalCreate } from '@/types';
import { Calendar, Target, PlusCircle } from 'lucide-react';

type Status = 'idle' | 'loading' | 'success' | 'error';

const getDaysToRace = (dateStr?: string | null): number | null => {
  if (!dateStr) return null;
  const race = new Date(dateStr);
  if (isNaN(race.getTime())) return null;

  const diff = Math.ceil((race.getTime() - Date.now()) / (1000 * 60 * 60 * 24));
  if (diff < 0) return 0;
  return diff;
};

const defaultForm: GoalCreate = {
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

export default function GoalsPage() {
  const router = useRouter();
  const [status, setStatus] = useState<Status>('idle');
  const [error, setError] = useState<string | null>(null);
  const [goals, setGoals] = useState<Goal[]>([]);
  const [form, setForm] = useState<GoalCreate>(defaultForm);
  const [submitting, setSubmitting] = useState(false);
  const [sportCategory, setSportCategory] = useState<SportCategory>('triathlon');

  useEffect(() => {
    if (!isAuthenticated()) {
      router.replace('/login');
      return;
    }

    let isCancelled = false;

    const loadGoals = async () => {
      try {
        setStatus('loading');
        setError(null);
        const data = await goalsAPI.list(false);
        if (isCancelled) return;
        setGoals(data);
        setStatus('success');
      } catch (err: unknown) {
        if (isCancelled) return;
        console.error('Load goals error:', err);
        setError('Failed to load goals');
        setStatus('error');
      }
    };

    loadGoals();

    return () => {
      isCancelled = true;
    };
  }, [router]);

  const primaryGoal = useMemo(
    () => goals.find((g) => g.is_primary) || null,
    [goals]
  );

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>
  ) => {
    const target = e.target;
    const { name, value } = target;

    if (name === 'is_primary' && target instanceof HTMLInputElement) {
      setForm((prev) => ({ ...prev, is_primary: target.checked }));
      return;
    }

    if (name === 'target_time') {
      setForm((prev) => ({ ...prev, target_time: value }));
      return;
    }

    setForm((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.race_name || !form.race_date) {
      setError('Race name and date are required');
      return;
    }

    setSubmitting(true);
    setError(null);

    try {
      const created = await goalsAPI.create(form);
      setGoals((prev) => [...prev, created]);
      setForm(defaultForm);
    } catch (err: unknown) {
      console.error('Create goal error:', err);
      setError('Failed to create goal');
    } finally {
      setSubmitting(false);
    }
  };

  if (status === 'loading' && goals.length === 0) {
    return (
      <div className="min-h-screen bg-slate-950 text-slate-50 flex items-center justify-center">
        <div className="text-slate-400">Loading goals...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-50">
      <PageHeader
        sectionLabel="Goals"
        title="Race planning"
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

        {/* Primary goal summary */}
        <section className="bg-slate-900/60 border border-slate-800 rounded-xl p-4">
          <div className="flex items-center gap-2 mb-3">
            <Target className="w-5 h-5 text-amber-400" />
            <h2 className="text-sm font-semibold">Primary race</h2>
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
                  <span className="text-xs text-slate-400 flex items-center gap-1">
                    <Calendar className="w-3 h-3" />
                    {new Date(primaryGoal.race_date).toLocaleDateString()}
                  </span>
                )}
              </div>
              {primaryGoal.target_time != null && (
                <div className="text-xs text-slate-400">
                  Target time:{' '}
                  <span className="text-slate-100">
                    {primaryGoal.target_time} h
                  </span>
                </div>
              )}
              {(() => {
                const d = getDaysToRace(primaryGoal.race_date);
                if (typeof d !== 'number') return null;
                return (
                  <div className="text-xs text-slate-400">
                    {d === 0 ? 'Race day is today or already passed' : `${d} days to go`}
                  </div>
                );
              })()}
            </div>
          ) : (
            <div className="text-xs text-slate-400">
              No primary race yet. Use the form below to create one.
            </div>
          )}
        </section>

        {/* Form */}
        <section className="bg-slate-900/60 border border-slate-800 rounded-xl p-4">
          <div className="flex items-center gap-2 mb-3">
            <PlusCircle className="w-5 h-5 text-sky-400" />
            <h2 className="text-sm font-semibold">Add or update goal</h2>
          </div>
          <form className="space-y-3 text-sm" onSubmit={handleSubmit}>
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
                  value={form.race_name}
                  onChange={handleChange}
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
                  value={form.goal_type ?? ''}
                  onChange={handleChange}
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
                  value={form.race_date}
                  onChange={handleChange}
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
                  value={form.target_time ?? ''}
                  onChange={handleChange}
                  step={1}
                  className="w-full rounded-md bg-slate-950 border border-slate-700 px-2 py-1.5 text-sm outline-none focus:border-sky-500"
                  placeholder="04:30:00"
                />
              </div>
            </div>

            <div className="flex items-center gap-2">
              <input
                id="is_primary"
                type="checkbox"
                name="is_primary"
                checked={form.is_primary}
                onChange={handleChange}
                className="w-4 h-4 rounded border-slate-700 bg-slate-950"
              />
              <label
                htmlFor="is_primary"
                className="text-xs text-slate-300 select-none"
              >
                Set as primary race
              </label>
            </div>

            <div className="flex justify-end">
              <button
                type="submit"
                disabled={submitting}
                className="px-4 py-2 rounded-md bg-sky-600 hover:bg-sky-500 disabled:opacity-50 text-xs font-medium"
              >
                {submitting ? 'Saving...' : 'Save goal'}
              </button>
            </div>
          </form>
        </section>

        {/* Goals list */}
        {goals.length > 0 && (
          <section className="bg-slate-900/60 border border-slate-800 rounded-xl p-4">
            <h2 className="text-sm font-semibold mb-3">All goals</h2>
            <div className="space-y-2 text-xs">
              {goals.map((g) => {
                const d = getDaysToRace(g.race_date);
                return (
                  <div
                    key={g.id}
                    className="flex flex-wrap justify-between gap-2 border border-slate-800 rounded-lg px-3 py-2 bg-slate-950/60"
                  >
                    <div>
                      <div className="font-medium text-slate-100">
                        {g.race_name}{' '}
                        {g.is_primary && (
                          <span className="ml-1 text-[10px] px-1.5 py-0.5 rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/40">
                            primary
                          </span>
                        )}
                      </div>
                      <div className="text-slate-400">
                        {g.goal_type && <span>{g.goal_type} · </span>}
                        {g.race_date && (
                          <span>
                            {new Date(g.race_date).toLocaleDateString()}
                          </span>
                        )}
                      </div>
                    </div>
                    <div className="text-right text-slate-400">
                      {g.target_time != null && (
                        <div>Target: {g.target_time} h</div>
                      )}
                      {typeof d === 'number' && (
                        <div className="text-[11px]">
                          {d === 0
                            ? 'today / passed'
                            : `${d} days to go`}
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </section>
        )}
      </main>
    </div>
  );
}
