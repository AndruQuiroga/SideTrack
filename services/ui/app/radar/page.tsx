import { Suspense } from 'react';
import dynamic from 'next/dynamic';
import ChartContainer from '../../components/ChartContainer';
import Skeleton from '../../components/Skeleton';
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
  loading: () => <Skeleton className="aspect-[4/3] h-[clamp(240px,40vh,380px)]" />,
});

export default async function Radar() {
  const data = await getRadar();
  return (
    <section className="space-y-4">
      <h2 className="text-xl font-semibold">Weekly Radar</h2>
      {!data.week ? (
        <p>No data yet. Ingest some listens to begin.</p>
      ) : (
        <ChartContainer title="Radar" subtitle="Current week vs baseline">
          <Suspense fallback={<Skeleton className="aspect-[4/3] h-[clamp(240px,40vh,380px)]" />}>
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
