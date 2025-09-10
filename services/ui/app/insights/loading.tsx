import Skeleton from '../../components/Skeleton';

export default function Loading() {
  return (
    <div className="grid gap-4 md:grid-cols-2">
      {[1, 2, 3].map((i) => (
        <Skeleton key={i} className="h-24" />
      ))}
    </div>
  );
}
