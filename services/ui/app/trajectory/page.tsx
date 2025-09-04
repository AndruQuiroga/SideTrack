async function getTrajectory() {
  const base = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8000';
  const res = await fetch(`${base}/dashboard/trajectory`, { next: { revalidate: 0 } });
  if (!res.ok) throw new Error('Failed to fetch trajectory');
  return res.json();
}

export default async function Trajectory() {
  const data = await getTrajectory();
  return (
    <section>
      <h2>Taste Trajectory</h2>
      <p>Showing weekly points (x = valence, y = energy):</p>
      <ol>
        {data.points.map((p: any) => (
          <li key={p.week}>
            <code>{p.week}</code> → x: {p.x.toFixed(3)}, y: {p.y.toFixed(3)}
          </li>
        ))}
      </ol>
      <h3>Arrows</h3>
      <ul>
        {data.arrows.map((a: any, i: number) => (
          <li key={i}>
            {a.from.week} → {a.to.week}
          </li>
        ))}
      </ul>
    </section>
  );
}
