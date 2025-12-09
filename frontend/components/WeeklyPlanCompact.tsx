'use client';

import { useQuery } from '@tanstack/react-query';
import { coachAPI } from '@/lib/api';
import { Calendar } from 'lucide-react';

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

export function WeeklyPlanCompact() {
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

  // Show max 4 workouts, scrollable
  const displayedDays = data?.days?.slice(0, 4) || [];

  return (
    <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 h-full flex flex-col">
      <div className="flex items-center gap-2 mb-3">
        <Calendar className="w-5 h-5 text-sky-400" />
        <div className="flex-1">
          <h2 className="text-sm font-semibold">This Week&apos;s Plan</h2>
          {data?.week_start_date && (
            <div className="text-[11px] text-slate-500">
              Week of {weekLabel} • {data.total_planned_hours?.toFixed(1) || '0'}h
            </div>
          )}
        </div>
      </div>

      {isLoading ? (
        <div className="text-slate-500 text-xs flex-1 flex items-center">
          Loading...
        </div>
      ) : isError || !data ? (
        <div className="text-slate-500 text-xs flex-1 flex items-center">
          No plan yet
        </div>
      ) : (
        <div className="flex-1 overflow-y-auto space-y-1.5 text-xs">
          {displayedDays.length > 0 ? (
            displayedDays.map((day, idx) => (
              <div
                key={`${day.day}-${idx}`}
                className="flex items-center gap-2 bg-slate-950/60 border border-slate-800 rounded px-2 py-1.5"
              >
                <span className="text-xs">
                  {day.completed ? '✅' : '○'}
                </span>
                <div className="flex-1 min-w-0">
                  <div className="text-slate-100 font-medium truncate">
                    {day.day}: {day.title}
                  </div>
                  {day.duration_minutes != null && (
                    <div className="text-slate-500 text-[10px]">
                      {day.duration_minutes}m
                    </div>
                  )}
                </div>
              </div>
            ))
          ) : (
            <div className="text-slate-500 text-xs">No workouts planned</div>
          )}
          {data.days && data.days.length > 4 && (
            <div className="text-[10px] text-slate-500 pt-1">
              +{data.days.length - 4} more
            </div>
          )}
        </div>
      )}

      <div className="mt-2 pt-2 border-t border-slate-800">
        <a
          href="/coach"
          className="text-[10px] text-sky-400 hover:text-sky-300 underline"
        >
          View Full →
        </a>
      </div>
    </div>
  );
}

