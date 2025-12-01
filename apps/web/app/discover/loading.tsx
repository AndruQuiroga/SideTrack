import { Card } from '../components/ui';
import { PageShell } from '../components/page-shell';
import { Skeleton } from '../components/skeleton';

export default function LoadingDiscover() {
  return (
    <PageShell title="Discover" description="Loading personalized recommendations…" accent="For You">
      <div className="grid gap-4 md:grid-cols-3">
        <Card className="md:col-span-2">
          <div className="space-y-3">
            <Skeleton className="h-5 w-40" />
            <div className="grid gap-3 sm:grid-cols-2">
              {Array.from({ length: 4 }).map((_, i) => (
                <Skeleton key={i} className="h-24" />
              ))}
            </div>
          </div>
        </Card>
        <Card>
          <div className="space-y-3">
            <Skeleton className="h-5 w-48" />
            <div className="space-y-2">
              {Array.from({ length: 3 }).map((_, i) => (
                <Skeleton key={i} className="h-12" />
              ))}
            </div>
          </div>
        </Card>
      </div>
    </PageShell>
  );
}
