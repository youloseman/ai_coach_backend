// components/RacePredictionCard.tsx
import { Trophy, Target } from 'lucide-react';

interface Prediction {
  race_type: string;
  predicted_time: string;
  predicted_time_seconds: number;
  confidence: string;
  pace_per_km?: string;
  based_on?: {
    effort_type: string;
    time: string;
    date: string;
  };
}

interface BestEffort {
  time?: string;
  formatted_time?: string;
}

interface RacePredictionCardProps {
  predictions: {
    status: string;
    sport: string;
    predictions: Prediction[];
    best_efforts?: Record<string, BestEffort>;
  } | null;
  isLoading?: boolean;
}

export function RacePredictionCard({ predictions, isLoading }: RacePredictionCardProps) {
  if (isLoading) {
    return (
      <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4">
        <div className="flex items-center justify-center h-32">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-sky-500" />
        </div>
      </div>
    );
  }

  if (!predictions || predictions.status !== 'success') {
    return (
      <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4">
        <div className="flex items-center gap-2 mb-3">
          <Trophy className="w-5 h-5 text-amber-400" />
          <h2 className="text-sm font-semibold">Race Predictions</h2>
        </div>
        <p className="text-xs text-slate-400">
          Complete some benchmark workouts (5K, 10K, HM) to get race predictions.
        </p>
      </div>
    );
  }

  const getConfidenceColor = (confidence: string) => {
    if (!confidence || typeof confidence !== 'string') return 'text-slate-400';
    const c = confidence.toLowerCase();
    if (c.includes('high')) return 'text-emerald-400';
    if (c.includes('medium')) return 'text-amber-400';
    return 'text-slate-400';
  };

  const getRaceIcon = (raceType: string) => {
    if (raceType === '5K') return '🏃‍♂️';
    if (raceType === '10K') return '🏃';
    if (raceType === 'HM') return '🏃‍♀️';
    if (raceType === 'Marathon') return '🏅';
    return '🎯';
  };

  return (
    <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4">
      <div className="flex items-center gap-2 mb-3">
        <Trophy className="w-5 h-5 text-amber-400" />
        <h2 className="text-sm font-semibold">Race Predictions</h2>
      </div>

      <div className="space-y-2">
        {predictions.predictions.map((pred, idx) => (
          <div
            key={idx}
            className="bg-slate-950/60 border border-slate-800 rounded-lg p-3 hover:border-slate-700 transition-colors"
          >
            <div className="flex items-start justify-between gap-2 mb-2">
              <div className="flex items-center gap-2">
                <span className="text-lg">{getRaceIcon(pred.race_type)}</span>
                <div>
                  <div className="text-sm font-medium text-slate-100">
                    {pred.race_type}
                  </div>
                  {pred.pace_per_km && (
                    <div className="text-[10px] text-slate-500">
                      {pred.pace_per_km}/km pace
                    </div>
                  )}
                </div>
              </div>
              <div className="text-right">
                <div className="text-base font-semibold text-sky-400">
                  {pred.predicted_time}
                </div>
                <div className={`text-[10px] ${getConfidenceColor(pred.confidence)}`}>
                  {pred.confidence} confidence
                </div>
              </div>
            </div>

            {pred.based_on && (
              <div className="text-[10px] text-slate-500 flex items-center gap-1">
                <Target className="w-3 h-3" />
                Based on {pred.based_on.effort_type} ({pred.based_on.time})
              </div>
            )}
          </div>
        ))}
      </div>

      {predictions.best_efforts && Object.keys(predictions.best_efforts).length > 0 && (
        <div className="mt-3 pt-3 border-t border-slate-800">
          <div className="text-[10px] text-slate-500 uppercase mb-2">
            Best Recent Efforts
          </div>
          <div className="grid grid-cols-2 gap-2 text-xs">
            {Object.entries(predictions.best_efforts).map(([key, effort]: [string, BestEffort]) => (
              <div key={key} className="flex items-center justify-between text-slate-400">
                <span className="capitalize">{key.replace('_', ' ')}</span>
                <span className="text-slate-300">{effort.time || effort.formatted_time}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}



