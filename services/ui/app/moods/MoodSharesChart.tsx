'use client';

import { AreaChart, Area, XAxis, YAxis, Tooltip, CartesianGrid } from 'recharts';

const AXES = ['energy', 'valence', 'danceability', 'brightness', 'pumpiness'] as const;
const COLORS: Record<typeof AXES[number], string> = {
  energy: '#8884d8',
  valence: '#82ca9d',
  danceability: '#ffc658',
  brightness: '#ff7300',
  pumpiness: '#a4de6c',
};

interface MoodSharesChartProps {
  data: Array<Record<string, number | string>>;
}

export default function MoodSharesChart({ data }: MoodSharesChartProps) {
  return (
    <AreaChart width={600} height={300} data={data}>
      <CartesianGrid strokeDasharray="3 3" />
      <XAxis dataKey="week" />
      <YAxis />
      <Tooltip />
      {AXES.map((ax) => (
        <Area key={ax} type="monotone" dataKey={ax} stackId="1" stroke={COLORS[ax]} fill={COLORS[ax]} />
      ))}
    </AreaChart>
  );
}
