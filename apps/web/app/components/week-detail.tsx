import { RatingRead } from '@sidetrack/shared';

import { WeekDetailWithRatings } from '../../src/api/weeks';
import { Card, Pill, SectionHeading } from './ui';
import { PageShell } from './page-shell';
import { RatingBadge } from './rating-badge';

interface WeekDetailPanelProps {
  week: WeekDetailWithRatings;
}

function formatDate(date?: string | null) {
  if (!date) return 'Date TBC';
  const parsed = new Date(date);
  if (Number.isNaN(parsed.getTime())) return 'Date TBC';
  return parsed.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
}

export function WeekDetailPanel({ week }: WeekDetailPanelProps) {
  const winner = week.nominations[0];
  const ratingCopy = week.rating_summary
    ? `${week.rating_summary.average?.toFixed(2) ?? '—'} (${week.rating_summary.count} ratings)`
    : week.aggregates.rating_average
      ? `${week.aggregates.rating_average?.toFixed(2)} avg · ${week.aggregates.rating_count} ratings`
      : 'No ratings yet';

  const sortedNominations = [...week.nominations].sort(
    (a, b) => b.vote_summary.points - a.vote_summary.points
  );

  return (
    <PageShell
      title={winner?.pitch ?? 'Sidetrack Week Detail'}
      description="Winner, poll results, and listener ratings from this club cycle."
      accent={week.label}
      actions={<Pill className="bg-slate-900/70 text-[0.65rem]">Live archive</Pill>}
    >
      <div className="grid gap-5 lg:grid-cols-[2fr,1fr]">
        <Card className="h-full">
          <div className="flex flex-col gap-3">
            <p className="text-sm text-slate-300">{formatDate(week.discussion_at ?? week.created_at)}</p>
            <h2 className="text-2xl font-semibold text-white sm:text-3xl">
              {winner?.pitch ?? 'Winner pending — nominations still open'}
            </h2>
            <div className="flex flex-wrap items-center gap-2 text-sm text-slate-300">
              <Pill>{winner?.genre ?? 'Genre TBD'}</Pill>
              <Pill className="text-[0.7rem]">{winner?.decade ?? 'Decade'}</Pill>
              <Pill className="text-[0.7rem]">{winner?.country ?? 'Country'}</Pill>
            </div>
            <div className="mt-3 grid gap-3 sm:grid-cols-3">
              <div className="rounded-2xl border border-slate-800/70 bg-slate-900/60 p-3">
                <p className="text-xs uppercase tracking-wide text-slate-400">Average rating</p>
                <div className="mt-2 flex items-center gap-2 text-lg font-semibold text-white">
                  <RatingBadge value={week.rating_summary?.average ?? week.aggregates.rating_average} />
                </div>
              </div>
              <div className="rounded-2xl border border-slate-800/70 bg-slate-900/60 p-3">
                <p className="text-xs uppercase tracking-wide text-slate-400">Ratings submitted</p>
                <p className="mt-2 text-xl font-semibold text-white">
                  {week.rating_summary?.count ?? week.aggregates.rating_count}
                </p>
                <p className="text-xs text-slate-400">Listeners shared their thoughts</p>
              </div>
              <div className="rounded-2xl border border-slate-800/70 bg-slate-900/60 p-3">
                <p className="text-xs uppercase tracking-wide text-slate-400">Votes tallied</p>
                <p className="mt-2 text-xl font-semibold text-white">{week.aggregates.vote_count}</p>
                <p className="text-xs text-slate-400">Across {week.aggregates.nomination_count} nominations</p>
              </div>
            </div>
            <p className="text-sm text-slate-300">{ratingCopy}</p>
          </div>
        </Card>

        <Card className="space-y-4">
          <SectionHeading title="Week recap" />
          <div className="space-y-2 text-sm text-slate-300">
            <p>
              A snapshot of this Sidetrack cycle. Ratings will update live as listeners add their scores. Poll numbers
              reflect the ranked voting run in Discord.
            </p>
            <p className="text-xs text-slate-400">
              Looking for Discord context? Jump into the nominations, poll, or ratings threads from your server to see
              the discussion history.
            </p>
          </div>
        </Card>
      </div>

      <Card className="space-y-4">
        <SectionHeading title="Poll results" aside={<p className="text-sm text-slate-400">{sortedNominations.length} nominees</p>} />
        <div className="space-y-3">
          {sortedNominations.map((nomination, idx) => {
            const votePoints = nomination.vote_summary.points;
            const maxPoints = Math.max(...sortedNominations.map((n) => n.vote_summary.points), 1);
            const voteWidth = Math.min(100, (votePoints / maxPoints) * 100);
            return (
              <div key={nomination.id} className="space-y-3 rounded-2xl border border-slate-800/80 bg-slate-900/60 p-4">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <p className="text-sm font-semibold text-white">
                      #{idx + 1} · {nomination.pitch ?? 'Nomination'}
                    </p>
                    <p className="text-xs text-slate-400">
                      {nomination.genre ?? 'Genre'} · {nomination.decade ?? 'Decade'} · {nomination.country ?? 'Country'}
                    </p>
                  </div>
                  <Pill className="text-[0.65rem]">
                    {votePoints} pts · {nomination.vote_summary.total_votes} votes
                  </Pill>
                </div>
                <div className="h-2 rounded-full bg-slate-800">
                  <div
                    className="h-full rounded-full bg-gradient-to-r from-sky-400 via-purple-500 to-emerald-400"
                    style={{ width: `${voteWidth}%`, minWidth: '8%' }}
                  />
                </div>
                <p className="text-xs text-slate-300">
                  Ratings: {nomination.rating_summary.count} · Avg:{' '}
                  {nomination.rating_summary.average?.toFixed(2) ?? '—'}
                </p>
              </div>
            );
          })}
        </div>
      </Card>

      <Card className="space-y-4">
        <SectionHeading title="Listener ratings" aside={<p className="text-sm text-slate-400">{week.ratings?.length ?? 0} submissions</p>} />
        {week.ratings?.length ? (
          <div className="grid gap-3 md:grid-cols-2">
            {week.ratings.map((rating: RatingRead) => (
              <div key={rating.id} className="rounded-2xl border border-slate-800/70 bg-slate-900/60 p-4">
                <div className="flex items-center justify-between">
                  <RatingBadge value={rating.value} />
                  <p className="text-xs text-slate-400">
                    {rating.created_at ? new Date(rating.created_at).toLocaleDateString() : 'Recently'}
                  </p>
                </div>
                {rating.favorite_track && <p className="mt-2 text-xs text-slate-300">Fav track: {rating.favorite_track}</p>}
                {rating.review && <p className="mt-2 text-sm text-slate-200 leading-relaxed">{rating.review}</p>}
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-slate-300">No ratings yet. Share yours to kick things off.</p>
        )}
      </Card>
    </PageShell>
  );
}
