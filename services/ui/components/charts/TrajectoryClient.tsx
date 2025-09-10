'use client';
import { Suspense } from 'react';
import dynamic from 'next/dynamic';
import ChartSkeleton from '../ChartSkeleton';
import { useTrajectory } from '../../lib/query';

const TrajectoryBubble = dynamic(() => import('./TrajectoryBubble'), {
  loading: () => <ChartSkeleton />,
  ssr: false,
});

export default function TrajectoryClient() {
  const { data, isLoading, isError } = useTrajectory();

  if (isLoading) return <ChartSkeleton />;
  if (isError || !data)
    return <div className="text-sm text-rose-400">Failed to load trajectory</div>;
  return (
    <Suspense fallback={<ChartSkeleton />}>
      <TrajectoryBubble data={data} />
    </Suspense>
  );
}
