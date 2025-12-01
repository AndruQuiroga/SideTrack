export function Skeleton({ className }: { className?: string }) {
  return <div className={`animate-pulse rounded-md bg-slate-800/60 ${className ?? ''}`} />;
}

export function TextSkeleton({ lines = 3 }: { lines?: number }) {
  return (
    <div className="space-y-2">
      {Array.from({ length: lines }).map((_, i) => (
        <Skeleton key={i} className={`h-3 w-${Math.max(3, 12 - i * 2)}/12`} />
      ))}
    </div>
  );
}
