import { apiFetch } from '../../lib/api';

type OutlierTrack = { track_id: number; title: string; artist?: string; distance: number };
type OutliersResponse = { tracks: OutlierTrack[] };

async function getOutliers(): Promise<OutliersResponse> {
  const res = await apiFetch('/dashboard/outliers', { next: { revalidate: 0 } });
  if (!res.ok) return { tracks: [] } as OutliersResponse;
  return (await res.json()) as OutliersResponse;
}

export default async function Outliers() {
  const data = await getOutliers();
  return (
    <section>
      <h2>Outliers</h2>
      {!data.tracks || data.tracks.length === 0 ? (
        <p>No outliers found.</p>
      ) : (
        <ul>
          {data.tracks.map((t: OutlierTrack) => (
            <li key={t.track_id}>
              {t.title} – {t.artist || 'Unknown'} ({t.distance.toFixed(3)})
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
