'use client';

import { useEffect, useState } from 'react';
import { Trophy, Target, RefreshCw } from 'lucide-react';
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
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
            Race Prediction
          </h3>
        </div>
        <div className="animate-pulse space-y-4">
          <div className="h-8 bg-gray-200 dark:bg-gray-700 rounded w-32"></div>
          <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-full"></div>
          <div className="h-12 bg-gray-200 dark:bg-gray-700 rounded"></div>
        </div>
      </div>
    );
  }

  if (error || !primaryGoal) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
        <div className="flex items-center gap-2 mb-3">
          <Trophy className="w-5 h-5 text-gray-400 dark:text-gray-500" />
          <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
            Race Prediction
          </h3>
        </div>
        <p className="text-sm text-gray-600 dark:text-gray-400">
          Set a primary goal to see your race prediction and success probability.
        </p>
      </div>
    );
  }

  if (!prediction || prediction.status !== 'success') {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
        <div className="flex items-center gap-2 mb-3">
          <Trophy className="w-5 h-5 text-amber-400" />
          <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
            Race Prediction
          </h3>
        </div>
        <p className="text-sm text-gray-600 dark:text-gray-400">
          Complete more workouts to get race predictions.
        </p>
      </div>
    );
  }

  const getProbabilityColor = (probability: number) => {
    if (probability >= 70) return 'text-green-600 dark:text-green-400';
    if (probability >= 40) return 'text-yellow-600 dark:text-yellow-400';
    return 'text-red-600 dark:text-red-400';
  };

  const getProbabilityBarColor = (probability: number) => {
    if (probability >= 70) return 'bg-green-500';
    if (probability >= 40) return 'bg-yellow-500';
    return 'bg-red-500';
  };

  const probability = typeof prediction.prediction.probability_of_success === 'number' 
    ? prediction.prediction.probability_of_success 
    : 0;

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Trophy className="w-5 h-5 text-amber-400" />
          <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
            Race Prediction: {prediction.prediction.goal_race_type}
          </h3>
        </div>
        <button
          onClick={loadPrediction}
          className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
          aria-label="Refresh prediction"
        >
          <RefreshCw className="w-4 h-4" />
        </button>
      </div>

      <div className="space-y-4">
        {/* Goal vs Predicted Times */}
        <div className="grid grid-cols-2 gap-4">
          <div className="text-center p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
            <div className="text-xs text-gray-500 dark:text-gray-400 uppercase mb-1">
              Your Goal
            </div>
            <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">
              {prediction.prediction.goal_time}
            </div>
          </div>
          <div className="text-center p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
            <div className="text-xs text-gray-500 dark:text-gray-400 uppercase mb-1">
              Predicted
            </div>
            <div className="text-2xl font-bold text-blue-600 dark:text-blue-400">
              {prediction.prediction.predicted_time}
            </div>
          </div>
        </div>

        {/* Success Probability */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
              Success Probability
            </span>
            <span className={`text-2xl font-bold ${getProbabilityColor(probability)}`}>
              {typeof probability === 'number' ? `${probability.toFixed(0)}%` : 'N/A'}
            </span>
          </div>
          <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-3">
            <div
              className={`h-3 rounded-full transition-all duration-500 ${getProbabilityBarColor(probability)}`}
              style={{ width: `${Math.min(typeof probability === 'number' ? probability : 0, 100)}%` }}
            ></div>
          </div>
        </div>

        {/* Current Fitness Level */}
        <div className="p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
          <div className="text-xs text-gray-500 dark:text-gray-400 uppercase mb-1">
            Current Fitness
          </div>
          <div className="text-base font-semibold text-gray-900 dark:text-gray-100">
            {prediction.prediction.current_fitness_level}
          </div>
        </div>

        {/* Recommendations */}
        {prediction.prediction.recommendations && prediction.prediction.recommendations.length > 0 && (
          <div>
            <p className="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-2">
              Recommendations:
            </p>
            <ul className="space-y-1">
              {prediction.prediction.recommendations.map((rec, idx) => (
                <li key={idx} className="text-sm text-gray-600 dark:text-gray-400 flex items-start gap-2">
                  <span className="text-blue-600 dark:text-blue-400">→</span>
                  <span>{rec}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Pacing Strategy (if available) */}
        {prediction.prediction.pacing_strategy && (
          <div className="pt-4 border-t border-gray-200 dark:border-gray-700">
            <p className="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-2 flex items-center gap-2">
              <Target className="w-4 h-4" />
              Pacing Strategy ({prediction.prediction.pacing_strategy.split_type})
            </p>
            <div className="space-y-1">
              {prediction.prediction.pacing_strategy.splits.map((split, idx) => (
                <div
                  key={idx}
                  className="flex items-center justify-between text-xs text-gray-600 dark:text-gray-400"
                >
                  <span>{split.segment}</span>
                  <div className="flex items-center gap-2">
                    <span className="text-blue-600 dark:text-blue-400">{split.target_pace}</span>
                    <span className="text-gray-500">({split.target_time})</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
