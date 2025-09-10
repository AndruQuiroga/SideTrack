import ChartSkeleton from '../../components/ChartSkeleton';
import ChartContainer from '../../components/ChartContainer';
import Skeleton from '../../components/Skeleton';

export default function Loading() {
  return (
    <section className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="space-y-2">
          <Skeleton className="h-6 w-32" />
          <Skeleton className="h-4 w-48" />
        </div>
        <Skeleton className="h-8 w-24" />
      </div>
      <ChartContainer title="Trajectory" subtitle="Recent weekly bubbles and positions">
        <ChartSkeleton />
      </ChartContainer>
    </section>
  );
}
