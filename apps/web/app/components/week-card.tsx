import Link from 'next/link';

import { WeekDetailWithRatings } from '../../src/api/weeks';
import { RatingBadge } from './rating-badge';

interface WeekCardProps {
  week: WeekDetailWithRatings;
}

function formatDate(date?: string | null) {
  if (!date) return 'Date TBC';
  const parsed = new Date(date);
  if (Number.isNaN(parsed.getTime())) return 'Date TBC';
  return parsed.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
}

export function WeekCard({ week }: WeekCardProps) {
  const winner = week.nominations[0];
  const ratingAvg = week.rating_summary?.average ?? week.aggregates.rating_average;
  const ratingCount = week.rating_summary?.count ?? week.aggregates.rating_count;
  const tags = [winner?.genre, winner?.decade, winner?.country].filter(Boolean) as string[];

  return (
    <Link
      href={`/club/weeks/${week.id}`}
      className="group relative overflow-hidden rounded-3xl border border-slate-800/80 bg-sidetrack-soft/70 p-4 shadow-soft transition-transform hover:-translate-y-1 hover:border-sidetrack-accent/70 hover:bg-sidetrack-soft/90"
    >
      <div className="absolute inset-x-0 -top-24 h-40 bg-gradient-to-b from-purple-500/20 via-sky-400/10 to-transparent opacity-70 transition-opacity group-hover:opacity-100" />
      <div className="relative flex flex-col gap-4">
        <div className="flex items-start justify-between gap-3">
          <div className="space-y-1">
            <p className="text-[0.7rem] font-medium uppercase tracking-wide text-slate-400">{week.label}</p>
            <h3 className="text-base font-semibold text-slate-50">
              {winner?.pitch ?? 'Winner pending'}
              {winner?.pitch ? null : <span className="text-slate-400"> · Nominations open</span>}
            </h3>
            <p className="text-xs text-slate-400">{formatDate(week.discussion_at ?? week.created_at)}</p>
          </div>
          <RatingBadge value={ratingAvg ?? undefined} count={ratingCount} />
        </div>

        <div className="flex flex-wrap gap-2 text-[0.75rem] text-slate-300">
          <span className="inline-flex items-center gap-1 rounded-full bg-slate-900/70 px-2.5 py-1">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
            {week.aggregates.vote_count} votes
          </span>
          <span className="inline-flex items-center gap-1 rounded-full bg-slate-900/70 px-2.5 py-1 text-slate-300">
            <span className="h-1.5 w-1.5 rounded-full bg-sky-400" />
            {week.aggregates.nomination_count} nominations
          </span>
          {tags.slice(0, 3).map((tag) => (
            <span key={tag} className="rounded-full bg-slate-900/70 px-2.5 py-1 text-slate-400">
              {tag}
            </span>
          ))}
          {!tags.length && <span className="rounded-full bg-slate-900/60 px-2.5 py-1 text-slate-500">Tags incoming</span>}
        </div>
      </div>
    </Link>
  );
}
