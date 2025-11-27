import { SidetrackApiClient, TasteMetric, UUID } from '@sidetrack/shared';

import { getApiBaseUrl } from '../config';

export interface WebApiClientOptions {
  authToken?: string;
  getAuthToken?: () => string | undefined;
}

/**
 * Create a Sidetrack API client preconfigured for the web app (web/api-client).
 */
export function createWebApiClient(options?: WebApiClientOptions): SidetrackApiClient {
  return new SidetrackApiClient({
    baseUrl: getApiBaseUrl(),
    authToken: options?.authToken,
    getAuthToken: options?.getAuthToken,
  });
}

export interface CompatibilityResult {
  score: number;
  overlap?: Record<string, unknown>;
  explanation?: string;
}

export async function fetchTasteMetrics(userId: UUID, options?: WebApiClientOptions): Promise<TasteMetric[]> {
  return createWebApiClient(options).getUserTasteMetrics(userId);
}

export async function fetchCompatibility(
  userA: UUID,
  userB: UUID,
  options?: WebApiClientOptions
): Promise<CompatibilityResult> {
  const token = options?.authToken ?? options?.getAuthToken?.();
  const res = await fetch(`${getApiBaseUrl()}/users/${userA}/compatibility/${userB}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
    cache: 'no-store',
  });

  if (!res.ok) {
    throw new Error(`Compatibility lookup failed with status ${res.status}`);
  }

  return (await res.json()) as CompatibilityResult;
}
