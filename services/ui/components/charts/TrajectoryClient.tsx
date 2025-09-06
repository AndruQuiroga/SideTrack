'use client';
import { Suspense } from 'react';
import dynamic from 'next/dynamic';
import Skeleton from '../Skeleton';
import { useTrajectory } from '../../lib/query';

const TrajectoryBubble = dynamic(() => import('./TrajectoryBubble'), {
  loading: () => (
    <Skeleton className="aspect-[4/3] h-[clamp(240px,40vh,380px)]" />
  ),
  ssr: false,
});

export default function TrajectoryClient() {
  const { data, isLoading, isError } = useTrajectory();

  if (isLoading)
    return <Skeleton className="aspect-[4/3] h-[clamp(240px,40vh,380px)]" />;
  if (isError || !data)
    return <div className="text-sm text-rose-400">Failed to load trajectory</div>;
  return (
    <Suspense
      fallback={
        <Skeleton className="aspect-[4/3] h-[clamp(240px,40vh,380px)]" />
      }
    >
      <TrajectoryBubble data={data} />
    </Suspense>
  );
}
