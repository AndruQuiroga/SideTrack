'use client';
import ChartContainer from '../ChartContainer';
import EmptyState from '../EmptyState';
import Skeleton from '../Skeleton';
import { useOutliers } from '../../lib/query';
import { useInspector } from '../../hooks/useInspector';

type Props = {
  range: string;
};

export default function OutliersPanel({ range }: Props) {
  const { data, isLoading, isError } = useOutliers(range);
  const tracks = data?.tracks ?? [];
  const { inspect } = useInspector();

  let content;
  if (isLoading) {
    content = <Skeleton className="h-[clamp(120px,25vh,160px)]" />;
  } else if (isError) {
    content = <EmptyState title="Failed to load outliers." />;
  } else if (!tracks.length) {
    content = <EmptyState title="No outliers found." />;
  } else {
    content = (
      <ul className="space-y-2 text-sm">
        {tracks.map((t) => (
          <li
            key={t.track_id}
            className="flex items-center justify-between cursor-pointer"
            onClick={() => inspect({ type: 'track', track: t })}
          >
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
    <section className="@container space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold">Outliers</h2>
      </div>
      <ChartContainer title="Outliers" subtitle="Far from your recent centroid">
        {content}
      </ChartContainer>
    </section>
  );
}
