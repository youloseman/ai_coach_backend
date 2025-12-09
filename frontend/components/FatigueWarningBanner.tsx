'use client';

import { useEffect, useState } from 'react';
import { AlertTriangle, X } from 'lucide-react';
import { analyticsAPI } from '@/lib/api';
import type { FatigueAnalysis } from '@/types';

export function FatigueWarningBanner() {
  const [fatigueData, setFatigueData] = useState<FatigueAnalysis | null>(null);
  const [loading, setLoading] = useState(true);
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => {
    const loadFatigueAnalysis = async () => {
      try {
        setLoading(true);
        const data = await analyticsAPI.getFatigueAnalysis(4);
        setFatigueData(data);
      } catch (err) {
        console.error('Failed to load fatigue analysis:', err);
      } finally {
        setLoading(false);
      }
    };

    loadFatigueAnalysis();
  }, []);

  // Don't show anything while loading
  if (loading) {
    return null;
  }

  // Don't show if dismissed
  if (dismissed) {
    return null;
  }

  // Don't show if no data or not high/critical fatigue
  if (!fatigueData || fatigueData.status !== 'success') {
    return null;
  }

  const level = fatigueData.overall_fatigue_level.toUpperCase();
  if (level !== 'HIGH' && level !== 'CRITICAL') {
    return null;
  }

  const isCritical = level === 'CRITICAL';

  return (
    <div
      className={`${
        isCritical
          ? 'bg-red-100 dark:bg-red-900/20 border-l-4 border-red-400'
          : 'bg-orange-100 dark:bg-orange-900/20 border-l-4 border-orange-400'
      } rounded-lg p-4 mb-6`}
    >
      <div className="flex items-start gap-3">
        <AlertTriangle
          className={`w-6 h-6 flex-shrink-0 mt-0.5 ${
            isCritical
              ? 'text-red-600 dark:text-red-400'
              : 'text-orange-600 dark:text-orange-400'
          }`}
        />

        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-2 mb-2">
            <h3
              className={`text-base font-bold ${
                isCritical
                  ? 'text-red-900 dark:text-red-300'
                  : 'text-orange-900 dark:text-orange-300'
              }`}
            >
              ⚠️ {isCritical ? 'Critical' : 'High'} Fatigue Warning
            </h3>
            <button
              onClick={() => setDismissed(true)}
              className="p-1 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 transition-colors"
              aria-label="Dismiss warning"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          <p className="text-sm text-gray-700 dark:text-gray-300 mb-3">
            Fatigue Score: <span className="font-bold">{fatigueData.fatigue_score.toFixed(1)}/100</span>
          </p>

          {/* Detected Issues */}
          {fatigueData.signals && fatigueData.signals.length > 0 && (
            <div className="mb-4">
              <p className="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-2">
                Detected Issues:
              </p>
              <ul className="space-y-1">
                {fatigueData.signals.map((signal, idx) => (
                  <li key={idx} className="text-sm text-gray-700 dark:text-gray-300 flex items-start gap-2">
                    <span className="text-gray-500">•</span>
                    <span>{signal.message || signal.description}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Recommendations */}
          {fatigueData.recommendations && fatigueData.recommendations.length > 0 && (
            <div className={`${
              isCritical
                ? 'bg-red-50 dark:bg-red-900/40'
                : 'bg-orange-50 dark:bg-orange-900/40'
            } rounded-lg p-3`}>
              <p className="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-2">
                Recommendations:
              </p>
              <ul className="space-y-1">
                {fatigueData.recommendations.map((rec, idx) => (
                  <li key={idx} className="text-sm text-gray-700 dark:text-gray-300 flex items-start gap-2">
                    <span className={`${
                      isCritical
                        ? 'text-red-600 dark:text-red-400'
                        : 'text-orange-600 dark:text-orange-400'
                    }`}>→</span>
                    <span>{rec}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
