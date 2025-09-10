import ChartSkeleton from '../components/ChartSkeleton';
import Skeleton from '../components/Skeleton';

export default function Loading() {
  return (
    <section className="@container space-y-6">
      <div className="flex items-center justify-between">
        <div className="space-y-2">
          <Skeleton className="h-6 w-32" />
          <Skeleton className="h-4 w-48" />
        </div>
        <Skeleton className="h-8 w-24" />
      </div>
      <div className="grid gap-4 @[640px]:grid-cols-2 @[1024px]:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-24" />
        ))}
      </div>
      <Skeleton className="h-8 w-32" />
      <div className="grid gap-6 @[768px]:grid-cols-2">
        <ChartSkeleton />
        <ChartSkeleton />
      </div>
    </section>
  );
}
