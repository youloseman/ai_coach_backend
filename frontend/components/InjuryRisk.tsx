'use client';

import { useQuery } from '@tanstack/react-query';
import { analyticsAPI } from '@/lib/api';

type RiskLevel = 'low' | 'moderate' | 'high';

interface InjuryRiskData {
  risk_level: RiskLevel;
  score: number;
  factors: string[];
  recommendation: string;
  updated_at?: string;
}

const riskColors: Record<RiskLevel, string> = {
  low: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30',
  moderate: 'text-amber-400 bg-amber-500/10 border-amber-500/30',
  high: 'text-red-400 bg-red-500/10 border-red-500/30',
};

const riskLabels: Record<RiskLevel, string> = {
  low: 'LOW',
  moderate: 'MODERATE',
  high: 'HIGH',
};

export function InjuryRiskCard() {
  const {
    data,
    isLoading,
    isError,
  } = useQuery<InjuryRiskData>({
    queryKey: ['injuryRisk'],
    queryFn: async () => {
      const response = await analyticsAPI.getInjuryRisk();
      return response;
    },
  });

  const riskLevel: RiskLevel = data?.risk_level || 'low';
  const color = riskColors[riskLevel];

  return (
    <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 h-full flex flex-col">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="text-lg">🏥</span>
          <h2 className="text-sm font-semibold">Injury Risk</h2>
        </div>
        <span className={`px-2 py-1 rounded-md border text-[11px] ${color}`}>
          {riskLabels[riskLevel]}
        </span>
      </div>

      {isLoading ? (
        <div className="text-slate-500 text-xs">Loading injury risk...</div>
      ) : isError || !data ? (
        <div className="text-slate-500 text-xs">
          Unable to load injury risk. Try again later.
        </div>
      ) : (
        <>
          <div className="text-xs text-slate-300 mb-2">
            Risk Score:{' '}
            <span className="text-slate-100 font-semibold">
              {Math.round(data.score)}/100
            </span>
          </div>

          {data.factors && data.factors.length > 0 && (
            <div className="text-xs text-slate-400 space-y-1 mb-2">
              <div className="font-semibold text-slate-300">Risk Factors:</div>
              <ul className="list-disc list-inside space-y-1">
                {data.factors.map((f, idx) => (
                  <li key={idx}>{f}</li>
                ))}
              </ul>
            </div>
          )}

          {data.recommendation && (
            <div className="text-xs text-slate-300">
              <span className="font-semibold text-slate-100">Recommendation: </span>
              {data.recommendation}
            </div>
          )}

          {data.updated_at && (
            <div className="text-[11px] text-slate-500 mt-3">
              Last updated: {new Date(data.updated_at).toLocaleDateString()}
            </div>
          )}
        </>
      )}
    </div>
  );
}


