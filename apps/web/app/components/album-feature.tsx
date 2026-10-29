import Link from 'next/link';
import type { WeekDetailWithRatings } from '../lib/api/weeks';
import { winnerTitle, formatUtc } from '../lib/club';
import { AlbumArt } from './album-art';
import { RatingBadge } from './rating-badge';

export function AlbumFeature({
  week,
  label = 'Latest scheduled week',
  detail = false,
  children,
}: {
  week: WeekDetailWithRatings;
  label?: string;
  detail?: boolean;
  children?: React.ReactNode;
}) {
  const title = winnerTitle(week);
  return (
    <div className="album-feature">
      <div>
        <AlbumArt url={week.winner_album?.cover_url} title={title} />
        {week.winner_album?.artwork_source_url && (
          <a
            className="small"
            href={week.winner_album.artwork_source_url}
            target="_blank"
            rel="noreferrer"
          >
            Artwork source ↗
          </a>
        )}
        <p className="cover-caption">
          {week.label} · {formatUtc(week.discussion_at ?? week.created_at)}
        </p>
      </div>
      <div>
        <p className="eyebrow">{label}</p>
        <h2 className="album-title">{title}</h2>
        {week.winner_album && <p className="album-artist">{week.winner_album.artist_name}</p>}
        <RatingBadge
          value={week.rating_summary?.average ?? week.aggregates.rating_average}
          count={week.rating_summary?.count ?? week.aggregates.rating_count}
        />
        <div className="schedule">
          Scheduled discussion
          {week.discussion_at ? (
            <time dateTime={week.discussion_at}>{formatUtc(week.discussion_at, true)}</time>
          ) : (
            <span> · Date unavailable</span>
          )}
        </div>
        {week.nominations_close_at && (
          <p className="small muted">
            Scheduled nomination deadline: {formatUtc(week.nominations_close_at, true)}
          </p>
        )}
        {week.poll_close_at && (
          <p className="small muted">
            Scheduled poll deadline: {formatUtc(week.poll_close_at, true)}
          </p>
        )}
        <div className="actions">
          {!detail && (
            <Link className="button button-primary" href={`/club/weeks/${week.id}`}>
              Open week →
            </Link>
          )}
          {children}
        </div>
      </div>
    </div>
  );
}
