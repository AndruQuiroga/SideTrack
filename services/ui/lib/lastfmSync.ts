import { apiFetch } from './api';

export type LastfmSyncResult = {
  ingested: number | null;
  since: string;
};

export function getLastWeekSince(): string {
  const now = new Date();
  const oneWeekAgo = new Date(Date.UTC(
    now.getUTCFullYear(),
    now.getUTCMonth(),
    now.getUTCDate(),
  ));
  oneWeekAgo.setUTCDate(oneWeekAgo.getUTCDate() - 7);
  return oneWeekAgo.toISOString().slice(0, 10);
}

export async function syncLastfmScrobbles({
  suppressErrorToast = true,
}: { suppressErrorToast?: boolean } = {}): Promise<LastfmSyncResult> {
  const since = getLastWeekSince();
  const searchParams = new URLSearchParams({ source: 'lastfm', since });
  const res = await apiFetch(`/api/v1/ingest/listens?${searchParams.toString()}`, {
    method: 'POST',
    suppressErrorToast,
  });
  let ingested: number | null = null;
  try {
    const data = (await res.json()) as { ingested?: unknown };
    if (typeof data?.ingested === 'number') {
      ingested = data.ingested;
    }
  } catch {
    // Ignore JSON parsing failures; toast messaging does not require payload
  }
  return { ingested, since };
}
