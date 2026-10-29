import type { SidetrackApiClient, SinglesSessionRead } from '@sidetrack/api-client';
import { accessFailure } from '../server-api';
import type { GalleryBatch, GalleryGroup } from '../singles-gallery';

export const GALLERY_BATCH_SIZE = 8;
export const GALLERY_CONCURRENCY = 3;

export function validGalleryOffset(offset: unknown): offset is number {
  return typeof offset === 'number' && Number.isSafeInteger(offset) && offset >= 0;
}

export async function fetchSinglesGallery(
  api: SidetrackApiClient,
  offset = 0,
): Promise<GalleryBatch> {
  if (!validGalleryOffset(offset)) throw new Error('Invalid gallery offset');
  const summaries = await api.listSinglesNights({ limit: GALLERY_BATCH_SIZE + 1, offset });
  const selected = summaries.slice(0, GALLERY_BATCH_SIZE);
  const groups: GalleryGroup[] = new Array(selected.length);
  let cursor = 0;
  await Promise.all(
    Array.from({ length: Math.min(GALLERY_CONCURRENCY, selected.length) }, async () => {
      for (;;) {
        const index = cursor++;
        if (index >= selected.length) return;
        const summary = selected[index];
        try {
          const detail = await api.getSinglesNight(summary.id);
          if (detail.id !== summary.id) throw new Error('Session identity mismatch');
          groups[index] = { summary, detail: { state: 'ok', data: detail } };
        } catch (error) {
          const failure = accessFailure(error);
          if (failure.state === 'forbidden' || failure.state === 'signed-out') throw error;
          groups[index] = { summary, detail: failure };
        }
      }
    }),
  );
  return {
    groups,
    nextOffset: summaries.length > GALLERY_BATCH_SIZE ? offset + selected.length : null,
  };
}

/** Server callers derive the actor from their session before passing this client. */
export async function fetchSinglesNights(api: SidetrackApiClient): Promise<SinglesSessionRead[]> {
  const result: SinglesSessionRead[] = [];
  const limit = 200;
  for (let offset = 0; ; offset += limit) {
    const page = await api.listSinglesNights({ limit, offset });
    result.push(...page);
    if (page.length < limit) return result;
  }
}

export async function fetchSinglesNight(api: SidetrackApiClient, id: string) {
  return api.getSinglesNight(id);
}
