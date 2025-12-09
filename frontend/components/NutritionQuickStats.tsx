'use client';

import { useQuery } from '@tanstack/react-query';
import { nutritionAPI } from '@/lib/api';

interface NutritionTargets {
  calories_kcal?: number;
  protein_g?: number;
  carbs_g?: number;
  fats_g?: number;
  water_l?: number;
  updated_at?: string;
}

export function NutritionQuickStats() {
  const { data, isLoading, isError } = useQuery<NutritionTargets>({
    queryKey: ['nutritionTargets'],
    queryFn: async () => {
      const res = await nutritionAPI.getTargets();
      return res;
    },
  });

  return (
    <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className="text-lg">🍎</span>
          <h2 className="text-sm font-semibold">Daily Targets</h2>
        </div>
        <a
          href="/coach"
          className="text-[11px] text-sky-400 hover:text-sky-300 underline"
        >
          Manage →
        </a>
      </div>

      {isLoading ? (
        <div className="text-slate-500 text-xs">Loading nutrition targets...</div>
      ) : isError || !data ? (
        <div className="text-slate-500 text-xs">
          Unable to load nutrition targets.
        </div>
      ) : (
        <div className="text-xs text-slate-200 space-y-1">
          <div className="flex items-center justify-between">
            <span>Calories</span>
            <span className="text-slate-100">
              {data.calories_kcal ? `${data.calories_kcal} kcal` : '--'}
            </span>
          </div>
          <div className="flex items-center justify-between">
            <span>Protein</span>
            <span className="text-slate-100">
              {data.protein_g ? `${data.protein_g}g` : '--'}
            </span>
          </div>
          <div className="flex items-center justify-between">
            <span>Carbs</span>
            <span className="text-slate-100">
              {data.carbs_g ? `${data.carbs_g}g` : '--'}
            </span>
          </div>
          <div className="flex items-center justify-between">
            <span>Water</span>
            <span className="text-slate-100">
              {data.water_l ? `${data.water_l.toFixed(1)} L` : '--'}
            </span>
          </div>
          {data.updated_at && (
            <div className="text-[11px] text-slate-500 pt-1">
              Updated {new Date(data.updated_at).toLocaleDateString()}
            </div>
          )}
        </div>
      )}
    </div>
  );
}


