// frontend/components/charts/PMCChart.tsx

'use client';

import React, { useEffect, useState } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceLine
} from 'recharts';
import { analyticsAPI } from '@/lib/api';

interface PMCData {
  dates: string[];
  ctl: number[];
  atl: number[];
  tsb: number[];
  rr?: number[];
}

interface ChartDataPoint {
  date: string;
  fullDate: string;
  CTL: number;
  ATL: number;
  TSB: number;
}

export function PMCChart() {
  const [data, setData] = useState<ChartDataPoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      setError(null);
      const pmc: PMCData = await analyticsAPI.getPMC();
      
      if (!pmc.dates || pmc.dates.length === 0) {
        setError('No PMC data available. Connect Strava to see your performance chart.');
        return;
      }
      
      // Transform for Recharts - show last 90 days
      const last90Days = pmc.dates.slice(-90);
      const chartData: ChartDataPoint[] = last90Days.map((date) => {
        const idx = pmc.dates.indexOf(date);
        return {
          date: new Date(date).toLocaleDateString('en-US', {
            month: 'short',
            day: 'numeric'
          }),
          fullDate: date,
          CTL: Math.round(pmc.ctl[idx] * 10) / 10,
          ATL: Math.round(pmc.atl[idx] * 10) / 10,
          TSB: Math.round(pmc.tsb[idx] * 10) / 10
        };
      });
      
      setData(chartData);
    } catch (err) {
      console.error('Failed to fetch PMC:', err);
      setError('Failed to load PMC data. Please try again later.');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-6">
        <h2 className="text-2xl font-bold mb-4 text-slate-100">Performance Management Chart</h2>
        <div className="flex items-center justify-center h-96">
          <div className="text-slate-400 animate-pulse">Loading PMC Chart...</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-6">
        <h2 className="text-2xl font-bold mb-4 text-slate-100">Performance Management Chart</h2>
        <div className="flex items-center justify-center h-96">
          <div className="text-slate-400 text-center">
            <p>{error}</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-6">
      <h2 className="text-2xl font-bold mb-4 text-slate-100">Performance Management Chart</h2>
      <div className="h-96">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="#475569" />
            
            <XAxis
              dataKey="date"
              tick={{ fontSize: 12, fill: '#94a3b8' }}
              stroke="#64748b"
              interval="preserveStartEnd"
            />
            
            <YAxis
              tick={{ fontSize: 12, fill: '#94a3b8' }}
              stroke="#64748b"
            />
            
            <Tooltip
              contentStyle={{
                backgroundColor: '#1e293b',
                border: '1px solid #334155',
                borderRadius: '8px',
                color: '#f1f5f9'
              }}
              labelStyle={{ color: '#94a3b8' }}
            />
            
            <Legend
              wrapperStyle={{ paddingTop: '20px', color: '#94a3b8' }}
            />
            
            {/* TSB Reference Lines */}
            <ReferenceLine
              y={-30}
              stroke="#ef4444"
              strokeDasharray="3 3"
              label={{ value: 'Overtraining Risk', position: 'right', fill: '#ef4444', fontSize: 10 }}
            />
            <ReferenceLine
              y={-5}
              stroke="#10b981"
              strokeDasharray="3 3"
              strokeOpacity={0.5}
            />
            <ReferenceLine
              y={15}
              stroke="#f59e0b"
              strokeDasharray="3 3"
              label={{ value: 'Detraining Risk', position: 'right', fill: '#f59e0b', fontSize: 10 }}
            />
            <ReferenceLine
              y={0}
              stroke="#64748b"
              strokeDasharray="2 2"
              strokeOpacity={0.3}
            />
            
            {/* Lines */}
            <Line
              type="monotone"
              dataKey="CTL"
              stroke="#3b82f6"
              strokeWidth={2}
              dot={false}
              name="CTL (Fitness)"
            />
            <Line
              type="monotone"
              dataKey="ATL"
              stroke="#ef4444"
              strokeWidth={2}
              dot={false}
              name="ATL (Fatigue)"
            />
            <Line
              type="monotone"
              dataKey="TSB"
              stroke="#10b981"
              strokeWidth={2}
              dot={false}
              name="TSB (Form)"
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <div className="mt-4 text-sm text-slate-400 space-y-1">
        <p><strong className="text-slate-300">CTL (Fitness):</strong> Chronic Training Load - your long-term fitness level</p>
        <p><strong className="text-slate-300">ATL (Fatigue):</strong> Acute Training Load - your recent training stress</p>
        <p><strong className="text-slate-300">TSB (Form):</strong> Training Stress Balance - CTL - ATL (positive = fresh, negative = fatigued)</p>
      </div>
    </div>
  );
}

