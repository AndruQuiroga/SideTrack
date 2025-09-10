'use client';

import KpiCard from '../../components/dashboard/KpiCard';
import InsightCard from '../../components/dashboard/InsightCard';
import QuickActions from '../../components/dashboard/QuickActions';

export default function DashboardPage() {
  const lastArtist = 'Daft Punk';
  const insights = [
    { id: 'new-artists', summary: '5 new artists discovered' },
    { id: 'daypart', summary: 'Afternoon energy peaked' },
    { id: 'freshness', summary: 'Catalog stayed fresh this week' },
  ];

  return (
    <section className="@container space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Overview</h1>
        <p className="text-sm text-muted-foreground">Your listening vibe at a glance</p>
      </div>

      <div className="grid gap-4 @[640px]:grid-cols-3">
        <KpiCard title="DiscoveryScore" value={72} delta={{ value: 3 }} />
        <KpiCard title="Day-part highlight" value="Evening" />
        <KpiCard title="Freshness delta" value="12%" delta={{ value: 2, suffix: '%' }} />
      </div>

      <div className="flex gap-4 overflow-x-auto pb-2">
        {insights.map((ins) => (
          <InsightCard key={ins.id} insight={ins} />
        ))}
      </div>

      <QuickActions lastArtist={lastArtist} />
    </section>
  );
}

