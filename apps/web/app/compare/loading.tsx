import { PageShell } from '../components/page-shell';
import { Card } from '../components/ui';
import { Skeleton } from '../components/skeleton';

export default function LoadingCompare() {
  return (
    <PageShell title="Compatibility" description="Crunching overlap and computing taste match…" accent="Prototype view">
      <Card className="space-y-3">
        <Skeleton className="h-6 w-40" />
        <Skeleton className="h-10 w-24" />
        <Skeleton className="h-4 w-full" />
        <div className="grid gap-3 md:grid-cols-2">
          <Skeleton className="h-24" />
          <Skeleton className="h-24" />
        </div>
      </Card>
    </PageShell>
  );
}
