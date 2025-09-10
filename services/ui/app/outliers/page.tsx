'use client';

import { useState } from 'react';
import ChartContainer from '../../components/ChartContainer';
import EmptyState from '../../components/EmptyState';
import Skeleton from '../../components/Skeleton';
import FilterBar from '../../components/FilterBar';
import { useOutliers } from '../../lib/query';

export default function Outliers() {
  const [range, setRange] = useState('12w');
  const { data, isLoading } = useOutliers(range);
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
    <section className="@container space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold">Outliers</h2>
        <FilterBar
          options={[
            { label: '4w', value: '4w' },
            { label: '12w', value: '12w' },
            { label: '24w', value: '24w' },
          ]}
          value={range}
          onChange={setRange}
        />
      </div>
      <ChartContainer title="Outliers" subtitle="Far from your recent centroid">
        {content}
      </ChartContainer>
    </section>
  );
}
