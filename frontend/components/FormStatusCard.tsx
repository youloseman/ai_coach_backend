// components/FormStatusCard.tsx
import { TrendingUp, TrendingDown, Minus, Activity } from 'lucide-react';

interface FormStatusCardProps {
  formStatus: {
    status: string;
    date: string;
    ctl: number;
    atl: number;
    tsb: number;
    form?: {
      label?: string;
      description?: string;
      recommendation?: string;
    };
  } | null;
  isLoading?: boolean;
}

export function FormStatusCard({ formStatus, isLoading }: FormStatusCardProps) {
  if (isLoading) {
    return (
      <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4">
        <div className="flex items-center justify-center h-32">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-sky-500" />
        </div>
      </div>
    );
  }

  if (!formStatus) {
    return (
      <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4">
        <div className="flex items-center gap-2 mb-3">
          <Activity className="w-5 h-5 text-slate-400" />
          <h2 className="text-sm font-semibold">Current Form</h2>
        </div>
        <p className="text-xs text-slate-400">
          No form data available. Connect Strava and complete some workouts.
        </p>
      </div>
    );
  }

  const getFormColor = (label: string) => {
    const l = label.toLowerCase();
    if (l.includes('fresh') || l.includes('optimal')) {
      return {
        bg: 'bg-emerald-500/10',
        border: 'border-emerald-500/30',
        text: 'text-emerald-400',
        icon: TrendingUp,
      };
    }
    if (l.includes('fatigued') || l.includes('overreaching')) {
      return {
        bg: 'bg-red-500/10',
        border: 'border-red-500/30',
        text: 'text-red-400',
        icon: TrendingDown,
      };
    }
    return {
      bg: 'bg-slate-500/10',
      border: 'border-slate-500/30',
      text: 'text-slate-400',
      icon: Minus,
    };
  };

  // Safely access form.label with fallback
  const formLabel = formStatus.form?.label || 'Unknown';
  const formColor = getFormColor(formLabel);
  const FormIcon = formColor.icon;

  return (
    <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4">
      <div className="flex items-center gap-2 mb-3">
        <Activity className="w-5 h-5 text-sky-400" />
        <h2 className="text-sm font-semibold">Current Form</h2>
      </div>

      <div className="space-y-3">
        {/* Form status badge */}
        <div className={`inline-flex items-center gap-2 px-3 py-2 rounded-lg border ${formColor.border} ${formColor.bg}`}>
          <FormIcon className={`w-4 h-4 ${formColor.text}`} />
          <span className={`text-sm font-medium ${formColor.text}`}>
            {formLabel}
          </span>
        </div>

        {/* TSB value */}
        <div className="text-xs text-slate-400">
          TSB: <span className={`font-medium ${formColor.text}`}>
            {formStatus.tsb > 0 ? '+' : ''}{formStatus.tsb.toFixed(1)}
          </span>
        </div>

        {/* Description */}
        {formStatus.form?.description && (
          <p className="text-xs text-slate-300 leading-relaxed">
            {formStatus.form.description}
          </p>
        )}

        {/* Recommendation */}
        {formStatus.form?.recommendation && (
          <div className="pt-2 border-t border-slate-800">
            <p className="text-xs text-slate-400">
              <span className="font-medium text-slate-300">Recommendation:</span>{' '}
              {formStatus.form.recommendation}
            </p>
          </div>
        )}

        {/* Detailed metrics */}
        <div className="grid grid-cols-3 gap-2 pt-2 border-t border-slate-800">
          <div className="text-center">
            <div className="text-[10px] text-slate-500 uppercase mb-0.5">Fitness</div>
            <div className="text-sm font-medium text-sky-400">
              {formStatus.ctl.toFixed(0)}
            </div>
          </div>
          <div className="text-center">
            <div className="text-[10px] text-slate-500 uppercase mb-0.5">Fatigue</div>
            <div className="text-sm font-medium text-amber-400">
              {formStatus.atl.toFixed(0)}
            </div>
          </div>
          <div className="text-center">
            <div className="text-[10px] text-slate-500 uppercase mb-0.5">Form</div>
            <div className={`text-sm font-medium ${formColor.text}`}>
              {formStatus.tsb > 0 ? '+' : ''}{formStatus.tsb.toFixed(0)}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}



