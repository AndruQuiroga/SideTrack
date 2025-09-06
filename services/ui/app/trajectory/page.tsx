import TrajectoryClient from '../../components/charts/TrajectoryClient';
import ChartContainer from '../../components/ChartContainer';
import FilterBar from '../../components/FilterBar';

export default async function Trajectory() {
  return (
    <section className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold">Taste Trajectory</h2>
          <p className="text-sm text-muted-foreground">Weekly points (x = valence, y = energy)</p>
        </div>
        <FilterBar
          options={[
            { label: '12w', value: '12w' },
            { label: '24w', value: '24w' },
            { label: '52w', value: '52w' },
          ]}
          value="12w"
        />
      </div>
      <ChartContainer title="Trajectory" subtitle="Recent weekly bubbles and positions">
        <TrajectoryClient />
      </ChartContainer>
    </section>
  );
}
