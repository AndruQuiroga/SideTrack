import fs from 'node:fs/promises';
import { WeekDetail, RatingSummary } from '@sidetrack/shared';

import { getLegacyDataPath } from '../config';

interface LegacyWeekRecord extends WeekDetail {
  rating_summary?: RatingSummary;
}

export async function loadLegacyWeeks(): Promise<LegacyWeekRecord[]> {
  const filePath = getLegacyDataPath();
  const raw = await fs.readFile(filePath, 'utf-8');
  const parsed = JSON.parse(raw) as LegacyWeekRecord[];
  return parsed.map((week: LegacyWeekRecord) => {
    const nominations = (week.nominations ?? []) as WeekDetail['nominations'];
    const vote_count = nominations.reduce((acc: number, nomination) => acc + nomination.vote_summary.total_votes, 0);
    const rating_count = nominations.reduce((acc: number, nomination) => acc + nomination.rating_summary.count, 0);

    return {
      ...week,
      nominations,
      aggregates: week.aggregates ?? {
        nomination_count: nominations.length,
        vote_count,
        rating_count,
        rating_average: week.rating_summary?.average ?? null,
      },
    };
  });
}

export async function findLegacyWeek(weekId: string): Promise<LegacyWeekRecord | undefined> {
  const weeks = await loadLegacyWeeks();
  return weeks.find((week) => week.id === weekId || week.legacy_week_id === weekId);
}
