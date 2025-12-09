'use client';

import { useEffect, useState } from 'react';
import { TrendingUp, TrendingDown, Minus, Activity, RefreshCw } from 'lucide-react';
import { analyticsAPI } from '@/lib/api';
import type { FormStatus } from '@/types';

export default function FormStatusCard() {
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
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
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

  if (error || !formStatus) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
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

  const getFormColor = (color: string) => {
    switch (color.toLowerCase()) {
      case 'green':
        return {
          bg: 'bg-green-100 dark:bg-green-900/20',
          text: 'text-green-800 dark:text-green-400',
          border: 'border-green-300 dark:border-green-700',
          icon: TrendingUp,
        };
      case 'yellow':
        return {
          bg: 'bg-yellow-100 dark:bg-yellow-900/20',
          text: 'text-yellow-800 dark:text-yellow-400',
          border: 'border-yellow-300 dark:border-yellow-700',
          icon: Minus,
        };
      case 'orange':
        return {
          bg: 'bg-orange-100 dark:bg-orange-900/20',
          text: 'text-orange-800 dark:text-orange-400',
          border: 'border-orange-300 dark:border-orange-700',
          icon: TrendingDown,
        };
      case 'red':
        return {
          bg: 'bg-red-100 dark:bg-red-900/20',
          text: 'text-red-800 dark:text-red-400',
          border: 'border-red-300 dark:border-red-700',
          icon: TrendingDown,
        };
      default:
        return {
          bg: 'bg-gray-100 dark:bg-gray-700',
          text: 'text-gray-800 dark:text-gray-300',
          border: 'border-gray-300 dark:border-gray-600',
          icon: Minus,
        };
    }
  };

  const getTSBColor = (tsb: number) => {
    if (tsb > 5) return 'text-green-600 dark:text-green-400';
    if (tsb < -10) return 'text-red-600 dark:text-red-400';
    return 'text-yellow-600 dark:text-yellow-400';
  };

  const formColor = getFormColor(formStatus.form.color);
  const FormIcon = formColor.icon;

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
          Current Form
        </h3>
        <button
          onClick={loadFormStatus}
          className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
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
            <div className="text-xs text-gray-500 dark:text-gray-400 uppercase mb-1">
              Fitness (CTL)
            </div>
            <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">
              {formStatus.current_ctl.toFixed(1)}
            </div>
          </div>
          <div className="text-center">
            <div className="text-xs text-gray-500 dark:text-gray-400 uppercase mb-1">
              Fatigue (ATL)
            </div>
            <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">
              {formStatus.current_atl.toFixed(1)}
            </div>
          </div>
          <div className="text-center">
            <div className="text-xs text-gray-500 dark:text-gray-400 uppercase mb-1">
              Form (TSB)
            </div>
            <div className={`text-2xl font-bold ${getTSBColor(formStatus.current_tsb)}`}>
              {formStatus.current_tsb > 0 ? '+' : ''}
              {formStatus.current_tsb.toFixed(1)}
            </div>
          </div>
        </div>

        {/* Description */}
        <p className="text-sm text-gray-600 dark:text-gray-400 leading-relaxed">
          {formStatus.form.description}
        </p>

        {/* Recommendation */}
        <div className="bg-blue-50 dark:bg-blue-900/20 border-l-4 border-blue-400 p-3 rounded">
          <div className="flex items-start gap-2">
            <span className="text-blue-600 dark:text-blue-400 text-lg">💡</span>
            <div>
              <p className="text-sm font-medium text-gray-900 dark:text-gray-100 mb-1">
                Recommendation:
              </p>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                {formStatus.form.recommendation}
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
