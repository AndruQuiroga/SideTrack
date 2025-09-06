import TrajectoryClient from '../../components/charts/TrajectoryClient';

export default async function Trajectory() {
  return (
    <section className="space-y-4">
      <div>
        <h2 className="text-xl font-semibold">Taste Trajectory</h2>
        <p className="text-sm text-muted-foreground">Weekly points (x = valence, y = energy)</p>
      </div>
      <TrajectoryClient />
    </section>
  );
}
