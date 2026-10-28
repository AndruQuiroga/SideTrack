import Link from 'next/link';
import type { Route } from 'next';
import type { WeekDetailWithRatings } from '../lib/api/weeks';
import { formatUtc } from '../lib/club';
import { safeReturnPath } from '../lib/navigation';
import { getDiscordGuildId } from '../lib/config';
import { PageShell } from './page-shell';
import { AlbumFeature } from './album-feature';
import { RatingBadge } from './rating-badge';
import { SectionHeading } from './ui';

export function DiscordLinks({
  week,
  guildId = getDiscordGuildId(),
}: {
  week: WeekDetailWithRatings;
  guildId?: string;
}) {
  const links = [
    { name: 'ratings', id: week.ratings_thread_id },
    { name: 'nominations', id: week.nominations_thread_id },
    { name: 'poll', id: week.poll_thread_id },
    { name: 'winner', id: week.winner_thread_id },
  ].filter((link) => link.id);
  if (!guildId || !links.length) return <p className="small muted">Discussion link unavailable</p>;
  return (
    <>
      {links.map((link, index) => (
        <a
          className={index === 0 ? 'button button-primary' : ''}
          key={link.name}
          target="_blank"
          rel="noreferrer"
          href={`https://discord.com/channels/${encodeURIComponent(guildId)}/${encodeURIComponent(String(link.id))}`}
        >
          Open {link.name} in Discord ↗
        </a>
      ))}
    </>
  );
}
export function RatingDistribution({ week }: { week: WeekDetailWithRatings }) {
  const bins = week.rating_summary?.histogram ?? [];
  if (!bins.length)
    return (
      <p className="small muted">
        {(week.rating_summary?.count ?? week.aggregates.rating_count) === 0
          ? 'No ratings yet'
          : 'Distribution unavailable'}
      </p>
    );
  const max = Math.max(...bins.map((bin) => bin.count), 1);
  return (
    <div aria-label="Rating distribution">
      {bins.map((bin) => (
        <div className="histogram-row numeric" key={bin.value}>
          <span>{bin.value.toFixed(1)}</span>
          <div className="histogram-track" aria-hidden="true">
            <div className="histogram-bar" style={{ width: `${(bin.count / max) * 100}%` }} />
          </div>
          <span>{bin.count}</span>
        </div>
      ))}
    </div>
  );
}
export function WeekDetailPanel({
  week,
  returnTo = '/club',
}: {
  week: WeekDetailWithRatings;
  returnTo?: string;
}) {
  const path = safeReturnPath(returnTo);
  const back = path === '/club' || path.startsWith('/club?') ? path : '/club';
  const sorted = [...week.nominations].sort(
    (a, b) => b.vote_summary.points - a.vote_summary.points,
  );
  return (
    <PageShell
      title={week.label}
      accent="Club / Week detail"
      actions={<Link href={back as Route}>← Back to archive</Link>}
    >
      <AlbumFeature week={week} label="Club selection" detail>
        <DiscordLinks week={week} />
      </AlbumFeature>
      <div className="two-columns">
        <section className="section">
          <SectionHeading
            title="Listener notes"
            aside={
              <RatingBadge
                value={week.rating_summary?.average ?? week.aggregates.rating_average}
                count={week.rating_summary?.count ?? week.aggregates.rating_count}
              />
            }
          />
          {week.ratings_state === 'unavailable' ? (
            <p role="status" className="muted">
              Ratings unavailable
            </p>
          ) : week.ratings?.length ? (
            week.ratings.map((rating) => (
              <article className="review" key={rating.id}>
                <div className="review-meta">
                  <span>Listener rating · {formatUtc(rating.created_at)}</span>
                  <RatingBadge value={rating.value} />
                </div>
                {rating.favorite_track && (
                  <p className="small muted">Favorite track: {rating.favorite_track}</p>
                )}
                {rating.review &&
                  (rating.review.length > 320 ? (
                    <>
                      <p>{rating.review.slice(0, 320)}…</p>
                      <details>
                        <summary>Read full review</summary>
                        <p>{rating.review}</p>
                      </details>
                    </>
                  ) : (
                    <p>{rating.review}</p>
                  ))}
              </article>
            ))
          ) : (
            <p className="muted">No ratings yet</p>
          )}
        </section>
        <section className="section">
          <h2>Rating distribution</h2>
          <RatingDistribution week={week} />
          <p className="small muted">
            {week.aggregates.vote_count} votes · {week.aggregates.nomination_count} nominations
          </p>
        </section>
      </div>
      <section className="section">
        <h2>Nomination results</h2>
        {sorted.length ? (
          sorted.map((nomination, index) => {
            const album = week.nomination_albums?.[nomination.album_id];
            return (
              <article className="data-row" key={nomination.id}>
                <span className="row-mark numeric">{String(index + 1).padStart(2, '0')}</span>
                <div>
                  <strong>{album?.title ?? 'Album details unavailable'}</strong>
                  {album && <p className="small muted">{album.artist_name}</p>}
                  {nomination.pitch && <p className="small">{nomination.pitch}</p>}
                  <p className="small muted">
                    {nomination.vote_summary.first_place} first-place ·{' '}
                    {nomination.vote_summary.second_place} second-place
                  </p>
                </div>
                <span className="small numeric">{nomination.vote_summary.points} points</span>
              </article>
            );
          })
        ) : (
          <p className="muted">No nominations recorded.</p>
        )}
      </section>
    </PageShell>
  );
}
