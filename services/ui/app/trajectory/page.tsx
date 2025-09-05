import { apiFetch } from '../../lib/api';

type TrajectoryPoint = { week: string; x: number; y: number };
type Trajectory = {
  points: TrajectoryPoint[];
  arrows: { from: TrajectoryPoint; to: TrajectoryPoint }[];
};

async function getTrajectory(): Promise<Trajectory> {
  const res = await apiFetch('/dashboard/trajectory', { next: { revalidate: 0 } });
  if (!res.ok) throw new Error('Failed to fetch trajectory');
  return (await res.json()) as Trajectory;
}

export default async function Trajectory() {
  const data = await getTrajectory();
  return (
    <section>
      <h2>Taste Trajectory</h2>
      <p>Showing weekly points (x = valence, y = energy):</p>
      <ol>
        {data.points.map((p: TrajectoryPoint) => (
          <li key={p.week}>
            <code>{p.week}</code> → x: {p.x.toFixed(3)}, y: {p.y.toFixed(3)}
          </li>
        ))}
      </ol>
      <h3>Arrows</h3>
      <ul>
        {data.arrows.map((a, i: number) => (
          <li key={i}>
            {a.from.week} → {a.to.week}
          </li>
        ))}
      </ul>
    </section>
  );
}
