import Skeleton from '../../components/Skeleton';

export default function Loading() {
  return (
    <section className="space-y-6">
      <Skeleton className="h-8 w-32" />
      <Skeleton className="h-5 w-48" />
      <Skeleton className="h-32" />
    </section>
  );
}
