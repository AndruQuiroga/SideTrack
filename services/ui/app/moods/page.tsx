import { apiFetch } from '../../lib/api';

async function getAgg() {
  // Use trajectory weeks and then pull radar for each to assemble a simple table
  const trajRes = await apiFetch('/dashboard/trajectory', { next: { revalidate: 0 } });
  if (!trajRes.ok) return { points: [] };
  const traj = await trajRes.json();
  return traj;
}

export default async function Moods() {
  const traj = await getAgg();
  return (
    <section>
      <h2>Moods</h2>
      {(!traj.points || traj.points.length === 0) ? (
        <p>No data yet. Ingest listens and aggregate weeks.</p>
      ) : (
        <>
          <p>Recent weeks:</p>
          <ul>
            {traj.points.map((p: any) => (
              <li key={p.week}><code>{p.week}</code> – valence: {p.x.toFixed(3)}, energy: {p.y.toFixed(3)}</li>
            ))}
          </ul>
        </>
      )}
    </section>
  );
}
