// components/ActivityCard.tsx
import { Activity, Clock, TrendingUp, Heart } from 'lucide-react';
import type { StravaActivity } from '@/types';

interface ActivityCardProps {
  activity: StravaActivity;
}

export function ActivityCard({ activity }: ActivityCardProps) {
  // Helper to get distance in meters (supports both field names)
  const getDistanceMeters = (): number | undefined => {
    return activity.distance_meters || activity.distance_m;
  };

  // Helper to get moving time in seconds (supports both field names)
  const getMovingTimeSeconds = (): number | undefined => {
    return activity.moving_time_seconds || activity.moving_time_s;
  };

  // Helper to get elevation gain (supports both field names)
  const getElevationGain = (): number | undefined => {
    return activity.total_elevation_gain || activity.total_elevation_gain_m;
  };

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

  const formatPace = (distanceMeters: number | undefined, timeSeconds: number | undefined): string => {
    if (!distanceMeters || !timeSeconds || distanceMeters === 0) return '--';
    
    const sportType = typeof activity.sport_type === 'string' ? activity.sport_type.toLowerCase() : '';
    
    // For running, show min/km
    if (sportType.includes('run')) {
      const minPerKm = (timeSeconds / 60) / (distanceMeters / 1000);
      const minutes = Math.floor(minPerKm);
      const seconds = Math.round((minPerKm - minutes) * 60);
      return `${minutes}:${seconds.toString().padStart(2, '0')}/km`;
    }
    
    // For cycling/other, show km/h
    const kmPerHour = (distanceMeters / 1000) / (timeSeconds / 3600);
    return `${kmPerHour.toFixed(1)} km/h`;
  };

  const getSportIcon = () => {
    const sport = typeof activity.sport_type === 'string' ? activity.sport_type.toLowerCase() : '';
    if (sport.includes('run')) return '🏃';
    if (sport.includes('ride') || sport.includes('bike') || sport.includes('cycling')) return '🚴';
    if (sport.includes('swim')) return '🏊';
    return '💪';
  };

  const getSportColor = () => {
    const sport = typeof activity.sport_type === 'string' ? activity.sport_type.toLowerCase() : '';
    if (sport.includes('run')) return 'bg-orange-100 text-orange-800 border-orange-300 dark:bg-orange-900/20 dark:text-orange-400 dark:border-orange-700';
    if (sport.includes('ride') || sport.includes('bike') || sport.includes('cycling')) return 'bg-purple-100 text-purple-800 border-purple-300 dark:bg-purple-900/20 dark:text-purple-400 dark:border-purple-700';
    if (sport.includes('swim')) return 'bg-cyan-100 text-cyan-800 border-cyan-300 dark:bg-cyan-900/20 dark:text-cyan-400 dark:border-cyan-700';
    return 'bg-gray-100 text-gray-800 border-gray-300 dark:bg-gray-700 dark:text-gray-300 dark:border-gray-600';
  };

  const formatDate = (dateStr: string): string => {
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

    if (diffDays === 0) return 'Today';
    if (diffDays === 1) return 'Yesterday';
    if (diffDays < 7) return `${diffDays} days ago`;
    
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  };

  const distanceMeters = getDistanceMeters();
  const movingTimeSeconds = getMovingTimeSeconds();
  const elevationGain = getElevationGain();

  return (
    <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 hover:border-slate-600 transition-colors">
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex items-center gap-2 flex-1 min-w-0">
          <span className="text-2xl">{getSportIcon()}</span>
          <div className="flex-1 min-w-0">
            <h3 className="text-base font-medium text-slate-100 truncate">
              {activity.name}
            </h3>
            <p className="text-xs text-slate-400">
              {formatDate(activity.start_date)}
            </p>
          </div>
        </div>
        <span className={`px-2 py-1 text-xs font-medium rounded-md border ${getSportColor()}`}>
          {activity.sport_type}
        </span>
      </div>

      <div className="grid grid-cols-2 gap-3">
        {distanceMeters && (
          <div className="flex flex-col">
            <div className="flex items-center gap-1.5 text-gray-500 dark:text-gray-400 text-xs mb-1">
              <Activity className="w-3.5 h-3.5" />
              <span>Distance</span>
            </div>
            <span className="text-sm font-semibold text-gray-900 dark:text-gray-100">
              {formatDistance(distanceMeters)}
            </span>
          </div>
        )}
        
        {movingTimeSeconds && (
          <div className="flex flex-col">
            <div className="flex items-center gap-1.5 text-gray-500 dark:text-gray-400 text-xs mb-1">
              <Clock className="w-3.5 h-3.5" />
              <span>Duration</span>
            </div>
            <span className="text-sm font-semibold text-gray-900 dark:text-gray-100">
              {formatDuration(movingTimeSeconds)}
            </span>
          </div>
        )}
        
        {distanceMeters && movingTimeSeconds && (
          <div className="flex flex-col">
            <div className="flex items-center gap-1.5 text-gray-500 dark:text-gray-400 text-xs mb-1">
              <TrendingUp className="w-3.5 h-3.5" />
              <span>Pace</span>
            </div>
            <span className="text-sm font-semibold text-gray-900 dark:text-gray-100">
              {formatPace(distanceMeters, movingTimeSeconds)}
            </span>
          </div>
        )}
        
        {activity.average_heartrate && (
          <div className="flex flex-col">
            <div className="flex items-center gap-1.5 text-gray-500 dark:text-gray-400 text-xs mb-1">
              <Heart className="w-3.5 h-3.5" />
              <span>Avg HR</span>
            </div>
            <span className="text-sm font-semibold text-gray-900 dark:text-gray-100">
              {Math.round(activity.average_heartrate)} bpm
            </span>
          </div>
        )}
        
        {elevationGain && elevationGain > 0 && (
          <div className="flex flex-col">
            <div className="flex items-center gap-1.5 text-gray-500 dark:text-gray-400 text-xs mb-1">
              <span>⛰️</span>
              <span>Elevation</span>
            </div>
            <span className="text-sm font-semibold text-gray-900 dark:text-gray-100">
              {Math.round(elevationGain)}m
            </span>
          </div>
        )}

        {activity.tss && (
          <div className="flex flex-col">
            <div className="flex items-center gap-1.5 text-gray-500 dark:text-gray-400 text-xs mb-1">
              <span>📊</span>
              <span>TSS</span>
            </div>
            <span className="text-sm font-semibold text-gray-900 dark:text-gray-100">
              {Math.round(activity.tss)}
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
