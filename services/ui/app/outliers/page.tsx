import { apiFetch } from '../../lib/api';

async function getOutliers() {
  const res = await apiFetch('/dashboard/outliers', { next: { revalidate: 0 } });
  if (!res.ok) return { tracks: [] };
  return res.json();
}

export default async function Outliers() {
  const data = await getOutliers();
  return (
    <section>
      <h2>Outliers</h2>
      {(!data.tracks || data.tracks.length === 0) ? (
        <p>No outliers found.</p>
      ) : (
        <ul>
          {data.tracks.map((t: any) => (
            <li key={t.track_id}>
              {t.title} – {t.artist || 'Unknown'} ({t.distance.toFixed(3)})
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

