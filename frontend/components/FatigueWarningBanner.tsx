// components/FatigueWarningBanner.tsx
import { AlertTriangle, Info } from 'lucide-react';

interface FatigueWarningBannerProps {
  fatigueData: {
    status: string;
    overall_fatigue_level: string;
    fatigue_score: number;
    signals: Array<{
      type: string;
      severity: string;
      description: string;
    }>;
    recommendations: string[];
  } | null;
  onDismiss?: () => void;
}

export function FatigueWarningBanner({ fatigueData, onDismiss }: FatigueWarningBannerProps) {
  if (!fatigueData || fatigueData.status !== 'success') {
    return null;
  }

  const levelStr = fatigueData.overall_fatigue_level;
  if (!levelStr || typeof levelStr !== 'string') {
    return null;
  }
  const level = levelStr.toLowerCase();
  
  // Only show banner for elevated or high fatigue
  if (level === 'low' || level === 'normal') {
    return null;
  }

  const getAlertStyle = () => {
    if (level === 'high' || level === 'critical') {
      return {
        bg: 'bg-red-500/10',
        border: 'border-red-500/30',
        text: 'text-red-400',
        icon: AlertTriangle,
      };
    }
    if (level === 'elevated' || level === 'moderate') {
      return {
        bg: 'bg-amber-500/10',
        border: 'border-amber-500/30',
        text: 'text-amber-400',
        icon: Info,
      };
    }
    return {
      bg: 'bg-slate-500/10',
      border: 'border-slate-500/30',
      text: 'text-slate-400',
      icon: Info,
    };
  };

  const style = getAlertStyle();
  const Icon = style.icon;

  return (
    <div className={`${style.bg} border ${style.border} rounded-xl p-4`}>
      <div className="flex items-start gap-3">
        <Icon className={`w-5 h-5 ${style.text} flex-shrink-0 mt-0.5`} />
        
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-2 mb-2">
            <div>
              <h3 className={`text-sm font-semibold ${style.text} mb-1`}>
                {level === 'high' || level === 'critical' 
                  ? '⚠️ High Fatigue Detected' 
                  : '⚡ Elevated Fatigue'}
              </h3>
              <p className="text-xs text-slate-300">
                Fatigue score: <span className={`font-medium ${style.text}`}>
                  {fatigueData.fatigue_score}/100
                </span>
              </p>
            </div>
            {onDismiss && (
              <button
                onClick={onDismiss}
                className="text-slate-500 hover:text-slate-300 text-xs px-2 py-1"
              >
                ✕
              </button>
            )}
          </div>

          {/* Signals */}
          {fatigueData.signals && fatigueData.signals.length > 0 && (
            <div className="mb-3 space-y-1">
              {fatigueData.signals.slice(0, 3).map((signal, idx) => (
                <div key={idx} className="text-xs text-slate-300 flex items-start gap-1.5">
                  <span className="text-slate-500 mt-0.5">•</span>
                  <span>{signal.description}</span>
                </div>
              ))}
            </div>
          )}

          {/* Recommendations */}
          {fatigueData.recommendations && fatigueData.recommendations.length > 0 && (
            <div className="pt-2 border-t border-slate-700/50">
              <div className="text-[10px] text-slate-500 uppercase mb-1">
                Recommendations
              </div>
              <div className="space-y-1">
                {fatigueData.recommendations.slice(0, 2).map((rec, idx) => (
                  <div key={idx} className="text-xs text-slate-300 flex items-start gap-1.5">
                    <span className={style.text}>→</span>
                    <span>{rec}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}



