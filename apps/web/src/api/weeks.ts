import { SidetrackApiClient, WeekDetail, RatingSummary, RatingRead, UUID } from '@sidetrack/shared';

import { createWebApiClient } from './client';

export interface WeekDetailWithRatings extends WeekDetail {
  rating_summary?: RatingSummary;
  ratings?: RatingRead[];
  source: 'api' | 'fallback';
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
  const rating_summary = await client
    .getWeekRatingSummary(weekId, { include_histogram: true, bin_size: 0.5 })
    .catch(() => undefined);
  const allRatings = await client.listRatings().catch(() => []);
  const ratings = allRatings.filter((rating) => rating.week_id === weekId);
  return { ...week, rating_summary, ratings, source: 'api' };
}

// --- Fallbacks for local/demo use --------------------------------------------------------------

function sampleHistogram(): RatingSummary['histogram'] {
  return [
    { value: 2, count: 1 },
    { value: 2.5, count: 2 },
    { value: 3, count: 3 },
    { value: 3.5, count: 4 },
    { value: 4, count: 6 },
    { value: 4.5, count: 5 },
    { value: 5, count: 2 },
  ];
}

function createSampleWeek(id: string, label: string, opts?: Partial<WeekDetailWithRatings>): WeekDetailWithRatings {
  const discussionDate = new Date();
  discussionDate.setDate(discussionDate.getDate() - 7);

  const nominations = [
    {
      id: `${id}-nom-1`,
      week_id: id,
      user_id: 'user-1',
      album_id: 'album-1',
      pitch: 'Spirit of Eden — Talk Talk (1988)',
      pitch_track_url: 'https://open.spotify.com/track/demo',
      genre: 'Art Rock',
      decade: '1980s',
      country: 'UK',
      submitted_at: discussionDate.toISOString(),
      vote_summary: { points: 18, first_place: 9, second_place: 0, total_votes: 9 },
      rating_summary: { average: 4.37, count: 24 },
    },
    {
      id: `${id}-nom-2`,
      week_id: id,
      user_id: 'user-2',
      album_id: 'album-2',
      pitch: 'Visions — Grimes (2012)',
      pitch_track_url: 'https://open.spotify.com/track/demo2',
      genre: 'Electropop',
      decade: '2010s',
      country: 'Canada',
      submitted_at: discussionDate.toISOString(),
      vote_summary: { points: 12, first_place: 4, second_place: 4, total_votes: 8 },
      rating_summary: { average: 3.9, count: 18 },
    },
    {
      id: `${id}-nom-3`,
      week_id: id,
      user_id: 'user-3',
      album_id: 'album-3',
      pitch: 'Heat Rush — Cloudy Friends (2023)',
      pitch_track_url: null,
      genre: 'Indie Rock',
      decade: '2020s',
      country: 'USA',
      submitted_at: discussionDate.toISOString(),
      vote_summary: { points: 9, first_place: 3, second_place: 3, total_votes: 6 },
      rating_summary: { average: 3.6, count: 11 },
    },
  ];

  const ratings: RatingRead[] = [
    {
      id: `${id}-rating-1`,
      week_id: id,
      user_id: 'user-11',
      album_id: 'album-1',
      nomination_id: `${id}-nom-1`,
      value: 4.5,
      favorite_track: 'Desire',
      review: 'Lush, slow-blooming, and gorgeously recorded.',
      created_at: discussionDate.toISOString(),
      metadata: null,
    },
    {
      id: `${id}-rating-2`,
      week_id: id,
      user_id: 'user-12',
      album_id: 'album-1',
      nomination_id: `${id}-nom-1`,
      value: 4.0,
      favorite_track: 'Eden',
      review: 'Rewarding listen with headphones on.',
      created_at: discussionDate.toISOString(),
      metadata: null,
    },
  ];

  const aggregates = {
    nomination_count: nominations.length,
    vote_count: nominations.reduce((acc, n) => acc + n.vote_summary.total_votes, 0),
    rating_count: ratings.length,
    rating_average: 4.2,
  };

  return {
    id,
    label,
    week_number: Number(id.replace(/\D/g, '')) || 0,
    created_at: discussionDate.toISOString(),
    discussion_at: discussionDate.toISOString(),
    nominations_close_at: discussionDate.toISOString(),
    poll_close_at: discussionDate.toISOString(),
    winner_album_id: 'album-1',
    nominations_thread_id: 123,
    poll_thread_id: 456,
    winner_thread_id: 789,
    ratings_thread_id: 1011,
    nominations,
    aggregates,
    rating_summary: { average: aggregates.rating_average, count: aggregates.rating_count, histogram: sampleHistogram() },
    ratings,
    source: 'fallback',
    ...opts,
  };
}

function getSampleWeeks(): WeekDetailWithRatings[] {
  return [
    createSampleWeek('week-demo-3', 'WEEK 003 [2025-11-24]'),
    createSampleWeek('week-demo-2', 'WEEK 002 [2025-11-17]', {
      nominations: [
        {
          id: 'week-demo-2-nom-1',
          week_id: 'week-demo-2',
          user_id: 'user-4',
          album_id: 'album-4',
          pitch: 'Carrie & Lowell — Sufjan Stevens (2015)',
          genre: 'Indie Folk',
          decade: '2010s',
          country: 'USA',
          submitted_at: new Date().toISOString(),
          pitch_track_url: 'https://open.spotify.com/track/demo3',
          vote_summary: { points: 22, first_place: 11, second_place: 0, total_votes: 11 },
          rating_summary: { average: 4.8, count: 30 },
        },
      ],
      aggregates: { nomination_count: 3, vote_count: 15, rating_count: 9, rating_average: 4.6 },
      rating_summary: { average: 4.6, count: 9, histogram: sampleHistogram() },
    }),
    createSampleWeek('week-demo-1', 'WEEK 001 [2025-11-10]'),
  ];
}

export async function fetchWeekListWithFallback(): Promise<WeekDetailWithRatings[]> {
  try {
    return await fetchWeekList();
  } catch (error) {
    console.warn('Falling back to sample week list due to API error', error);
    return getSampleWeeks();
  }
}

export async function fetchWeekDetailWithFallback(weekId: UUID): Promise<WeekDetailWithRatings | undefined> {
  try {
    return await fetchWeekDetail(weekId);
  } catch (error) {
    console.warn('Falling back to sample week detail due to API error', error);
    return getSampleWeeks().find((week) => week.id === weekId) ?? getSampleWeeks()[0];
  }
}
