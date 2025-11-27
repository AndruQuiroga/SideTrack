import { SidetrackApiClient, WeekDetail, RatingSummary, RatingRead, UUID } from '@sidetrack/shared';

import { createWebApiClient } from './client';

export interface WeekDetailWithRatings extends WeekDetail {
  rating_summary?: RatingSummary;
  ratings?: RatingRead[];
  source: 'api';
}

async function attachRatingSummaries(
  client: SidetrackApiClient,
  weeks: WeekDetail[]
): Promise<WeekDetailWithRatings[]> {
  return Promise.all(
    weeks.map(async (week) => {
      const rating_summary = await client.getWeekRatingSummary(week.id).catch(() => undefined);
      return { ...week, rating_summary, source: 'api' as const };
    })
  );
}

const createClient = createWebApiClient;

export async function fetchWeekList(): Promise<WeekDetailWithRatings[]> {
  const client = createClient();
  const weeks = await client.listWeeks({ has_winner: true });
  return attachRatingSummaries(client, weeks);
}

export async function fetchWeekDetail(weekId: UUID): Promise<WeekDetailWithRatings | undefined> {
  const client = createClient();
  const week = await client.getWeek(weekId);
  const rating_summary = await client.getWeekRatingSummary(weekId).catch(() => undefined);
  const allRatings = await client.listRatings().catch(() => []);
  const ratings = allRatings.filter((rating) => rating.week_id === weekId);
  return { ...week, rating_summary, ratings, source: 'api' };
}
