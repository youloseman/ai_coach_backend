'use client';

import { useEffect, useState } from 'react';
import { TrendingUp, TrendingDown, Minus, Activity, RefreshCw } from 'lucide-react';
import { analyticsAPI } from '@/lib/api';
import type { FormStatus } from '@/types';

export function FormStatusCard() {
  const [formStatus, setFormStatus] = useState<FormStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadFormStatus = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await analyticsAPI.getFormStatus();
      setFormStatus(data);
    } catch (err) {
      console.error('Failed to load form status:', err);
      setError('Failed to load form status');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadFormStatus();
  }, []);

  if (loading) {
    return (
      <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
            Current Form
          </h3>
        </div>
        <div className="animate-pulse space-y-4">
          <div className="h-8 bg-gray-200 dark:bg-gray-700 rounded w-32"></div>
          <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-full"></div>
          <div className="grid grid-cols-3 gap-4">
            <div className="h-16 bg-gray-200 dark:bg-gray-700 rounded"></div>
            <div className="h-16 bg-gray-200 dark:bg-gray-700 rounded"></div>
            <div className="h-16 bg-gray-200 dark:bg-gray-700 rounded"></div>
          </div>
        </div>
      </div>
    );
  }

  if (error || !formStatus || formStatus.status !== 'success' || !formStatus.form) {
    return (
      <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4">
        <div className="flex items-center gap-2 mb-3">
          <Activity className="w-5 h-5 text-gray-400 dark:text-gray-500" />
          <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
            Current Form
          </h3>
        </div>
        <p className="text-sm text-gray-600 dark:text-gray-400">
          Connect Strava and sync activities to see your current form status.
        </p>
      </div>
    );
  }

  const getFormColor = (color: string | undefined) => {
    const normalized = (color || 'gray').toLowerCase();
    switch (normalized) {
      case 'green':
        return {
          bg: 'bg-emerald-500/10',
          text: 'text-emerald-400',
          border: 'border-emerald-500/30',
          icon: TrendingUp,
        };
      case 'yellow':
      case 'lightgreen':
        return {
          bg: 'bg-emerald-500/10',
          text: 'text-emerald-400',
          border: 'border-emerald-500/30',
          icon: Minus,
        };
      case 'orange':
        return {
          bg: 'bg-amber-500/10',
          text: 'text-amber-400',
          border: 'border-amber-500/30',
          icon: TrendingDown,
        };
      case 'red':
        return {
          bg: 'bg-red-500/10',
          text: 'text-red-400',
          border: 'border-red-500/30',
          icon: TrendingDown,
        };
      default:
        return {
          bg: 'bg-slate-800',
          text: 'text-slate-200',
          border: 'border-slate-700',
          icon: Minus,
        };
    }
  };

  const getTSBColor = (tsb: number) => {
    if (tsb > 5) return 'text-emerald-400';
    if (tsb < -10) return 'text-red-400';
    return 'text-amber-400';
  };

  const formColor = getFormColor(formStatus.form.color);
  const FormIcon = formColor.icon;

  return (
    <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-slate-100">
          Current Form
        </h3>
        <button
          onClick={loadFormStatus}
          className="p-2 text-slate-500 hover:text-slate-300 transition-colors"
          aria-label="Refresh form status"
        >
          <RefreshCw className="w-4 h-4" />
        </button>
      </div>

      <div className="space-y-4">
        {/* Form Badge */}
        <div
          className={`inline-flex items-center gap-2 px-4 py-2 rounded-lg border ${formColor.border} ${formColor.bg}`}
        >
          <FormIcon className={`w-5 h-5 ${formColor.text}`} />
          <span className={`text-base font-semibold ${formColor.text}`}>
            {formStatus.form.label}
          </span>
        </div>

        {/* Metrics Grid */}
        <div className="grid grid-cols-3 gap-4">
          <div className="text-center">
            <div className="text-xs text-slate-400 uppercase mb-1">
              Fitness (CTL)
            </div>
            <div className="text-2xl font-bold text-slate-100">
              {typeof formStatus.ctl === 'number' ? formStatus.ctl.toFixed(1) : 'N/A'}
            </div>
          </div>
          <div className="text-center">
            <div className="text-xs text-slate-400 uppercase mb-1">
              Fatigue (ATL)
            </div>
            <div className="text-2xl font-bold text-slate-100">
              {typeof formStatus.atl === 'number' ? formStatus.atl.toFixed(1) : 'N/A'}
            </div>
          </div>
          <div className="text-center">
            <div className="text-xs text-slate-400 uppercase mb-1">
              Form (TSB)
            </div>
            <div className={`text-2xl font-bold ${getTSBColor(formStatus.tsb)}`}>
              {typeof formStatus.tsb === 'number' 
                ? `${formStatus.tsb > 0 ? '+' : ''}${formStatus.tsb.toFixed(1)}`
                : 'N/A'}
            </div>
          </div>
        </div>

        {/* Description */}
        <p className="text-sm text-slate-300 leading-relaxed">
          {formStatus.form.description}
        </p>

        {/* Recommendation */}
        <div className="bg-sky-500/10 border-l-4 border-sky-500/60 p-3 rounded">
          <div className="flex items-start gap-2">
            <span className="text-blue-600 dark:text-blue-400 text-lg">💡</span>
            <div>
              <p className="text-sm font-medium text-slate-100 mb-1">
                Recommendation:
              </p>
              <p className="text-sm text-slate-300">
                {formStatus.form.recommendation}
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
