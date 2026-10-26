import { SidetrackApiClient, TasteMetric, UUID } from '@sidetrack/api-client';

import { apiRequest } from '../server-api';

export interface CompatibilityResult {
  score: number;
  overlap?: Record<string, unknown>;
  explanation?: string;
}

export async function fetchTasteMetrics(
  api: SidetrackApiClient,
  userId: UUID,
): Promise<TasteMetric[]> {
  return api.getUserTasteMetrics(userId);
}

/** Compatibility between the session user's view of two users (server only). */
export async function fetchCompatibility(
  sessionUserId: string,
  userA: UUID,
  userB: UUID,
): Promise<CompatibilityResult> {
  return apiRequest<CompatibilityResult>(
    sessionUserId,
    `/users/${encodeURIComponent(userA)}/compatibility/${encodeURIComponent(userB)}`,
  );
}
