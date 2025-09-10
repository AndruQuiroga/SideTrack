'use client';

import ChartContainer from '../../components/ChartContainer';
import EmptyState from '../../components/EmptyState';
import Skeleton from '../../components/Skeleton';
import { useOutliers } from '../../lib/query';

export default function Outliers() {
  const { data, isLoading } = useOutliers();
  const tracks = data?.tracks ?? [];

  let content;
  if (isLoading) {
    content = <Skeleton className="h-[clamp(120px,25vh,160px)]" />;
  } else if (!tracks.length) {
    content = <EmptyState title="No outliers found." />;
  } else {
    content = (
      <ul className="space-y-2 text-sm">
        {tracks.map((t) => (
          <li key={t.track_id} className="flex items-center justify-between">
            <span>
              {t.title} – {t.artist || 'Unknown'}
            </span>
            <span className="text-muted-foreground">{t.distance.toFixed(3)}</span>
          </li>
        ))}
      </ul>
    );
  }

  return (
    <section className="space-y-4">
      <h2 className="text-xl font-semibold">Outliers</h2>
      <ChartContainer title="Outliers" subtitle="Far from your recent centroid">
        {content}
      </ChartContainer>
    </section>
  );
}
