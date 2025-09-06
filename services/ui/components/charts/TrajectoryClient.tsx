'use client';
import { Suspense } from 'react';
import dynamic from 'next/dynamic';
import Skeleton from '../Skeleton';
import { useTrajectory } from '../../lib/query';

const TrajectoryBubble = dynamic(() => import('./TrajectoryBubble'), {
  loading: () => <Skeleton className="h-[380px]" />,
  ssr: false,
});

export default function TrajectoryClient() {
  const { data, isLoading, isError } = useTrajectory();

  if (isLoading) return <Skeleton className="h-[380px]" />;
  if (isError || !data)
    return <div className="text-sm text-rose-400">Failed to load trajectory</div>;
  return (
    <Suspense fallback={<Skeleton className="h-[380px]" />}>
      <TrajectoryBubble data={data} />
    </Suspense>
  );
}
