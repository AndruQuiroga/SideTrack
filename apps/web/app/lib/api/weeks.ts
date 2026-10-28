import type {
  AlbumRead,
  SidetrackApiClient,
  WeekDetail,
  RatingSummary,
  RatingRead,
  UUID,
} from '@sidetrack/api-client';

export interface WeekDetailWithRatings extends WeekDetail {
  winner_album?: AlbumRead | null;
  nomination_albums?: Record<string, AlbumRead | null>;
  rating_summary?: RatingSummary;
  rating_summary_state?: 'ok' | 'unavailable';
  ratings?: RatingRead[];
  ratings_state?: 'ok' | 'unavailable';
}

async function withCatalog(
  client: SidetrackApiClient,
  weeks: WeekDetail[],
  nominations = false,
): Promise<WeekDetailWithRatings[]> {
  const ids = new Set(
    weeks
      .flatMap((week) => [
        week.winner_album_id,
        ...(nominations ? week.nominations.map((n) => n.album_id) : []),
      ])
      .filter((id): id is string => Boolean(id)),
  );
  const albums = new Map(
    await Promise.all(
      [...ids].map(async (id) => [id, await client.getAlbum(id).catch(() => null)] as const),
    ),
  );
  return weeks.map((week) => ({
    ...week,
    winner_album: week.winner_album_id ? (albums.get(week.winner_album_id) ?? null) : null,
    ...(nominations
      ? {
          nomination_albums: Object.fromEntries(
            week.nominations.map((n) => [n.album_id, albums.get(n.album_id) ?? null]),
          ),
        }
      : {}),
  }));
}

/** Winner archive uses supplied aggregates, never a per-week histogram request. */
export async function fetchWeekList(client: SidetrackApiClient): Promise<WeekDetailWithRatings[]> {
  return withCatalog(client, await client.listWeeks({ has_winner: true }));
}
/** Includes future and pending weeks; selection is explicit in the presentation model. */
export async function fetchScheduledWeeks(
  client: SidetrackApiClient,
): Promise<WeekDetailWithRatings[]> {
  return withCatalog(client, await client.listWeeks());
}
export async function fetchWeekDetail(
  client: SidetrackApiClient,
  weekId: UUID,
): Promise<WeekDetailWithRatings> {
  const week = await client.getWeek(weekId);
  const [catalog, summary, ratings] = await Promise.all([
    withCatalog(client, [week], true),
    client
      .getWeekRatingSummary(weekId, { include_histogram: true, bin_size: 0.5 })
      .then((data) => ({ state: 'ok' as const, data }))
      .catch(() => ({ state: 'unavailable' as const, data: undefined })),
    client
      .listRatings()
      .then((data) => ({ state: 'ok' as const, data: data.filter((r) => r.week_id === weekId) }))
      .catch(() => ({ state: 'unavailable' as const, data: undefined })),
  ]);
  return {
    ...catalog[0],
    rating_summary: summary.data,
    rating_summary_state: summary.state,
    ratings: ratings.data,
    ratings_state: ratings.state,
  };
}
