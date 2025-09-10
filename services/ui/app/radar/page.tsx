import { Suspense } from 'react';
import dynamic from 'next/dynamic';
import ChartContainer from '../../components/ChartContainer';
import ChartSkeleton from '../../components/ChartSkeleton';
import EmptyState from '../../components/EmptyState';
import FilterBar from '../../components/FilterBar';
import { apiFetch } from '../../lib/api';

type RadarData = {
  week: string | null;
  axes: Record<string, unknown>;
  baseline: Record<string, unknown>;
};

async function getRadar(): Promise<RadarData> {
  // Pull trajectory to discover the most recent week, then build radar
  const trajRes = await apiFetch('/dashboard/trajectory', { next: { revalidate: 0 } });
  const traj = await trajRes.json();
  const last = traj.points?.[traj.points.length - 1];
  const week = last?.week;
  if (!week) return { week: null, axes: {}, baseline: {} } as RadarData;
  const res = await apiFetch(`/dashboard/radar?week=${encodeURIComponent(week)}`, {
    next: { revalidate: 0 },
  });
  if (!res.ok) throw new Error('Failed to fetch radar');
  return (await res.json()) as RadarData;
}

const RadarChart = dynamic(() => import('../../components/charts/RadarChart'), {
  ssr: false,
  loading: () => <ChartSkeleton />,
});

export default async function Radar() {
  const data = await getRadar();
  return (
    <section className="@container space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold">Weekly Radar</h2>
        <FilterBar options={[{ label: 'wk', value: 'wk' }]} value="wk" />
      </div>
      {!data.week ? (
        <EmptyState title="No data yet" description="Ingest some listens to begin." />
      ) : (
        <ChartContainer title="Radar" subtitle="Current week vs baseline">
          <Suspense fallback={<ChartSkeleton />}>
            <RadarChart
              axes={data.axes as Record<string, number>}
              baseline={data.baseline as Record<string, number>}
            />
          </Suspense>
        </ChartContainer>
      )}
    </section>
  );
}
