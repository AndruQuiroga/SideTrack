import { RatingRead } from '@sidetrack/shared';

import { getDiscordGuildId } from '../../src/config';
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

function gradientFromSeed(seed: string) {
  const hash = seed.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0);
  const hue = hash % 360;
  const hue2 = (hash * 5) % 360;
  return `linear-gradient(135deg, hsl(${hue}, 70%, 55%), hsl(${hue2}, 70%, 40%))`;
}

function buildHistogram(summary: WeekDetailWithRatings['rating_summary'], fallbackCount: number) {
  if (summary?.histogram?.length) return summary.histogram;
  if (!fallbackCount) return [];
  return [2, 2.5, 3, 3.5, 4, 4.5, 5].map((value, idx) => ({
    value,
    count: Math.max(1, Math.round((fallbackCount - idx) / 2)),
  }));
}

function albumAndArtist(pitch?: string | null) {
  if (!pitch) return { album: 'Winner pending', artist: 'Nomination window still open' };
  const [album, artist] = pitch.split('—').map((part) => part.trim());
  return { album: album ?? pitch, artist: artist ?? '' };
}

function threadHref(threadId?: number | null) {
  const guildId = getDiscordGuildId();
  if (!guildId || !threadId) return null;
  return `https://discord.com/channels/${guildId}/${threadId}`;
}

export function WeekDetailPanel({ week }: WeekDetailPanelProps) {
  const winner = week.nominations[0];
  const { album, artist } = albumAndArtist(winner?.pitch);
  const ratingCopy = week.rating_summary
    ? `${week.rating_summary.average?.toFixed(2) ?? '—'} (${week.rating_summary.count} ratings)`
    : week.aggregates.rating_average
      ? `${week.aggregates.rating_average?.toFixed(2)} avg · ${week.aggregates.rating_count} ratings`
      : 'No ratings yet';

  const sortedNominations = [...week.nominations].sort((a, b) => b.vote_summary.points - a.vote_summary.points);
  const histogram = buildHistogram(week.rating_summary, week.aggregates.rating_count);
  const coverStyle = { backgroundImage: gradientFromSeed(winner?.album_id ?? week.id) };

  return (
    <PageShell
      title={album}
      description="Winner, poll results, ratings, and live club context."
      accent={week.label}
      actions={<Pill className="bg-emerald-500/15 text-emerald-200">Archive + live</Pill>}
    >
      <div className="grid gap-5 lg:grid-cols-[1.6fr,1fr]">
        <Card className="h-full space-y-4">
          <div className="grid gap-4 md:grid-cols-[1.2fr,1fr]">
            <div className="space-y-3">
              <div className="flex items-start gap-3">
                <div className="relative aspect-square w-28 shrink-0 overflow-hidden rounded-2xl border border-slate-800/70 shadow-soft" style={coverStyle}>
                  <div className="absolute inset-0 bg-gradient-to-br from-black/50 via-transparent to-black/30" />
                  <div className="absolute bottom-2 left-2 rounded-full bg-black/60 px-2 py-0.5 text-[0.65rem] font-semibold uppercase tracking-wide text-white">
                    {formatDate(week.discussion_at ?? week.created_at)}
                  </div>
                </div>
                <div className="space-y-1">
                  <p className="text-xs uppercase tracking-wide text-slate-400">{week.label}</p>
                  <h2 className="text-2xl font-semibold text-white sm:text-3xl">{album}</h2>
                  <p className="text-sm text-slate-300">{artist || 'Club winner'}</p>
                  <div className="flex flex-wrap items-center gap-2 text-xs text-slate-200">
                    {[winner?.genre, winner?.decade, winner?.country].filter(Boolean).map((chip) => (
                      <span key={chip as string} className="rounded-full bg-slate-900/80 px-3 py-1 uppercase tracking-wide text-[0.7rem] text-slate-200">
                        {chip as string}
                      </span>
                    ))}
                    {week.source === 'fallback' && (
                      <span className="rounded-full bg-amber-500/20 px-3 py-1 text-[0.7rem] font-semibold text-amber-200">Demo data</span>
                    )}
                  </div>
                </div>
              </div>
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
                <div className="rounded-2xl border border-slate-800/70 bg-slate-900/60 p-3">
                  <p className="text-xs uppercase tracking-wide text-slate-400">Average rating</p>
                  <div className="mt-2 flex items-center gap-2 text-lg font-semibold text-white">
                    <RatingBadge value={week.rating_summary?.average ?? week.aggregates.rating_average} />
                  </div>
                  <p className="text-xs text-slate-400">{ratingCopy}</p>
                </div>
                <div className="rounded-2xl border border-slate-800/70 bg-slate-900/60 p-3">
                  <p className="text-xs uppercase tracking-wide text-slate-400">Participation</p>
                  <p className="mt-2 text-xl font-semibold text-white">{week.aggregates.vote_count} votes</p>
                  <p className="text-xs text-slate-400">{week.aggregates.nomination_count} nominations</p>
                </div>
                <div className="rounded-2xl border border-slate-800/70 bg-slate-900/60 p-3">
                  <p className="text-xs uppercase tracking-wide text-slate-400">Ratings submitted</p>
                  <p className="mt-2 text-xl font-semibold text-white">{week.rating_summary?.count ?? week.aggregates.rating_count}</p>
                  <p className="text-xs text-slate-400">Listener reviews posted</p>
                </div>
              </div>
            </div>
            <div className="space-y-3 rounded-2xl border border-slate-800/70 bg-slate-900/60 p-4">
              <SectionHeading eyebrow="Club links" title="Discord context" />
              <div className="space-y-2 text-sm text-slate-300">
                <p>Jump into the live Discord threads to see how the discussion unfolded.</p>
                <div className="flex flex-wrap gap-2 text-xs font-semibold text-slate-200">
                  {[
                    { label: 'Nominations', href: threadHref(week.nominations_thread_id) },
                    { label: 'Poll', href: threadHref(week.poll_thread_id) },
                    { label: 'Winner', href: threadHref(week.winner_thread_id) },
                    { label: 'Ratings', href: threadHref(week.ratings_thread_id) },
                  ].map((link) =>
                    link.href ? (
                      <a
                        key={link.label}
                        href={link.href}
                        target="_blank"
                        rel="noreferrer"
                        className="rounded-full bg-slate-800 px-3 py-1 text-[0.7rem] uppercase tracking-wide text-emerald-200 hover:text-white"
                      >
                        {link.label}
                      </a>
                    ) : (
                      <span
                        key={link.label}
                        className="rounded-full bg-slate-900 px-3 py-1 text-[0.7rem] uppercase tracking-wide text-slate-500"
                      >
                        {link.label}
                      </span>
                    )
                  )}
                </div>
                <p className="text-xs text-slate-400">
                  Presence: <span className="text-emerald-200">live listeners spotted</span>. Ratings update in real time as they come in.
                </p>
              </div>
            </div>
          </div>
        </Card>

        <Card className="space-y-4">
          <SectionHeading title="Week recap" />
          <div className="space-y-2 text-sm text-slate-300">
            <p>
              Ranked votes decide the winner, backed by a ratings thread that keeps updating as club members finish their listens. This page mixes the
              public archive with live context so newcomers can catch up fast.
            </p>
            <p className="text-xs text-slate-400">
              Hosting a listening party? Use the Discord links to jump straight into the active threads and share your thoughts.
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
                <div className="flex flex-wrap items-start justify-between gap-2">
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
        <SectionHeading
          title="Nominations & pitches"
          aside={<p className="text-sm text-slate-400">{week.aggregates.nomination_count} submissions</p>}
        />
        <div className="grid gap-3 md:grid-cols-2">
          {week.nominations.map((nomination) => (
            <div key={nomination.id} className="rounded-2xl border border-slate-800/70 bg-slate-900/60 p-4">
              <div className="flex items-center justify-between">
                <p className="text-sm font-semibold text-white">{nomination.pitch ?? 'Nomination'}</p>
                <span className="rounded-full bg-slate-800 px-3 py-1 text-[0.7rem] text-slate-300">
                  {nomination.vote_summary.points} pts
                </span>
              </div>
              <p className="mt-1 text-xs text-slate-400">
                {nomination.genre ?? 'Genre'} · {nomination.decade ?? 'Decade'} · {nomination.country ?? 'Country'}
              </p>
              <div className="mt-2 flex flex-wrap gap-2 text-xs text-slate-300">
                {nomination.pitch_track_url ? (
                  <a
                    href={nomination.pitch_track_url}
                    target="_blank"
                    rel="noreferrer"
                    className="rounded-full bg-slate-800 px-3 py-1 text-[0.7rem] font-semibold text-emerald-200 hover:text-white"
                  >
                    Pitch track
                  </a>
                ) : (
                  <span className="rounded-full bg-slate-900 px-3 py-1 text-[0.7rem] text-slate-400">Track link pending</span>
                )}
                <span className="rounded-full bg-slate-900 px-3 py-1 text-[0.7rem] text-slate-400">
                  First-place votes: {nomination.vote_summary.first_place}
                </span>
                <span className="rounded-full bg-slate-900 px-3 py-1 text-[0.7rem] text-slate-400">
                  Second-place votes: {nomination.vote_summary.second_place}
                </span>
              </div>
            </div>
          ))}
        </div>
      </Card>

      <Card className="space-y-4">
        <SectionHeading
          title="Listener ratings"
          aside={<p className="text-sm text-slate-400">{week.ratings?.length ?? 0} submissions</p>}
        />
        <div className="grid gap-4 lg:grid-cols-[1fr,1.5fr]">
          <div className="space-y-3 rounded-2xl border border-slate-800/70 bg-slate-900/60 p-4">
            <p className="text-xs uppercase tracking-wide text-slate-400">Distribution</p>
            {histogram.length ? (
              <div className="space-y-2">
                {histogram.map((bin) => {
                  const max = Math.max(...histogram.map((b) => b.count), 1);
                  return (
                    <div key={bin.value} className="flex items-center gap-2">
                      <span className="w-8 text-right text-xs text-slate-300">{bin.value.toFixed(1)}</span>
                      <div className="h-2 flex-1 rounded-full bg-slate-800">
                        <div
                          className="h-full rounded-full bg-gradient-to-r from-emerald-400 via-sky-400 to-purple-500"
                          style={{ width: `${(bin.count / max) * 100}%`, minWidth: '8%' }}
                        />
                      </div>
                      <span className="w-8 text-xs text-slate-400 text-right">{bin.count}</span>
                    </div>
                  );
                })}
              </div>
            ) : (
              <p className="text-sm text-slate-300">Histogram will appear as soon as ratings arrive.</p>
            )}
            <p className="text-xs text-slate-400">
              {week.rating_summary?.count ?? week.aggregates.rating_count} total · live updates as listeners finish the album.
            </p>
          </div>
          <div className="space-y-3">
            {week.ratings?.length ? (
              <div className="grid gap-3 md:grid-cols-2">
                {week.ratings.slice(0, 6).map((rating: RatingRead) => (
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
          </div>
        </div>
      </Card>

      <Card className="space-y-4">
        <SectionHeading title="If you enjoyed this" />
        <div className="grid gap-3 md:grid-cols-3">
          {['Follow the nominator', 'Queue the pitch track', 'Invite a friend to vote'].map((idea) => (
            <div key={idea} className="rounded-2xl border border-slate-800/70 bg-slate-900/60 p-4 text-sm text-slate-200">
              <p className="font-semibold text-white">{idea}</p>
              <p className="mt-1 text-slate-400">
                Keep the momentum going with a quick action — recommendations and presence surface right here when linked accounts are live.
              </p>
            </div>
          ))}
        </div>
      </Card>
    </PageShell>
  );
}
