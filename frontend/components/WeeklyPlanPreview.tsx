'use client';

import { useQuery } from '@tanstack/react-query';
import { coachAPI } from '@/lib/api';

interface PlanDay {
  day: string;
  title: string;
  duration_minutes?: number;
  completed?: boolean;
}

interface WeeklyPlanResponse {
  week_start_date: string;
  total_planned_hours: number;
  days: PlanDay[];
}

export function WeeklyPlanPreview() {
  const { data, isLoading, isError } = useQuery<WeeklyPlanResponse>({
    queryKey: ['weeklyPlanPreview'],
    queryFn: async () => {
      const res = await coachAPI.getWeeklyPlan();
      return res;
    },
  });

  const weekLabel = data?.week_start_date
    ? new Date(data.week_start_date).toLocaleDateString(undefined, {
        month: 'short',
        day: 'numeric',
      })
    : '';

  return (
    <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className="text-lg">📅</span>
          <div>
            <h2 className="text-sm font-semibold">This Week&apos;s Plan</h2>
            {data?.week_start_date && (
              <div className="text-[11px] text-slate-500">
                Week of {weekLabel}
              </div>
            )}
          </div>
        </div>
        <div className="text-xs text-slate-400">
          {data?.total_planned_hours != null
            ? `${data.total_planned_hours.toFixed(1)}h total`
            : ''}
        </div>
      </div>

      {isLoading ? (
        <div className="text-slate-500 text-xs">Loading weekly plan...</div>
      ) : isError || !data ? (
        <div className="text-slate-500 text-xs">
          Unable to load plan. Generate a plan to see it here.
        </div>
      ) : (
        <div className="space-y-2 text-xs text-slate-200">
          {data.days && data.days.length > 0 ? (
            data.days.map((day, idx) => (
              <div
                key={`${day.day}-${idx}`}
                className="flex items-center justify-between bg-slate-950/60 border border-slate-800 rounded-lg px-3 py-2"
              >
                <div className="flex items-center gap-2">
                  <span className="text-sm">
                    {day.completed ? '✅' : '•'}
                  </span>
                  <div>
                    <div className="text-slate-100 font-medium">
                      {day.day}: {day.title}
                    </div>
                    {day.duration_minutes != null && (
                      <div className="text-slate-500">
                        {day.duration_minutes} min
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))
          ) : (
            <div className="text-slate-500">No plan available.</div>
          )}
        </div>
      )}

      <div className="mt-3">
        <a
          href="/coach"
          className="text-[11px] text-sky-400 hover:text-sky-300 underline"
        >
          View Full Plan →
        </a>
      </div>
    </div>
  );
}


