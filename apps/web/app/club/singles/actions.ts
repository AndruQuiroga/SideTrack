'use server';

import { fetchSinglesGallery, fetchSinglesNight, validGalleryOffset } from '../../lib/api/singles';
import { loadAs } from '../../lib/server-api';
import { sessionUserId } from '../../lib/session';

export async function loadOlderSinglesNights(offset: number) {
  const user = await sessionUserId();
  if (!user) return { state: 'signed-out' as const };
  if (!validGalleryOffset(offset)) return { state: 'unavailable' as const };
  return loadAs(user, (api) => fetchSinglesGallery(api, offset));
}

export async function retrySinglesNight(id: string) {
  const user = await sessionUserId();
  if (!user) return { state: 'signed-out' as const };
  if (
    typeof id !== 'string' ||
    !/^[a-f\d]{8}-[a-f\d]{4}-[a-f\d]{4}-[a-f\d]{4}-[a-f\d]{12}$/i.test(id)
  ) {
    return { state: 'unavailable' as const };
  }
  return loadAs(user, (api) => fetchSinglesNight(api, id));
}
