'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { weeklyPlanAPI } from '@/lib/api';

type PlanDay = {
  day?: string;
  title?: string;
  duration_minutes?: number;
  completed?: boolean;
  id?: string;
};

type WeeklyPlan = {
  week_start_date?: string;
  total_planned_hours?: number;
  days?: PlanDay[];
};

export default function PlansPage() {
  const queryClient = useQueryClient();

  const { data: plan, isLoading, isError } = useQuery<WeeklyPlan>({
    queryKey: ['weeklyPlanFull'],
    queryFn: weeklyPlanAPI.getCurrent,
  });

  const { data: history } = useQuery<{ plans: { week_start_date: string; filename: string }[] }>({
    queryKey: ['planHistory'],
    queryFn: weeklyPlanAPI.getHistory,
  });

  const completeMutation = useMutation({
    mutationFn: (workoutId: string) => weeklyPlanAPI.completeWorkout(workoutId, plan?.week_start_date),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['weeklyPlanFull'] });
    },
  });

  return (
    <main className="min-h-screen bg-slate-950 text-slate-50 px-4 py-6">
      <div className="max-w-5xl mx-auto space-y-6">
        <header className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-semibold">Plans</h1>
            <p className="text-sm text-slate-400">Your current weekly plan and history.</p>
          </div>
        </header>

        <section className="bg-slate-900/70 border border-slate-800 rounded-xl p-4 space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold">This Week</h2>
            {isLoading && <span className="text-xs text-slate-400">Loading...</span>}
          </div>

          {isError ? (
            <p className="text-xs text-red-400">Unable to load weekly plan.</p>
          ) : plan && plan.days && plan.days.length > 0 ? (
            <div className="space-y-2">
              {plan.days.map((day, idx) => (
                <div
                  key={`${day.day}-${idx}`}
                  className="bg-slate-950/60 border border-slate-800 rounded-lg px-3 py-2 text-xs flex justify-between items-center"
                >
                  <div>
                    <div className="text-slate-100 font-medium">
                      {day.day}: {day.title}
                    </div>
                    {day.duration_minutes != null && (
                      <div className="text-slate-500">{day.duration_minutes} min</div>
                    )}
                  </div>
                  <button
                    onClick={() => completeMutation.mutate(String(day.id || day.title || idx))}
                    className="text-[11px] text-sky-400 hover:text-sky-300 underline"
                  >
                    {day.completed ? 'Completed' : 'Mark done'}
                  </button>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-xs text-slate-400">No plan available.</p>
          )}
        </section>

        <section className="bg-slate-900/70 border border-slate-800 rounded-xl p-4 space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold">History</h2>
          </div>

          {history && history.plans && history.plans.length > 0 ? (
            <ul className="space-y-2 text-xs">
              {history.plans.map((p) => (
                <li
                  key={p.week_start_date}
                  className="bg-slate-950/60 border border-slate-800 rounded-lg px-3 py-2 flex justify-between"
                >
                  <span className="text-slate-100">{p.week_start_date}</span>
                  <span className="text-slate-500">{p.filename}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-xs text-slate-400">No saved plans yet.</p>
          )}
        </section>
      </div>
    </main>
  );
}

