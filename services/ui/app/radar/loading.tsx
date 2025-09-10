import ChartSkeleton from '../../components/ChartSkeleton';
import ChartContainer from '../../components/ChartContainer';
import Skeleton from '../../components/Skeleton';

export default function Loading() {
  return (
    <section className="space-y-4">
      <Skeleton className="h-6 w-40" />
      <ChartContainer title="Radar" subtitle="Current week vs baseline">
        <ChartSkeleton />
      </ChartContainer>
    </section>
  );
}
