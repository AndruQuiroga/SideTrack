import { Suspense } from 'react';
import dynamic from 'next/dynamic';
import ChartContainer from '../../components/ChartContainer';
import FilterBar from '../../components/FilterBar';
import ChartSkeleton from '../../components/ChartSkeleton';

const TrajectoryClient = dynamic(() => import('../../components/charts/TrajectoryClient'), {
  loading: () => <ChartSkeleton />,
  ssr: false,
});

export default async function Trajectory() {
  return (
    <section className="@container space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold">Taste Trajectory</h2>
          <p className="text-sm text-muted-foreground">Weekly points (x = valence, y = energy)</p>
        </div>
        <FilterBar
          options={[
            { label: '12w', value: '12w' },
            { label: '24w', value: '24w' },
            { label: '52w', value: '52w' },
          ]}
          value="12w"
        />
      </div>
      <ChartContainer title="Trajectory" subtitle="Recent weekly bubbles and positions">
        <Suspense fallback={<ChartSkeleton />}>
          <TrajectoryClient />
        </Suspense>
      </ChartContainer>
    </section>
  );
}
