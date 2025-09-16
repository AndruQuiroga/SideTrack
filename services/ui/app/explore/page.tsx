'use client';

import dynamic from 'next/dynamic';
import { useSearchParams } from 'next/navigation';
import { useEffect, useRef, type ReactNode } from 'react';

import ChartSkeleton from '../../components/ChartSkeleton';
import Skeleton from '../../components/Skeleton';
import { Card } from '../../components/ui/card';
import Filters from '../../components/explore/Filters';
import Tabs from '../../components/explore/Tabs';

const TrajectoryPanel = dynamic(() => import('../../components/explore/TrajectoryPanel'), {
  loading: () => <TrajectoryPanelFallback />,
  ssr: false,
});

const MoodsPanel = dynamic(() => import('../../components/explore/MoodsPanel'), {
  loading: () => <MoodsPanelFallback />,
  ssr: false,
});

const RadarPanel = dynamic(() => import('../../components/explore/RadarPanel'), {
  loading: () => <RadarPanelFallback />,
  ssr: false,
});

const OutliersPanel = dynamic(() => import('../../components/explore/OutliersPanel'), {
  loading: () => <OutliersPanelFallback />,
  ssr: false,
});

export default function ExplorePage() {
  const searchParams = useSearchParams();
  const tab = searchParams.get('tab') ?? 'trajectory';
  const range = searchParams.get('range') ?? '12w';
  const scrollPositions = useRef<Record<string, number>>({});
  const prevTabRef = useRef(tab);

  const handleTabChange = (next: string, prev: string) => {
    scrollPositions.current[prev] = window.scrollY;
    prevTabRef.current = next;
  };

  useEffect(() => {
    const pos = scrollPositions.current[tab] ?? 0;
    window.scrollTo(0, pos);
  }, [tab]);

  let panel;
  if (tab === 'moods') panel = <MoodsPanel />;
  else if (tab === 'radar') panel = <RadarPanel />;
  else if (tab === 'outliers') panel = <OutliersPanel range={range} />;
  else panel = <TrajectoryPanel />;

  return (
    <section className="space-y-6">
      <Tabs onTabChange={handleTabChange} />
      <Filters />
      {panel}
    </section>
  );
}

function PanelHeading({ title, description }: { title: string; description?: string }) {
  return (
    <div className="flex items-center justify-between">
      <div>
        <h2 className="text-xl font-semibold">{title}</h2>
        {description && <p className="text-sm text-muted-foreground">{description}</p>}
      </div>
    </div>
  );
}

function ChartCardSkeleton({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle?: string;
  children: ReactNode;
}) {
  return (
    <Card variant="glass" className="p-4">
      <section>
        <div className="mb-3 flex items-center justify-between gap-4">
          <div>
            <h3 className="text-sm font-medium">{title}</h3>
            {subtitle && <p className="text-xs text-muted-foreground">{subtitle}</p>}
          </div>
        </div>
        <div className="min-h-[clamp(120px,25vh,160px)]">{children}</div>
      </section>
    </Card>
  );
}

function TrajectoryPanelFallback() {
  return (
    <section className="@container space-y-6">
      <PanelHeading
        title="Taste Trajectory"
        description="Weekly points (x = valence, y = energy)"
      />
      <ChartCardSkeleton title="Trajectory" subtitle="Recent weekly bubbles and positions">
        <ChartSkeleton />
      </ChartCardSkeleton>
    </section>
  );
}

function MoodsPanelFallback() {
  return (
    <section className="@container space-y-6">
      <PanelHeading title="Moods" description="Stacked axes over the last 12 weeks" />
      <div className="flex gap-2 overflow-x-auto py-2">
        {Array.from({ length: 4 }).map((_, index) => (
          <Skeleton key={index} className="h-6 w-20 rounded-full" />
        ))}
      </div>
      <ChartCardSkeleton title="Mood streamgraph" subtitle="Axes stacked by week">
        <ChartSkeleton className="h-[clamp(240px,40vh,340px)]" />
      </ChartCardSkeleton>
      <ChartCardSkeleton title="Mixtape candidates" subtitle="k-medoids picks">
        <div className="space-y-2">
          {Array.from({ length: 4 }).map((_, index) => (
            <Skeleton key={index} className="h-4 w-full" />
          ))}
        </div>
      </ChartCardSkeleton>
    </section>
  );
}

function RadarPanelFallback() {
  return (
    <section className="@container space-y-6 md:flex md:space-x-6">
      <div className="md:flex-1 space-y-6">
        <PanelHeading title="Weekly Radar" />
        <ChartCardSkeleton title="Radar" subtitle="Current week vs baseline">
          <ChartSkeleton />
        </ChartCardSkeleton>
      </div>
      <Card variant="glass" className="md:w-64 space-y-3 p-4">
        <h3 className="text-lg font-semibold">Top Contributors</h3>
        <div className="space-y-2">
          {Array.from({ length: 4 }).map((_, index) => (
            <Skeleton key={index} className="h-10 w-full" />
          ))}
        </div>
      </Card>
    </section>
  );
}

function OutliersPanelFallback() {
  return (
    <section className="@container space-y-6">
      <PanelHeading title="Outliers" />
      <ChartCardSkeleton title="Outliers" subtitle="Far from your recent centroid">
        <div className="space-y-2">
          {Array.from({ length: 5 }).map((_, index) => (
            <Skeleton key={index} className="h-4 w-full" />
          ))}
        </div>
      </ChartCardSkeleton>
    </section>
  );
}
