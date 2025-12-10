'use client';

import { useEffect, useState } from 'react';
import { Trophy, RefreshCw } from 'lucide-react';
import { goalsAPI, analyticsAPI } from '@/lib/api';
import type { Goal, RacePrediction } from '@/types';

export function RacePredictionCard() {
  const [prediction, setPrediction] = useState<RacePrediction | null>(null);
  const [primaryGoal, setPrimaryGoal] = useState<Goal | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadPrediction = async () => {
    try {
      setLoading(true);
      setError(null);

      // First, get the primary goal
      const goal = await goalsAPI.getPrimary();
      setPrimaryGoal(goal);

      // Then get the race prediction for this goal
      if (goal && goal.goal_type && goal.target_time) {
        const predictionData = await analyticsAPI.predictRace(
          goal.goal_type,
          goal.target_time,
          'run',
          12
        );
        setPrediction(predictionData);
      }
    } catch (err) {
      console.error('Failed to load race prediction:', err);
      setError('Failed to load prediction');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadPrediction();
  }, []);

  if (loading) {
    return (
      <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-semibold text-slate-100">
            Race Prediction
          </h3>
        </div>
        <div className="animate-pulse space-y-4">
          <div className="h-8 bg-slate-800 rounded w-32"></div>
          <div className="h-4 bg-slate-800 rounded w-full"></div>
          <div className="h-12 bg-slate-800 rounded"></div>
        </div>
      </div>
    );
  }

  if (error || !primaryGoal) {
    return (
      <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4">
        <div className="flex items-center gap-2 mb-3">
          <Trophy className="w-5 h-5 text-amber-400" />
          <h3 className="text-sm font-semibold text-slate-100">
            Race Prediction
          </h3>
        </div>
        <p className="text-sm text-slate-300">
          Set a primary goal to see your race prediction and success probability.
        </p>
      </div>
    );
  }

  if (!prediction) {
    return (
      <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4">
        <div className="flex items-center gap-2 mb-3">
          <Trophy className="w-5 h-5 text-amber-400" />
          <h3 className="text-sm font-semibold text-slate-100">
            Race Prediction
          </h3>
        </div>
        <p className="text-sm text-slate-300">
          Complete more workouts to get race predictions.
        </p>
      </div>
    );
  }

  if (prediction.status !== 'success' || !prediction.prediction || !prediction.goal) {
    return (
      <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4">
        <div className="flex items-center gap-2 mb-3">
          <Trophy className="w-5 h-5 text-amber-400" />
          <h3 className="text-sm font-semibold text-slate-100">
            Race Prediction
          </h3>
        </div>
        <p className="text-sm text-slate-300 mb-2">
          {prediction.error ||
            (prediction.status === 'no_data'
              ? 'No race efforts found in your training history.'
              : prediction.status === 'invalid_target_time'
              ? 'Target time format is invalid. Use formats like 1:30:00 or 45:30.'
              : 'Unable to generate race prediction right now.')}
        </p>
        {prediction.recommendation && (
          <p className="text-xs text-slate-400">{prediction.recommendation}</p>
        )}
      </div>
    );
  }

  const getProbabilityColor = (probability?: number) => {
    if (probability === undefined || probability === null) return 'text-slate-400';
    if (probability >= 70) return 'text-emerald-400';
    if (probability >= 40) return 'text-amber-400';
    return 'text-red-400';
  };

  const getProbabilityBarColor = (probability?: number) => {
    if (probability === undefined || probability === null) return 'bg-slate-700';
    if (probability >= 70) return 'bg-green-500';
    if (probability >= 40) return 'bg-yellow-500';
    return 'bg-red-500';
  };

  const probability = prediction.prediction?.probability_of_success;

  return (
    <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Trophy className="w-5 h-5 text-amber-400" />
          <h3 className="text-sm font-semibold text-slate-100">
            Race Prediction: {prediction.goal.race_type}
          </h3>
        </div>
        <button
          onClick={loadPrediction}
          className="p-2 text-slate-500 hover:text-slate-300 transition-colors"
          aria-label="Refresh prediction"
        >
          <RefreshCw className="w-4 h-4" />
        </button>
      </div>

      <div className="space-y-4">
        {/* Goal vs Predicted Times */}
        <div className="grid grid-cols-2 gap-4">
          <div className="text-center p-3 bg-slate-900 rounded-lg border border-slate-700">
            <div className="text-xs text-slate-400 uppercase mb-1">Your Goal</div>
            <div className="text-2xl font-bold text-slate-100">
              {prediction.goal.target_time}
            </div>
          </div>
          <div className="text-center p-3 bg-sky-500/10 rounded-lg border border-sky-500/40">
            <div className="text-xs text-slate-400 uppercase mb-1">Predicted</div>
            <div className="text-2xl font-bold text-sky-400">
              {prediction.prediction.predicted_time}
            </div>
          </div>
        </div>

        {/* Success Probability */}
        {probability !== undefined && probability !== null && (
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-slate-200">
                Success Probability
              </span>
              <span className={`text-2xl font-bold ${getProbabilityColor(probability)}`}>
                {probability.toFixed(0)}%
              </span>
            </div>
            <div className="w-full bg-slate-800 rounded-full h-3">
              <div
                className={`h-3 rounded-full transition-all duration-500 ${getProbabilityBarColor(
                  probability,
                )}`}
                style={{ width: `${Math.min(probability, 100)}%` }}
              ></div>
            </div>
          </div>
        )}

        {/* Based on and confidence */}
        <div className="text-xs text-slate-400 space-y-1">
          <div>Based on: {prediction.prediction.based_on}</div>
          <div>Model confidence: {prediction.prediction.confidence.toFixed(1)}%</div>
        </div>

        {/* Recommendations */}
        {prediction.recommendations && prediction.recommendations.length > 0 && (
          <div>
            <p className="text-sm font-semibold text-slate-100 mb-2">Recommendations:</p>
            <ul className="space-y-1">
              {prediction.recommendations.map((rec, idx) => (
                <li key={idx} className="text-sm text-slate-300 flex items-start gap-2">
                  <span className="text-sky-400">→</span>
                  <span>{rec}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}
