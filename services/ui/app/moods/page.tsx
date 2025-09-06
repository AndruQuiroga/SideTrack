'use client';
import { useEffect, useMemo, useState } from 'react';
import { apiFetch } from '../../lib/api';
import MoodsStreamgraph from '../../components/charts/MoodsStreamgraph';
import ChartContainer from '../../components/ChartContainer';
import FilterBar from '../../components/FilterBar';
import { Card } from '../../components/ui/card';

type Trajectory = { points: { week: string }[] };

export default function Moods() {
  const [loading, setLoading] = useState(true);
  const [series, setSeries] = useState<{ week: Date; [axis: string]: number | Date }[]>([]);
  const [axes] = useState<string[]>([
    'energy',
    'valence',
    'danceability',
    'brightness',
    'pumpiness',
  ]);

  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        const trajRes = await apiFetch('/dashboard/trajectory');
        const traj: Trajectory = await trajRes.json();
        const weeks = (traj.points ?? []).slice(-12).map((p) => p.week);
        const rows = await Promise.all(
          weeks.map(async (w) => {
            const r = await apiFetch(`/dashboard/radar?week=${encodeURIComponent(w)}`);
            const j = await r.json();
            return { week: new Date(j.week), ...j.axes };
          }),
        );
        if (!mounted) return;
        setSeries(rows);
      } catch (e) {
        setSeries([]);
      } finally {
        setLoading(false);
      }
    })();
    return () => {
      mounted = false;
    };
  }, []);

  const content = useMemo(() => {
    if (loading) return <Card variant="glass" className="h-[340px] w-full" />;
    if (!series.length) return <div className="text-sm text-muted-foreground">No data yet.</div>;
    return <MoodsStreamgraph data={series} axes={axes} />;
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
