import dynamic from 'next/dynamic';

const Plot = dynamic(() => import('react-plotly.js'), { ssr: false });

async function getTrajectory() {
  const base = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8000';
  const res = await fetch(`${base}/dashboard/trajectory`, { next: { revalidate: 0 } });
  if (!res.ok) throw new Error('Failed to fetch trajectory');
  return res.json();
}

export default async function Trajectory() {
  const data = await getTrajectory();
  const trace = {
    type: 'scatter',
    mode: 'lines+markers',
    x: data.points.map((p: any) => p.x),
    y: data.points.map((p: any) => p.y),
    text: data.points.map((p: any) => p.week),
    textposition: 'top center',
  };
  const layout = {
    xaxis: { title: 'Valence', range: [0, 1] },
    yaxis: { title: 'Energy', range: [0, 1] },
    annotations: data.arrows.map((a: any) => ({
      x: a.to.x,
      y: a.to.y,
      ax: a.from.x,
      ay: a.from.y,
      xref: 'x',
      yref: 'y',
      axref: 'x',
      ayref: 'y',
      showarrow: true,
      arrowhead: 3,
    })),
    margin: { t: 20 },
  };
  return (
    <section>
      <h2>Taste Trajectory</h2>
      <p>Showing weekly points (x = valence, y = energy):</p>
      <Plot data={[trace]} layout={layout} />
    </section>
  );
}
