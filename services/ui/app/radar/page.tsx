import { apiFetch } from '../../lib/api';

async function getRadar() {
  // Pull trajectory to discover the most recent week, then build radar
  const trajRes = await apiFetch('/dashboard/trajectory', { next: { revalidate: 0 } });
  const traj = await trajRes.json();
  const last = traj.points?.[traj.points.length - 1];
  const week = last?.week;
  if (!week) return { week: null, axes: {}, baseline: {} };
  const res = await apiFetch(`/dashboard/radar?week=${encodeURIComponent(week)}`, { next: { revalidate: 0 } });
  if (!res.ok) throw new Error('Failed to fetch radar');
  return res.json();
}

export default async function Radar() {
  const data = await getRadar();
  return (
    <section>
      <h2>Weekly Radar</h2>
      {!data.week ? (
        <p>No data yet. Ingest some listens to begin.</p>
      ) : (
        <>
          <p>Week: <code>{data.week}</code></p>
          <h3>Axes</h3>
          <ul>
            {Object.entries(data.axes).map(([k, v]: any) => (
              <li key={k}><strong>{k}</strong>: {Number(v).toFixed(3)}</li>
            ))}
          </ul>
          <h3>Baseline (prev 24w)</h3>
          <ul>
            {Object.entries(data.baseline).map(([k, v]: any) => (
              <li key={k}><strong>{k}</strong>: {Number(v).toFixed(3)}</li>
            ))}
          </ul>
        </>
      )}
    </section>
  );
}
