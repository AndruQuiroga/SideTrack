'use client';
import { Suspense, useEffect, useMemo, useState } from 'react';
import dynamic from 'next/dynamic';
import { apiFetch } from '../../lib/api';
import { useTrajectory } from '../../lib/query';
import ChartContainer from '../../components/ChartContainer';
import FilterBar from '../../components/FilterBar';
import Skeleton from '../../components/Skeleton';
import EmptyState from '../../components/EmptyState';

const MoodsStreamgraph = dynamic(() => import('../../components/charts/MoodsStreamgraph'), {
  loading: () => <Skeleton className="aspect-[4/3] h-[clamp(240px,40vh,340px)]" />,
  ssr: false,
});

export default function Moods() {
  const { data: traj, isLoading: trajLoading } = useTrajectory();
  const [radarLoading, setRadarLoading] = useState(false);
  const [series, setSeries] = useState<{ week: Date; [axis: string]: number | Date }[]>([]);
  const [axes] = useState<string[]>([
    'energy',
    'valence',
    'danceability',
    'brightness',
    'pumpiness',
  ]);

  useEffect(() => {
    if (!traj) return;
    let mounted = true;
    setRadarLoading(true);
    (async () => {
      try {
        const weeks = (traj.points ?? []).slice(-12).map((p) => p.week);
        const rows = await Promise.all(
          weeks.map(async (w) => {
            const r = await apiFetch(`/dashboard/radar?week=${encodeURIComponent(w)}`);
            const j = await r.json();
            return { week: new Date(j.week), ...j.axes };
          }),
        );
        if (mounted) setSeries(rows);
      } catch (e) {
        if (mounted) setSeries([]);
      } finally {
        if (mounted) setRadarLoading(false);
      }
    })();
    return () => {
      mounted = false;
    };
  }, [traj]);

  const loading = trajLoading || radarLoading;

  const content = useMemo(() => {
    if (loading) return <Skeleton className="aspect-[4/3] h-[clamp(240px,40vh,340px)]" />;
    if (!series.length)
      return <EmptyState title="No data yet" description="Ingest some listens to begin." />;
    return (
      <Suspense fallback={<Skeleton className="aspect-[4/3] h-[clamp(240px,40vh,340px)]" />}>
        <MoodsStreamgraph data={series} axes={axes} />
      </Suspense>
    );
  }, [loading, series, axes]);

  return (
    <section className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold">Moods</h2>
          <p className="text-sm text-muted-foreground">Stacked axes over the last 12 weeks</p>
        </div>
        <FilterBar
          options={[
            { label: '12w', value: '12w' },
            { label: '24w', value: '24w' },
          ]}
          value="12w"
        />
      </div>
      <ChartContainer title="Mood streamgraph" subtitle="Axes stacked by week">
        {content}
      </ChartContainer>
    </section>
  );
}
