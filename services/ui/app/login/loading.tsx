import Skeleton from '../../components/Skeleton';

export default function Loading() {
  return (
    <section className="max-w-sm mx-auto mt-20 space-y-4">
      <Skeleton className="h-6 w-32" />
      <Skeleton className="h-10 w-full" />
      <Skeleton className="h-10 w-full" />
      <Skeleton className="h-8 w-full" />
    </section>
  );
}
