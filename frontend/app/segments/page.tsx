'use client';

import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { performanceAPI } from '@/lib/api';

type TrackedSegment = {
  id: number;
  name: string;
  activity_type: string;
  distance_meters: number;
  city?: string;
  country?: string;
};

type SegmentPR = {
  id?: number;
  segment_name?: string;
  name?: string;
  elapsed_time_seconds?: number;
  elapsed_time?: string;
  achieved_date?: string;
  improvement?: string;
};

type SearchSegment = {
  id?: number;
  strava_segment_id?: string;
  name: string;
  activity_type: string;
  distance_meters: number;
  city?: string;
  country?: string;
};

type TrackSegmentPayload = {
  strava_segment_id: string;
  name: string;
  activity_type: string;
  distance_meters: number;
  city?: string;
  country?: string;
};

export default function SegmentsPage() {
  const queryClient = useQueryClient();
  const [searchTerm, setSearchTerm] = useState('');

  const { data: trackedSegments, isLoading: trackedLoading, isError: trackedError } =
    useQuery<TrackedSegment[]>({
      queryKey: ['trackedSegments'],
      queryFn: () => performanceAPI.getTrackedSegments(),
    });

  const { data: prs, isLoading: prsLoading, isError: prsError } = useQuery<SegmentPR[]>({
    queryKey: ['segmentPRs'],
    queryFn: () => performanceAPI.getSegmentPersonalRecords(10),
  });

  const searchMutation = useMutation({
    mutationFn: () => performanceAPI.searchSegments(searchTerm),
  });

  const trackMutation = useMutation({
    mutationFn: (segment: TrackSegmentPayload) => performanceAPI.trackSegment(segment),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['trackedSegments'] });
    },
  });

  const formatKm = (meters?: number) =>
    meters != null ? `${(meters / 1000).toFixed(1)} km` : '–';

  return (
    <main className="min-h-screen bg-slate-950 text-slate-50 px-4 py-6">
      <div className="max-w-6xl mx-auto space-y-6">
        <header className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-semibold">Segments</h1>
            <p className="text-sm text-slate-400">Track and review your Strava segments.</p>
          </div>
        </header>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <section className="bg-slate-900/70 border border-slate-800 rounded-xl p-4 space-y-3">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-semibold">Tracked Segments</h2>
              {trackedLoading && <span className="text-xs text-slate-400">Loading...</span>}
            </div>

            {trackedError ? (
              <p className="text-xs text-red-400">Unable to load segments.</p>
            ) : trackedSegments && trackedSegments.length > 0 ? (
              <div className="space-y-2">
                {trackedSegments.map((seg) => (
                  <div
                    key={seg.id}
                    className="bg-slate-950/60 border border-slate-800 rounded-lg px-3 py-2 text-xs"
                  >
                    <div className="flex justify-between">
                      <span className="text-slate-100 font-medium">{seg.name}</span>
                      <span className="text-slate-500">{seg.activity_type}</span>
                    </div>
                    <div className="text-slate-400 flex gap-3 mt-1">
                      <span>{formatKm(seg.distance_meters)}</span>
                      {seg.city && <span>{seg.city}</span>}
                      {seg.country && <span>{seg.country}</span>}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-slate-400">No tracked segments yet.</p>
            )}
          </section>

          <section className="bg-slate-900/70 border border-slate-800 rounded-xl p-4 space-y-3">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-semibold">Recent Personal Records</h2>
              {prsLoading && <span className="text-xs text-slate-400">Loading...</span>}
            </div>
            {prsError ? (
              <p className="text-xs text-red-400">Unable to load personal records.</p>
            ) : prs && prs.length > 0 ? (
              <div className="space-y-2">
                {prs.map((pr, idx) => (
                  <div
                    key={`${pr.id || pr.name || idx}`}
                    className="bg-slate-950/60 border border-slate-800 rounded-lg px-3 py-2 text-xs"
                  >
                    <div className="text-slate-100 font-medium">
                      {pr.segment_name || pr.name || 'Segment'}
                    </div>
                    <div className="text-slate-300 mt-1">
                      {pr.elapsed_time ||
                        (pr.elapsed_time_seconds
                          ? `${Math.floor(pr.elapsed_time_seconds / 60)}:${(
                              '0' + (pr.elapsed_time_seconds % 60)
                            ).slice(-2)}`
                          : '—')}
                    </div>
                    {pr.improvement && (
                      <div className="text-emerald-400 text-[11px]">
                        ⬆️ {pr.improvement}
                      </div>
                    )}
                    {pr.achieved_date && (
                      <div className="text-[11px] text-slate-500">{pr.achieved_date}</div>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-slate-400">No personal records found.</p>
            )}
          </section>
        </div>

        <section className="bg-slate-900/70 border border-slate-800 rounded-xl p-4 space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold">Search Segments</h2>
            {searchMutation.isPending && (
              <span className="text-xs text-slate-400">Searching...</span>
            )}
          </div>
          <div className="flex flex-col sm:flex-row gap-2">
            <input
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Search by name"
              className="bg-slate-950/70 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:ring-1 focus:ring-sky-500 flex-1"
            />
            <button
              onClick={() => searchMutation.mutate()}
              className="px-4 py-2 bg-sky-600 hover:bg-sky-500 rounded-lg text-sm"
              disabled={!searchTerm}
            >
              Search
            </button>
          </div>

          {searchMutation.isError && (
            <p className="text-xs text-red-400">Search failed. Try again.</p>
          )}

          {searchMutation.data && Array.isArray(searchMutation.data) && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
              {searchMutation.data.map((seg: SearchSegment) => (
                <div
                  key={seg.id || seg.strava_segment_id}
                  className="bg-slate-950/60 border border-slate-800 rounded-lg px-3 py-2 text-xs"
                >
                  <div className="flex justify-between">
                    <span className="text-slate-100 font-medium">{seg.name}</span>
                    <span className="text-slate-500">{seg.activity_type}</span>
                  </div>
                  <div className="text-slate-400 mt-1">{formatKm(seg.distance_meters)}</div>
                  <button
                    onClick={() =>
                      trackMutation.mutate({
                        strava_segment_id: seg.strava_segment_id || String(seg.id || seg.name),
                        name: seg.name,
                        activity_type: seg.activity_type || 'Run',
                        distance_meters: seg.distance_meters || 0,
                        city: seg.city,
                        country: seg.country,
                      })
                    }
                    className="mt-2 text-[11px] text-sky-400 hover:text-sky-300 underline"
                  >
                    Track this segment
                  </button>
                </div>
              ))}
            </div>
          )}
        </section>
      </div>
    </main>
  );
}

