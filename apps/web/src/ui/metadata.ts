export interface PageMetadata {
  title: string;
  description: string;
}

export function buildWinnersMetadata(weekCount: number): PageMetadata {
  const title = 'Sidetrack Club — Winners Gallery';
  const description =
    weekCount > 0
      ? `Browse ${weekCount} weeks of Sidetrack Club winners, nominees, and ratings without needing an account.`
      : 'Browse Sidetrack Club week history, album winners, and rating stats.';
  return { title, description };
}

export function buildWeekMetadata(titleText: string, summary?: string): PageMetadata {
  const title = `${titleText} — Sidetrack Club Week Details`;
  const description = summary?.slice(0, 180) ?? 'Winner, nominees, and poll results for this Sidetrack Club week.';
  return { title, description };
}
