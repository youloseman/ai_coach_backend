// frontend/components/analytics/FitnessSummary.tsx

'use client';

import React, { useEffect, useState } from 'react';
import { analyticsAPI } from '@/lib/api';

interface Summary {
  ctl: number;
  atl: number;
  tsb: number;
  rr: number;
  status: string;
  message: string;
  form_status: string;
}

export function FitnessSummary() {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchSummary();
  }, []);

  const fetchSummary = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await analyticsAPI.getSummary();
      setSummary(data);
    } catch (err) {
      console.error('Failed to fetch summary:', err);
      setError('Failed to load fitness summary');
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'optimal':
        return 'bg-emerald-500/20 border-emerald-500/50 text-emerald-300';
      case 'race_ready':
        return 'bg-blue-500/20 border-blue-500/50 text-blue-300';
      case 'overtrained':
        return 'bg-red-500/20 border-red-500/50 text-red-300';
      case 'detraining':
        return 'bg-amber-500/20 border-amber-500/50 text-amber-300';
      case 'fresh':
        return 'bg-green-500/20 border-green-500/50 text-green-300';
      case 'no_data':
        return 'bg-slate-500/20 border-slate-500/50 text-slate-300';
      default:
        return 'bg-slate-500/20 border-slate-500/50 text-slate-300';
    }
  };

  if (loading) {
    return (
      <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-6">
        <h3 className="text-lg font-semibold mb-4 text-slate-100">Current Fitness</h3>
        <div className="animate-pulse space-y-4">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="h-20 bg-slate-800 rounded-lg" />
            ))}
          </div>
          <div className="h-12 bg-slate-800 rounded-lg" />
        </div>
      </div>
    );
  }

  if (error || !summary) {
    return (
      <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-6">
        <h3 className="text-lg font-semibold mb-4 text-slate-100">Current Fitness</h3>
        <div className="text-slate-400 text-center py-8">
          <p>{error || 'No fitness data available'}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-6">
      <h3 className="text-lg font-semibold mb-4 text-slate-100">Current Fitness</h3>
      
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
        <div className="bg-slate-900/60 rounded-lg p-4 border border-slate-800">
          <div className="text-sm text-slate-400 mb-1">CTL (Fitness)</div>
          <div className="text-2xl font-bold text-blue-400">{summary.ctl}</div>
        </div>
        <div className="bg-slate-900/60 rounded-lg p-4 border border-slate-800">
          <div className="text-sm text-slate-400 mb-1">ATL (Fatigue)</div>
          <div className="text-2xl font-bold text-red-400">{summary.atl}</div>
        </div>
        <div className="bg-slate-900/60 rounded-lg p-4 border border-slate-800">
          <div className="text-sm text-slate-400 mb-1">TSB (Form)</div>
          <div className={`text-2xl font-bold ${
            summary.tsb > 10 ? 'text-green-400' :
            summary.tsb > -10 ? 'text-yellow-400' :
            'text-red-400'
          }`}>
            {summary.tsb > 0 ? '+' : ''}{summary.tsb}
          </div>
        </div>
        <div className="bg-slate-900/60 rounded-lg p-4 border border-slate-800">
          <div className="text-sm text-slate-400 mb-1">Ramp Rate</div>
          <div className={`text-2xl font-bold ${
            summary.rr > 8 ? 'text-red-400' :
            summary.rr > 5 ? 'text-yellow-400' :
            'text-green-400'
          }`}>
            {summary.rr > 0 ? '+' : ''}{summary.rr}
          </div>
        </div>
      </div>
      
      <div className={`${getStatusColor(summary.status)} border rounded-lg px-4 py-3`}>
        <p className="font-medium">{summary.message}</p>
      </div>
    </div>
  );
}

