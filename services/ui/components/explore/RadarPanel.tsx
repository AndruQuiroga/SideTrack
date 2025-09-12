'use client';
import { useEffect, useState, Suspense } from 'react';
import dynamic from 'next/dynamic';
import ChartContainer from '../ChartContainer';
import ChartSkeleton from '../ChartSkeleton';
import EmptyState from '../EmptyState';
import { apiFetch } from '../../lib/api';
import InfluencePanel from '../radar/InfluencePanel';

const RadarChart = dynamic(() => import('../charts/RadarChart'), {
  ssr: false,
  loading: () => <ChartSkeleton />,
});

type RadarData = {
  week: string | null;
  axes: Record<string, number>;
  baseline: Record<string, number>;
};

async function fetchRadar(cohort?: string): Promise<RadarData> {
  const trajRes = await apiFetch('/api/dashboard/trajectory');
  const traj = await trajRes.json();
  const last = traj.points?.[traj.points.length - 1];
  const week = last?.week;
  if (!week) return { week: null, axes: {}, baseline: {} } as RadarData;
  const cohortParam = cohort ? `&cohort=${encodeURIComponent(cohort)}` : '';
  const res = await apiFetch(`/api/dashboard/radar?week=${encodeURIComponent(week)}${cohortParam}`);
  return (await res.json()) as RadarData;
}

export default function RadarPanel() {
  const [data, setData] = useState<RadarData>({
    week: null,
    axes: {},
    baseline: {},
  });
  const [filter, setFilter] = useState<string | null>(null);

  useEffect(() => {
    fetchRadar(filter)
      .then(setData)
      .catch(() => setData({ week: null, axes: {}, baseline: {} }));
  }, [filter]);

  const axes = data.axes;
  const baseline = data.baseline;

  return (
    <section className="@container space-y-6 md:flex md:space-x-6">
      <div className="md:flex-1 space-y-6">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-semibold">Weekly Radar</h2>
        </div>
        {!data.week ? (
          <EmptyState title="No data yet" description="Ingest some listens to begin." />
        ) : (
          <ChartContainer title="Radar" subtitle="Current week vs baseline">
            <Suspense fallback={<ChartSkeleton />}>
              <RadarChart axes={axes} baseline={baseline} />
            </Suspense>
          </ChartContainer>
        )}
      </div>
      <InfluencePanel onSelect={setFilter} />
    </section>
  );
}
