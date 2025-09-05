import { apiFetch } from '../../lib/api';

type RadarData = {
  week: string | null;
  axes: Record<string, unknown>;
  baseline: Record<string, unknown>;
};

async function getRadar(): Promise<RadarData> {
  // Pull trajectory to discover the most recent week, then build radar
  const trajRes = await apiFetch('/dashboard/trajectory', { next: { revalidate: 0 } });
  const traj = await trajRes.json();
  const last = traj.points?.[traj.points.length - 1];
  const week = last?.week;
  if (!week) return { week: null, axes: {}, baseline: {} } as RadarData;
  const res = await apiFetch(`/dashboard/radar?week=${encodeURIComponent(week)}`, {
    next: { revalidate: 0 },
  });
  if (!res.ok) throw new Error('Failed to fetch radar');
  return (await res.json()) as RadarData;
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
          <p>
            Week: <code>{data.week}</code>
          </p>
          <h3>Axes</h3>
          <ul>
            {Object.entries(data.axes as Record<string, unknown>).map(([k, v]) => (
              <li key={k}>
                <strong>{k}</strong>: {Number(v).toFixed(3)}
              </li>
            ))}
          </ul>
          <h3>Baseline (prev 24w)</h3>
          <ul>
            {Object.entries(data.baseline as Record<string, unknown>).map(([k, v]) => (
              <li key={k}>
                <strong>{k}</strong>: {Number(v).toFixed(3)}
              </li>
            ))}
          </ul>
        </>
      )}
    </section>
  );
}
