import { WeekDetailWithRatings } from '../../src/api/weeks';
import { WeekCard } from './week-card';

interface WeekListProps {
  weeks: WeekDetailWithRatings[];
  emptyMessage?: string;
}

export function WeekList({ weeks, emptyMessage }: WeekListProps) {
  if (!weeks.length) {
    return <p className="card text-sm text-slate-300">{emptyMessage ?? 'No weeks yet. Check back soon.'}</p>;
  }

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {weeks.map((week) => (
        <WeekCard key={week.id} week={week} />
      ))}
    </div>
  );
}
