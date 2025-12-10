// frontend/components/settings/TrainingZones.tsx

'use client';

import React, { useEffect, useState } from 'react';
import { profileAPI } from '@/lib/api';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import type { AthleteProfile } from '@/types';

interface TrainingZonesForm {
  ftp: number;
  threshold_pace_min_per_km: number;
  css_pace_100m_seconds: number;
  max_hr: number;
  rest_hr: number;
}

export function TrainingZones() {
  const queryClient = useQueryClient();
  const [zones, setZones] = useState<TrainingZonesForm>({
    ftp: 0,
    threshold_pace_min_per_km: 0,
    css_pace_100m_seconds: 0,
    max_hr: 0,
    rest_hr: 0,
  });
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // Load current profile
  const { data: profile } = useQuery<AthleteProfile>({
    queryKey: ['profile'],
    queryFn: () => profileAPI.get(),
  });

  useEffect(() => {
    if (profile) {
      // Extract zones from profile
      setZones({
        ftp: profile.training_zones_bike?.ftp || 0,
        threshold_pace_min_per_km: profile.training_zones_run?.threshold_pace_min_per_km || 
                                   profile.training_zones_run?.threshold_pace || 0,
        css_pace_100m_seconds: profile.training_zones_swim?.css_pace_100m_seconds ||
                               profile.training_zones_swim?.css_pace_100m ||
                               profile.training_zones_swim?.css || 0,
        max_hr: profile.training_zones_bike?.max_hr || 
                profile.training_zones_run?.max_hr || 
                profile.training_zones_swim?.max_hr || 0,
        rest_hr: profile.training_zones_bike?.rest_hr || 
                 profile.training_zones_run?.rest_hr || 
                 profile.training_zones_swim?.rest_hr || 0,
      });
    }
  }, [profile]);

  const handleSave = async () => {
    try {
      setSaving(true);
      setMessage(null);

      await profileAPI.updateTrainingZones({
        ftp: zones.ftp > 0 ? zones.ftp : undefined,
        threshold_pace_min_per_km: zones.threshold_pace_min_per_km > 0 ? zones.threshold_pace_min_per_km : undefined,
        css_pace_100m_seconds: zones.css_pace_100m_seconds > 0 ? zones.css_pace_100m_seconds : undefined,
        max_hr: zones.max_hr > 0 ? zones.max_hr : undefined,
        rest_hr: zones.rest_hr > 0 ? zones.rest_hr : undefined,
      });

      // Invalidate profile cache
      queryClient.invalidateQueries({ queryKey: ['profile'] });

      setMessage({ type: 'success', text: 'Training zones saved successfully!' });
    } catch (error) {
      console.error('Failed to save training zones:', error);
      setMessage({ type: 'error', text: 'Failed to save training zones. Please try again.' });
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-6">
      <h3 className="text-lg font-semibold mb-4 text-slate-100">Training Zones</h3>
      <p className="text-sm text-slate-400 mb-6">
        Set your training zones for accurate TSS (Training Stress Score) calculation.
        These values are used to calculate training load for your activities.
      </p>

      <div className="space-y-6">
        {/* Cycling FTP */}
        <div>
          <label className="block text-sm font-medium text-slate-300 mb-2">
            FTP (Functional Threshold Power) - Cycling
          </label>
          <input
            type="number"
            min="0"
            step="1"
            value={zones.ftp || ''}
            onChange={(e) => setZones({ ...zones, ftp: +e.target.value || 0 })}
            className="w-full rounded-md bg-slate-950 border border-slate-700 px-3 py-2 text-slate-100 outline-none focus:border-sky-500"
            placeholder="250"
          />
          <p className="text-xs text-slate-500 mt-1">
            Your Functional Threshold Power in watts. Run an FTP test to determine this value.
            Required for cycling TSS calculation.
          </p>
        </div>

        {/* Running Threshold Pace */}
        <div>
          <label className="block text-sm font-medium text-slate-300 mb-2">
            Threshold Pace - Running (min/km)
          </label>
          <input
            type="number"
            min="0"
            step="0.1"
            value={zones.threshold_pace_min_per_km || ''}
            onChange={(e) => setZones({ ...zones, threshold_pace_min_per_km: +e.target.value || 0 })}
            className="w-full rounded-md bg-slate-950 border border-slate-700 px-3 py-2 text-slate-100 outline-none focus:border-sky-500"
            placeholder="4.0"
          />
          <p className="text-xs text-slate-500 mt-1">
            Your 1-hour race pace in minutes per kilometer (e.g., 4.0 for 4:00/km).
            Required for running TSS calculation.
          </p>
        </div>

        {/* Swimming CSS */}
        <div>
          <label className="block text-sm font-medium text-slate-300 mb-2">
            CSS (Critical Swim Speed) - Swimming (seconds/100m)
          </label>
          <input
            type="number"
            min="0"
            step="0.1"
            value={zones.css_pace_100m_seconds || ''}
            onChange={(e) => setZones({ ...zones, css_pace_100m_seconds: +e.target.value || 0 })}
            className="w-full rounded-md bg-slate-950 border border-slate-700 px-3 py-2 text-slate-100 outline-none focus:border-sky-500"
            placeholder="90"
          />
          <p className="text-xs text-slate-500 mt-1">
            Your Critical Swim Speed in seconds per 100 meters (e.g., 90 for 1:30/100m).
            Required for swimming TSS calculation.
          </p>
        </div>

        {/* Max HR */}
        <div>
          <label className="block text-sm font-medium text-slate-300 mb-2">
            Maximum Heart Rate (bpm)
          </label>
          <input
            type="number"
            min="0"
            step="1"
            value={zones.max_hr || ''}
            onChange={(e) => setZones({ ...zones, max_hr: +e.target.value || 0 })}
            className="w-full rounded-md bg-slate-950 border border-slate-700 px-3 py-2 text-slate-100 outline-none focus:border-sky-500"
            placeholder="190"
          />
          <p className="text-xs text-slate-500 mt-1">
            Your maximum heart rate in beats per minute. Used for heart rate zone calculations.
          </p>
        </div>

        {/* Rest HR */}
        <div>
          <label className="block text-sm font-medium text-slate-300 mb-2">
            Resting Heart Rate (bpm)
          </label>
          <input
            type="number"
            min="0"
            step="1"
            value={zones.rest_hr || ''}
            onChange={(e) => setZones({ ...zones, rest_hr: +e.target.value || 0 })}
            className="w-full rounded-md bg-slate-950 border border-slate-700 px-3 py-2 text-slate-100 outline-none focus:border-sky-500"
            placeholder="50"
          />
          <p className="text-xs text-slate-500 mt-1">
            Your resting heart rate in beats per minute. Used for heart rate reserve calculations.
          </p>
        </div>

        {/* Message */}
        {message && (
          <div
            className={`px-4 py-3 rounded-lg ${
              message.type === 'success'
                ? 'bg-emerald-500/20 border border-emerald-500/50 text-emerald-300'
                : 'bg-red-500/20 border border-red-500/50 text-red-300'
            }`}
          >
            {message.text}
          </div>
        )}

        {/* Save Button */}
        <button
          onClick={handleSave}
          disabled={saving}
          className="w-full px-4 py-2 rounded-lg bg-sky-600 hover:bg-sky-700 disabled:bg-slate-700 disabled:cursor-not-allowed text-white font-medium transition-colors"
        >
          {saving ? 'Saving...' : 'Save Training Zones'}
        </button>
      </div>
    </div>
  );
}

