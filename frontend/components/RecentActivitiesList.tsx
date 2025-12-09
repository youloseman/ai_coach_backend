'use client';

import { useEffect, useState } from 'react';
import { stravaAPI } from '@/lib/api';
import type { StravaActivity } from '@/types';

// Import the existing ActivityCard component
import { ActivityCard } from './ActivityCard';

export default function RecentActivitiesList() {
  const [activities, setActivities] = useState<StravaActivity[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadActivities = async () => {
      try {
        setLoading(true);
        setError(null);
        const data = await stravaAPI.getActivities(1, 10);
        setActivities(Array.isArray(data) ? data : []);
      } catch (err) {
        console.error('Failed to load activities:', err);
        setError('Failed to load activities');
      } finally {
        setLoading(false);
      }
    };

    loadActivities();
  }, []);

  if (loading) {
    return (
      <div className="space-y-4">
        {[1, 2, 3].map((i) => (
          <div
            key={i}
            className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4 animate-pulse"
          >
            <div className="flex items-start gap-3">
              <div className="w-10 h-10 bg-gray-200 dark:bg-gray-700 rounded"></div>
              <div className="flex-1 space-y-2">
                <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-3/4"></div>
                <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded w-1/2"></div>
                <div className="grid grid-cols-2 gap-2">
                  <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded"></div>
                  <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded"></div>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-6 text-center">
        <p className="text-sm text-gray-600 dark:text-gray-400">
          Failed to load activities. Please try again later.
        </p>
      </div>
    );
  }

  if (!activities || activities.length === 0) {
    return (
      <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-6 text-center">
        <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">
          No activities yet
        </p>
        <p className="text-xs text-gray-500 dark:text-gray-500">
          Connect your Strava account and complete some workouts to see them here.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {activities.map((activity) => (
        <ActivityCard key={activity.id || Math.random()} activity={activity} />
      ))}
    </div>
  );
}

