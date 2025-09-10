'use client';
import { Suspense, useEffect, useMemo, useState } from 'react';
import dynamic from 'next/dynamic';
import { apiFetch } from '../../../lib/api';
import { useTrajectory } from '../../../lib/query';
import ChartContainer from '../../../components/ChartContainer';
import FilterBar from '../../../components/FilterBar';
import ChartSkeleton from '../../../components/ChartSkeleton';
import EmptyState from '../../../components/EmptyState';
import ShiftMarkers, { type Shift } from '../../../components/moods/ShiftMarkers';

const MoodsStreamgraph = dynamic(() => import('../../../components/charts/MoodsStreamgraph'), {
  loading: () => <ChartSkeleton className="h-[clamp(240px,40vh,340px)]" />,
  ssr: false,
});

export default function Moods() {
  const { data: traj, isLoading: trajLoading } = useTrajectory();
  const [radarLoading, setRadarLoading] = useState(false);
  const [series, setSeries] = useState<{ week: Date; [axis: string]: number | Date }[]>([]);
  const [shifts, setShifts] = useState<Shift[]>([]);
  const [selectedWeek, setSelectedWeek] = useState<Date | null>(null);
  const [candidates, setCandidates] = useState<any[]>([]);
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

  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        const r = await apiFetch('/moods/shifts');
        const j = await r.json();
        if (mounted) setShifts(j);
      } catch {
        if (mounted) setShifts([]);
      }
    })();
    return () => {
      mounted = false;
    };
  }, []);

  useEffect(() => {
    if (!selectedWeek) {
      setCandidates([]);
      return;
    }
    let mounted = true;
    (async () => {
      try {
        const r = await apiFetch('/dashboard/outliers?limit=5');
        const j = await r.json();
        if (mounted) setCandidates(j.tracks ?? []);
      } catch {
        if (mounted) setCandidates([]);
      }
    })();
    return () => {
      mounted = false;
    };
  }, [selectedWeek]);

  const loading = trajLoading || radarLoading;

  const displaySeries = useMemo(() => {
    if (!selectedWeek) return series;
    const start = new Date(selectedWeek);
    start.setDate(start.getDate() - 14);
    const end = new Date(selectedWeek);
    end.setDate(end.getDate() + 14);
    return series.filter((s) => s.week >= start && s.week <= end);
  }, [series, selectedWeek]);

  const content = useMemo(() => {
    if (loading) return <ChartSkeleton className="h-[clamp(240px,40vh,340px)]" />;
    if (!displaySeries.length)
      return <EmptyState title="No data yet" description="Ingest some listens to begin." />;
    return (
      <Suspense fallback={<ChartSkeleton className="h-[clamp(240px,40vh,340px)]" />}> 
        <MoodsStreamgraph data={displaySeries} axes={axes} />
      </Suspense>
    );
  }, [loading, displaySeries, axes]);

  return (
    <section className="@container space-y-6">
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
      <ShiftMarkers shifts={shifts} onSelect={(w) => setSelectedWeek(new Date(w))} />
      <ChartContainer title="Mood streamgraph" subtitle="Axes stacked by week">
        {content}
      </ChartContainer>
      {!!candidates.length && (
        <ChartContainer title="Mixtape candidates" subtitle="k-medoids picks">
          <ul className="text-sm space-y-1">
            {candidates.map((t: any) => (
              <li key={t.track_id}>{t.artist} – {t.title}</li>
            ))}
          </ul>
        </ChartContainer>
      )}
    </section>
  );
}
