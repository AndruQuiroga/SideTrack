import {
  SidetrackApiClient,
  WeekDetail,
  RatingSummary,
  RatingRead,
  UUID,
} from '@sidetrack/api-client';

export interface WeekDetailWithRatings extends WeekDetail {
  rating_summary?: RatingSummary;
  ratings?: RatingRead[];
}

async function attachRatingSummaries(
  client: SidetrackApiClient,
  weeks: WeekDetail[],
): Promise<WeekDetailWithRatings[]> {
  return Promise.all(
    weeks.map(async (week) => {
      const rating_summary = await client.getWeekRatingSummary(week.id).catch(() => undefined);
      return { ...week, rating_summary };
    }),
  );
}

/** Weeks with a winner, newest first. Throws ApiError when the API is unavailable. */
export async function fetchWeekList(client: SidetrackApiClient): Promise<WeekDetailWithRatings[]> {
  const weeks = await client.listWeeks({ has_winner: true });
  return attachRatingSummaries(client, weeks);
}

/** One week with its ratings. Throws ApiError (status 404 when the week doesn't exist). */
export async function fetchWeekDetail(
  client: SidetrackApiClient,
  weekId: UUID,
): Promise<WeekDetailWithRatings> {
  const week = await client.getWeek(weekId);
  const rating_summary = await client
    .getWeekRatingSummary(weekId, { include_histogram: true, bin_size: 0.5 })
    .catch(() => undefined);
  const allRatings = await client.listRatings().catch(() => []);
  const ratings = allRatings.filter((rating) => rating.week_id === weekId);
  return { ...week, rating_summary, ratings };
}
