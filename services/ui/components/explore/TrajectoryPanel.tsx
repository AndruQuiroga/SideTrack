import { Suspense } from 'react';
import dynamic from 'next/dynamic';
import ChartContainer from '../ChartContainer';
import ChartSkeleton from '../ChartSkeleton';

const TrajectoryClient = dynamic(() => import('../charts/TrajectoryClient'), {
  loading: () => <ChartSkeleton />,
  ssr: false,
});

export default function TrajectoryPanel() {
  return (
    <section className="@container space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold">Taste Trajectory</h2>
          <p className="text-sm text-muted-foreground">Weekly points (x = valence, y = energy)</p>
        </div>
      </div>
      <ChartContainer title="Trajectory" subtitle="Recent weekly bubbles and positions">
        <Suspense fallback={<ChartSkeleton />}>
          <TrajectoryClient />
        </Suspense>
      </ChartContainer>
    </section>
  );
}
