import Skeleton from '../../components/Skeleton';

export default function Loading() {
  return (
    <section className="space-y-6">
      <Skeleton className="h-8 w-32" />
      {Array.from({ length: 4 }).map((_, i) => (
        <Skeleton key={i} className="h-40" />
      ))}
    </section>
  );
}
