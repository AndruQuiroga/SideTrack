import ChartContainer from '../../components/ChartContainer';
import Skeleton from '../../components/Skeleton';

export default function Loading() {
  return (
    <section className="space-y-4">
      <Skeleton className="h-6 w-32" />
      <ChartContainer title="Outliers" subtitle="Far from your recent centroid">
        <Skeleton className="h-[clamp(120px,25vh,160px)]" />
      </ChartContainer>
    </section>
  );
}
