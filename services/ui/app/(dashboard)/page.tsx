'use client';

import KpiCard from '../../components/dashboard/KpiCard';
import InsightCard from '../../components/dashboard/InsightCard';
import QuickActions from '../../components/dashboard/QuickActions';
import Skeleton from '../../components/Skeleton';
import { useDashboard } from '../../lib/query';

export default function DashboardPage() {
  const { data, isLoading, error } = useDashboard();

  if (error) {
    return (
      <section className="@container space-y-6">
        <p className="text-sm text-rose-400">
          Failed to load dashboard: {(error as Error).message}
        </p>
      </section>
    );
  }

  return (
    <section className="@container space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Overview</h1>
        <p className="text-sm text-muted-foreground">Your listening vibe at a glance</p>
      </div>

      <div className="grid gap-4 @[640px]:grid-cols-3">
        {isLoading
          ? [1, 2, 3].map((i) => <Skeleton key={i} className="h-24" />)
          : data?.kpis.map((kpi) => <KpiCard key={kpi.id} kpi={kpi} />)}
      </div>

      <div className="flex gap-4 overflow-x-auto pb-2">
        {isLoading
          ? [1, 2, 3].map((i) => <Skeleton key={i} className="h-24 min-w-[200px]" />)
          : data?.insights.map((ins) => <InsightCard key={ins.id} insight={ins} />)}
      </div>

      {isLoading ? (
        <Skeleton className="h-32" />
      ) : (
        <QuickActions lastArtist={data?.lastArtist ?? ''} />
      )}
    </section>
  );
}
