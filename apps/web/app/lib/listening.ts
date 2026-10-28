import type { RecentListen } from '@sidetrack/api-client';
export const LISTEN_PAGE_SIZE = 50;
export function parseListenPage(value?: string): number {
  if (!value || !/^\d+$/.test(value)) return 0;
  const page = Number(value);
  return Number.isSafeInteger(page) &&
    page <= Math.floor(Number.MAX_SAFE_INTEGER / LISTEN_PAGE_SIZE)
    ? page
    : 0;
}
export function groupListensByUtcDay(
  listens: RecentListen[],
): { date: string; listens: RecentListen[] }[] {
  const groups = new Map<string, RecentListen[]>();
  for (const listen of listens) {
    const day = new Date(listen.listened_at).toISOString().slice(0, 10);
    groups.set(day, [...(groups.get(day) ?? []), listen]);
  }
  return [...groups].map(([date, records]) => ({ date, listens: records }));
}
