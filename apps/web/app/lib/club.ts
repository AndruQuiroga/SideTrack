import type { WeekDetailWithRatings } from './api/weeks';
export type ArchiveState = {
  q: string;
  tag: string;
  sort: 'newest' | 'rating';
  view: 'grid' | 'list';
};

export function parseArchiveState(params: URLSearchParams): ArchiveState {
  return {
    q: (params.get('q') ?? '').slice(0, 160),
    tag: (params.get('tag') ?? '').slice(0, 100),
    sort: params.get('sort') === 'rating' ? 'rating' : 'newest',
    view: params.get('view') === 'list' ? 'list' : 'grid',
  };
}
export function archiveUrl(state: ArchiveState): string {
  const params = new URLSearchParams();
  if (state.q) params.set('q', state.q);
  if (state.tag) params.set('tag', state.tag);
  if (state.sort !== 'newest') params.set('sort', state.sort);
  if (state.view !== 'grid') params.set('view', state.view);
  return `/club${params.size ? `?${params}` : ''}`;
}
function timestamp(value?: string | null): number {
  const n = Date.parse(value ?? '');
  return Number.isNaN(n) ? 0 : n;
}
export function newestFirst(a: WeekDetailWithRatings, b: WeekDetailWithRatings): number {
  return (
    timestamp(b.discussion_at ?? b.created_at) - timestamp(a.discussion_at ?? a.created_at) ||
    timestamp(b.created_at) - timestamp(a.created_at) ||
    a.id.localeCompare(b.id)
  );
}
export function latestScheduled(weeks: WeekDetailWithRatings[]): WeekDetailWithRatings | undefined {
  return [...weeks].sort(
    (a, b) =>
      (b.week_number ?? -Infinity) - (a.week_number ?? -Infinity) ||
      timestamp(b.created_at) - timestamp(a.created_at) ||
      a.id.localeCompare(b.id),
  )[0];
}
export function winnerTitle(week: WeekDetailWithRatings): string {
  return (
    week.winner_album?.title ??
    (week.winner_album_id ? 'Album details unavailable' : 'Winner pending')
  );
}
export function filterArchive(
  weeks: WeekDetailWithRatings[],
  state: ArchiveState,
): WeekDetailWithRatings[] {
  const query = state.q.trim().toLowerCase();
  return weeks
    .filter((week) => {
      const tags = week.nominations.flatMap((n) => [n.genre, n.decade, n.country]).filter(Boolean);
      return (
        (!state.tag || tags.includes(state.tag)) &&
        (!query ||
          [week.label, week.winner_album?.title, week.winner_album?.artist_name, ...tags].some(
            (value) => value?.toLowerCase().includes(query),
          ))
      );
    })
    .sort((a, b) => {
      if (state.sort === 'rating') {
        const av = a.aggregates.rating_average,
          bv = b.aggregates.rating_average;
        if (av == null && bv != null) return 1;
        if (bv == null && av != null) return -1;
        if (av != null && bv != null && av !== bv) return bv - av;
      }
      return newestFirst(a, b);
    });
}
export function formatUtc(date?: string | null, time = false): string {
  if (!date || Number.isNaN(Date.parse(date))) return 'Date unavailable';
  return (
    new Intl.DateTimeFormat('en-US', {
      timeZone: 'UTC',
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      ...(time ? { hour: '2-digit', minute: '2-digit', hour12: false } : {}),
    }).format(new Date(date)) + ' UTC'
  );
}
