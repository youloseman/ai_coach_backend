'use client';

import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

interface PMCData {
  date: string;
  ctl: number;
  atl: number;
  tsb: number;
}

interface PerformanceChartProps {
  data: PMCData[];
}

export const PerformanceChart = ({ data }: PerformanceChartProps) => {
  if (!data || data.length === 0) {
    return (
      <div className="flex items-center justify-center h-64 bg-gray-50 rounded-lg">
        <p className="text-gray-500">No data available</p>
      </div>
    );
  }

  return (
    <div className="w-full">
      <ResponsiveContainer width="100%" height={400}>
        <LineChart
          data={data}
          margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
          <XAxis
            dataKey="date"
            tick={{ fontSize: 12, fill: '#6b7280' }}
            tickFormatter={(date) => {
              const d = new Date(date);
              return d.toLocaleDateString('ru-RU', { month: 'short', day: 'numeric' });
            }}
          />
          <YAxis tick={{ fontSize: 12, fill: '#6b7280' }} />
          <Tooltip
            labelFormatter={(date) => new Date(date).toLocaleDateString('ru-RU', { 
              year: 'numeric',
              month: 'long',
              day: 'numeric'
            })}
            formatter={(value: number | string) => {
              const numValue = typeof value === 'string' ? parseFloat(value) : value;
              if (typeof numValue === 'number' && !isNaN(numValue)) {
                return numValue.toFixed(1);
              }
              return 'N/A';
            }}
            contentStyle={{
              backgroundColor: '#ffffff',
              border: '1px solid #e5e7eb',
              borderRadius: '0.5rem',
              padding: '0.75rem',
            }}
          />
          <Legend
            wrapperStyle={{ paddingTop: '1rem' }}
            iconType="line"
          />
          <Line
            type="monotone"
            dataKey="ctl"
            stroke="#3b82f6"
            name="Fitness (CTL)"
            strokeWidth={2}
            dot={false}
          />
          <Line
            type="monotone"
            dataKey="atl"
            stroke="#ef4444"
            name="Fatigue (ATL)"
            strokeWidth={2}
            dot={false}
          />
          <Line
            type="monotone"
            dataKey="tsb"
            stroke="#10b981"
            name="Form (TSB)"
            strokeWidth={2}
            dot={false}
          />
        </LineChart>
      </ResponsiveContainer>

      <div className="mt-4 grid grid-cols-3 gap-4 text-sm">
        <div className="flex items-center gap-2">
          <div className="w-4 h-1 bg-blue-500 rounded"></div>
          <span className="text-gray-600">
            <strong>Fitness (CTL)</strong>: Chronic Training Load
          </span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-1 bg-red-500 rounded"></div>
          <span className="text-gray-600">
            <strong>Fatigue (ATL)</strong>: Acute Training Load
          </span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-1 bg-green-500 rounded"></div>
          <span className="text-gray-600">
            <strong>Form (TSB)</strong>: Training Stress Balance
          </span>
        </div>
      </div>
    </div>
  );
};