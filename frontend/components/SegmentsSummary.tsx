'use client';

import { useQuery } from '@tanstack/react-query';
import { performanceAPI } from '@/lib/api';

interface SegmentPR {
  name: string;
  elapsed_time: string;
  improvement: string;
  achieved_date: string;
}

export function SegmentsSummary() {
  const { data, isLoading, isError } = useQuery<SegmentPR[]>({
    queryKey: ['recentSegmentPRs'],
    queryFn: async () => {
      const res = await performanceAPI.getRecentSegmentPRs(3);
      return res || [];
    },
  });

  return (
    <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 h-full">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className="text-lg">🏔️</span>
          <h2 className="text-sm font-semibold">Recent PRs</h2>
        </div>
        <a
          href="/segments"
          className="text-[11px] text-sky-400 hover:text-sky-300 underline"
        >
          View All Segments →
        </a>
      </div>

      {isLoading ? (
        <div className="text-slate-500 text-xs">Loading segment PRs...</div>
      ) : isError ? (
        <div className="text-slate-500 text-xs">Unable to load segment PRs.</div>
      ) : data && data.length > 0 ? (
        <div className="space-y-3 text-xs text-slate-200">
          {data.map((pr, idx) => (
            <div
              key={`${pr.name}-${idx}`}
              className="bg-slate-950/60 border border-slate-800 rounded-lg p-3"
            >
              <div className="text-slate-100 font-medium flex items-center gap-2">
                🎯 <span>{pr.name}</span>
              </div>
              <div className="text-slate-300 mt-1">{pr.elapsed_time}</div>
              <div className="text-emerald-400 text-[11px]">
                ⬆️ {pr.improvement} faster
              </div>
              <div className="text-[11px] text-slate-500">
                {pr.achieved_date}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="text-slate-500 text-xs">No recent PRs.</div>
      )}
    </div>
  );
}


