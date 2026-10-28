import Link from 'next/link';
import type { Route } from 'next';
import type { WeekDetailWithRatings } from '../lib/api/weeks';
import { formatUtc, winnerTitle } from '../lib/club';
import { AlbumArt } from './album-art';
import { RatingBadge } from './rating-badge';
export function WeekCard({
  week,
  returnTo = '/club',
}: {
  week: WeekDetailWithRatings;
  returnTo?: string;
}) {
  const title = winnerTitle(week);
  return (
    <Link
      className="album-card"
      href={`/club/weeks/${week.id}?from=${encodeURIComponent(returnTo)}` as Route}
    >
      <AlbumArt url={week.winner_album?.cover_url} title={title} />
      <h2>{title}</h2>
      {week.winner_album && <p>{week.winner_album.artist_name}</p>}
      <p>
        {week.label} · {formatUtc(week.discussion_at ?? week.created_at)}
      </p>
      <RatingBadge value={week.aggregates.rating_average} count={week.aggregates.rating_count} />
    </Link>
  );
}
