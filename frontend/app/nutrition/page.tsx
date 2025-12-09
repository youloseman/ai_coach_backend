'use client';

import { useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { nutritionAPI } from '@/lib/api';

type NutritionTargets = {
  calories: number;
  carbs_grams: number;
  protein_grams: number;
  fat_grams: number;
  breakdown?: Record<string, number>;
};

type NutritionPlan = {
  id: number;
  plan_type: string;
  race_type?: string;
  created_at?: string;
  notes?: string;
};

export default function NutritionPage() {
  const queryClient = useQueryClient();

  const { data: targets, isLoading, isError } = useQuery<NutritionTargets>({
    queryKey: ['nutritionTargets'],
    queryFn: nutritionAPI.getTargets,
    retry: 0,
  });

  const { data: plans, isLoading: plansLoading, isError: plansError } = useQuery<NutritionPlan[]>({
    queryKey: ['nutritionPlans'],
    queryFn: nutritionAPI.getPlans,
  });

  // Initialize form from targets using useMemo to avoid setState in effect
  const initialForm = useMemo<NutritionTargets>(() => {
    if (targets) {
      return {
        calories: targets.calories || 0,
        carbs_grams: targets.carbs_grams || 0,
        protein_grams: targets.protein_grams || 0,
        fat_grams: targets.fat_grams || 0,
      };
    }
    return {
      calories: 0,
      carbs_grams: 0,
      protein_grams: 0,
      fat_grams: 0,
    };
  }, [targets]);

  // Use key to reset form when targets change, avoiding setState in effect
  const formKey = useMemo(() => (targets ? JSON.stringify(initialForm) : 'empty'), [targets, initialForm]);
  const [form, setForm] = useState<NutritionTargets>(initialForm);

  const updateMutation = useMutation({
    mutationFn: () => nutritionAPI.updateTargets(form),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['nutritionTargets'] });
    },
  });

  const generatePlanMutation = useMutation({
    mutationFn: () => nutritionAPI.generateDailyPlan(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['nutritionPlans'] });
    },
  });

  return (
    <main className="min-h-screen bg-slate-950 text-slate-50 px-4 py-6">
      <div className="max-w-5xl mx-auto space-y-6">
        <header className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-semibold">Nutrition</h1>
            <p className="text-sm text-slate-400">Manage daily targets and plans.</p>
          </div>
        </header>

        <section className="bg-slate-900/70 border border-slate-800 rounded-xl p-4 space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold">Daily Targets</h2>
            {isLoading && <span className="text-xs text-slate-400">Loading...</span>}
          </div>

          {isError && (
            <p className="text-xs text-slate-400">
              No targets yet. Set your calories and macros below.
            </p>
          )}

          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
            {[
              { key: 'calories', label: 'Calories (kcal)' },
              { key: 'protein_grams', label: 'Protein (g)' },
              { key: 'carbs_grams', label: 'Carbs (g)' },
              { key: 'fat_grams', label: 'Fat (g)' },
            ].map((field) => {
              const fieldKey = field.key as keyof NutritionTargets;
              // Use key to reset input when targets change
              const inputKey = `${field.key}-${formKey}`;
              return (
                <label key={field.key} className="flex flex-col gap-1 text-slate-200">
                  <span className="text-xs text-slate-400">{field.label}</span>
                  <input
                    key={inputKey}
                    type="number"
                    defaultValue={initialForm[fieldKey]}
                    onChange={(e) =>
                      setForm((prev) => ({
                        ...prev,
                        [fieldKey]: Number(e.target.value),
                      }))
                    }
                    className="bg-slate-950/70 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:ring-1 focus:ring-sky-500"
                  />
                </label>
              );
            })}

          <button
            onClick={() => updateMutation.mutate()}
            className="px-4 py-2 bg-sky-600 hover:bg-sky-500 rounded-lg text-sm"
            disabled={updateMutation.isPending}
          >
            {updateMutation.isPending ? 'Saving...' : 'Save Targets'}
          </button>

          {updateMutation.isError && (
            <p className="text-xs text-red-400 mt-1">Failed to save targets.</p>
          )}
          {updateMutation.isSuccess && (
            <p className="text-xs text-emerald-400 mt-1">Targets saved.</p>
          )}
        </section>

        <section className="bg-slate-900/70 border border-slate-800 rounded-xl p-4 space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold">Plans</h2>
            {plansLoading && <span className="text-xs text-slate-400">Loading...</span>}
          </div>

          {plansError ? (
            <p className="text-xs text-red-400">Unable to load plans.</p>
          ) : plans && Array.isArray(plans) && plans.length > 0 ? (
            <div className="space-y-2 text-xs">
              {plans.map((plan: NutritionPlan) => (
                <div
                  key={plan.id}
                  className="bg-slate-950/60 border border-slate-800 rounded-lg px-3 py-2"
                >
                  <div className="flex justify-between">
                    <span className="text-slate-100 font-medium">
                      {plan.plan_type || 'Plan'}
                    </span>
                    <span className="text-slate-500">
                      {plan.created_at
                        ? new Date(plan.created_at).toLocaleDateString()
                        : ''}
                    </span>
                  </div>
                  {plan.notes && <div className="text-slate-400 mt-1">{plan.notes}</div>}
                </div>
              ))}
            </div>
          ) : (
            <p className="text-xs text-slate-400">No plans yet.</p>
          )}

          <button
            onClick={() => generatePlanMutation.mutate()}
            className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 rounded-lg text-sm"
            disabled={generatePlanMutation.isPending}
          >
            {generatePlanMutation.isPending ? 'Generating...' : 'Generate Daily Plan'}
          </button>
          {generatePlanMutation.isError && (
            <p className="text-xs text-red-400 mt-1">Failed to generate plan.</p>
          )}
          {generatePlanMutation.isSuccess && (
            <p className="text-xs text-emerald-400 mt-1">Plan generated.</p>
          )}
        </section>
      </div>
    </main>
  );
}

