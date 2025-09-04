import MoodSharesChart from './MoodSharesChart';

async function getSeries() {
  const base = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8000';
  const trajRes = await fetch(`${base}/dashboard/trajectory`, { next: { revalidate: 0 } });
  if (!trajRes.ok) return [];
  const traj = await trajRes.json();
  const weeks: string[] = traj.points?.map((p: any) => p.week) ?? [];
  const radarData = await Promise.all(
    weeks.map(async (week: string) => {
      const res = await fetch(`${base}/dashboard/radar?week=${encodeURIComponent(week)}`, { next: { revalidate: 0 } });
      if (!res.ok) return null;
      const radar = await res.json();
      return { week: radar.week, ...radar.axes };
    })
  );
  return radarData.filter(Boolean);
}

export default async function Moods() {
  const series = await getSeries();
  return (
    <section>
      <h2>Moods</h2>
      {series.length === 0 ? (
        <p>No data yet. Ingest listens and aggregate weeks.</p>
      ) : (
        <MoodSharesChart data={series} />
      )}
    </section>
  );
}
