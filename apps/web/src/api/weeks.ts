import { SidetrackApiClient, WeekDetail, RatingSummary, UUID } from '@sidetrack/shared';

import { getApiBaseUrl } from '../config';
import { findLegacyWeek, loadLegacyWeeks } from '../legacy/loadLegacyWeeks';

export interface WeekDetailWithRatings extends WeekDetail {
  rating_summary?: RatingSummary;
  source: 'api' | 'legacy';
}

function createClient(): SidetrackApiClient {
  return new SidetrackApiClient({ baseUrl: getApiBaseUrl() });
}

export async function fetchWeekListWithFallback(): Promise<WeekDetailWithRatings[]> {
  const client = createClient();
  try {
    const weeks = await client.listWeeks({ has_winner: true });
    if (weeks.length > 0) {
      return weeks.map((week) => ({ ...week, source: 'api' as const }));
    }
  } catch (error) {
    console.warn('API week list failed, falling back to legacy data', error);
  }

  const legacyWeeks = await loadLegacyWeeks();
  return legacyWeeks.map((week) => ({ ...week, source: 'legacy' as const }));
}

export async function fetchWeekDetailWithFallback(weekId: UUID): Promise<WeekDetailWithRatings | undefined> {
  const client = createClient();
  try {
    const week = await client.getWeek(weekId);
    const rating_summary = await client.getWeekRatingSummary(weekId).catch(() => undefined);
    return { ...week, rating_summary, source: 'api' };
  } catch (error) {
    console.warn(`API week detail failed for ${weekId}, falling back to legacy data`, error);
    const legacyWeek = await findLegacyWeek(weekId);
    if (legacyWeek) {
      return { ...legacyWeek, source: 'legacy' };
    }
    return undefined;
  }
}
