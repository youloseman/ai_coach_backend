// components/ActivityCard.tsx
import { Activity, Clock, TrendingUp, Heart } from 'lucide-react';

interface ActivityCardProps {
  activity: {
    id?: number;
    name: string;
    sport_type: string;
    start_date: string;
    distance_m?: number;
    moving_time_s?: number;
    total_elevation_gain_m?: number;
    average_heartrate?: number;
    average_speed_m_s?: number;
  };
}

export function ActivityCard({ activity }: ActivityCardProps) {
  const formatDistance = (meters: number | undefined): string => {
    if (!meters) return '--';
    const km = meters / 1000;
    return `${km.toFixed(2)} km`;
  };

  const formatDuration = (seconds: number | undefined): string => {
    if (!seconds) return '--';
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    if (hours > 0) {
      return `${hours}h ${minutes}m`;
    }
    return `${minutes}m`;
  };

  const formatPace = (metersPerSecond: number | undefined, distanceMeters: number | undefined): string => {
    if (!metersPerSecond || !distanceMeters) return '--';
    const kmPerHour = metersPerSecond * 3.6;
    
    // For running, show min/km
    const sportType = typeof activity.sport_type === 'string' ? activity.sport_type.toLowerCase() : '';
    if (sportType.includes('run')) {
      const minPerKm = 60 / kmPerHour;
      const minutes = Math.floor(minPerKm);
      const seconds = Math.round((minPerKm - minutes) * 60);
      return `${minutes}:${seconds.toString().padStart(2, '0')}/km`;
    }
    
    // For cycling/other, show km/h
    return `${kmPerHour.toFixed(1)} km/h`;
  };

  const getSportIcon = () => {
    const sport = typeof activity.sport_type === 'string' ? activity.sport_type.toLowerCase() : '';
    if (sport.includes('run')) return '🏃';
    if (sport.includes('ride') || sport.includes('bike')) return '🚴';
    if (sport.includes('swim')) return '🏊';
    return '💪';
  };

  const getSportColor = () => {
    const sport = typeof activity.sport_type === 'string' ? activity.sport_type.toLowerCase() : '';
    if (sport.includes('run')) return 'text-amber-400 border-amber-500/30 bg-amber-500/10';
    if (sport.includes('ride') || sport.includes('bike')) return 'text-sky-400 border-sky-500/30 bg-sky-500/10';
    if (sport.includes('swim')) return 'text-cyan-400 border-cyan-500/30 bg-cyan-500/10';
    return 'text-slate-400 border-slate-500/30 bg-slate-500/10';
  };

  const formatDate = (dateStr: string): string => {
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

    if (diffDays === 0) return 'Today';
    if (diffDays === 1) return 'Yesterday';
    if (diffDays < 7) return `${diffDays} days ago`;
    
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  };

  return (
    <div className="bg-slate-900/60 border border-slate-800 rounded-lg p-3 hover:border-slate-700 transition-colors">
      <div className="flex items-start justify-between gap-2 mb-2">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className={`text-base px-2 py-0.5 rounded border ${getSportColor()}`}>
              {getSportIcon()}
            </span>
            <h3 className="text-sm font-medium text-slate-100 truncate">
              {activity.name}
            </h3>
          </div>
          <p className="text-xs text-slate-400">
            {formatDate(activity.start_date)}
          </p>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-2 text-xs">
        {activity.distance_m && (
          <div className="flex items-center gap-1.5 text-slate-300">
            <Activity className="w-3.5 h-3.5 text-slate-500" />
            <span>{formatDistance(activity.distance_m)}</span>
          </div>
        )}
        
        {activity.moving_time_s && (
          <div className="flex items-center gap-1.5 text-slate-300">
            <Clock className="w-3.5 h-3.5 text-slate-500" />
            <span>{formatDuration(activity.moving_time_s)}</span>
          </div>
        )}
        
        {activity.average_speed_m_s && (
          <div className="flex items-center gap-1.5 text-slate-300">
            <TrendingUp className="w-3.5 h-3.5 text-slate-500" />
            <span>{formatPace(activity.average_speed_m_s, activity.distance_m)}</span>
          </div>
        )}
        
        {activity.average_heartrate && (
          <div className="flex items-center gap-1.5 text-slate-300">
            <Heart className="w-3.5 h-3.5 text-slate-500" />
            <span>{Math.round(activity.average_heartrate)} bpm</span>
          </div>
        )}
        
        {activity.total_elevation_gain_m && activity.total_elevation_gain_m > 0 && (
          <div className="flex items-center gap-1.5 text-slate-300">
            <span className="text-slate-500">⛰️</span>
            <span>{Math.round(activity.total_elevation_gain_m)}m</span>
          </div>
        )}
      </div>
    </div>
  );
}



