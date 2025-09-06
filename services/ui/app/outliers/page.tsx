'use client';

import { useOutliers } from '../../lib/query';

export default function Outliers() {
  const { data, isLoading } = useOutliers();
  const tracks = data?.tracks ?? [];
  return (
    <section>
      <h2>Outliers</h2>
      {isLoading ? (
        <p>Loading...</p>
      ) : tracks.length === 0 ? (
        <p>No outliers found.</p>
      ) : (
        <ul>
          {tracks.map((t) => (
            <li key={t.track_id}>
              {t.title} – {t.artist || 'Unknown'} ({t.distance.toFixed(3)})
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
