/**
 * Server-only access to the Sidetrack API for the signed-in user (ADR 0009).
 *
 * Every call carries the web app's own token and names the acting user with
 * `X-Sidetrack-Act-As: user:<id>`. The ID must come from the server session
 * (`sessionUserId()` in session.ts), never from a URL, form or request body.
 */
import { ApiError, SidetrackApiClient } from '@sidetrack/api-client';

import { readSecret, serverApiBaseUrl, serverApiHeaders } from './server-env';

/** What a page can show: data, or why there is none. */
export type Access<T> =
  | { state: 'ok'; data: T }
  | { state: 'signed-out' }
  | { state: 'forbidden' }
  | { state: 'not-found' }
  | { state: 'unavailable' };

/** An API client acting for the session user. */
export function apiForUser(userId: string): SidetrackApiClient {
  return new SidetrackApiClient({
    baseUrl: serverApiBaseUrl(),
    authToken: readSecret('SIDETRACK_WEB_API_TOKEN'),
    actAs: { user: userId },
  });
}

/** Raw JSON call acting for the session user; throws ApiError on a non-2xx status. */
export async function apiRequest<T>(
  userId: string,
  path: string,
  init: { method?: string; body?: unknown } = {},
): Promise<T> {
  const res = await fetch(`${serverApiBaseUrl()}${path}`, {
    method: init.method ?? 'GET',
    headers: serverApiHeaders(process.env, userId),
    body: init.body === undefined ? undefined : JSON.stringify(init.body),
    cache: 'no-store',
  });
  if (!res.ok) {
    const data = await res.json().catch(() => undefined);
    throw new ApiError(`API ${init.method ?? 'GET'} ${path} failed`, res.status, data);
  }
  return (await res.json()) as T;
}

/** Classify an API failure for display. */
export function accessFailure(error: unknown): Exclude<Access<never>, { state: 'ok' }> {
  if (error instanceof ApiError) {
    if (error.status === 401 || error.status === 403) return { state: 'forbidden' };
    if (error.status === 404 || error.status === 422) return { state: 'not-found' };
  }
  return { state: 'unavailable' };
}

/** Load data for the session user; anonymous visitors never reach the API. */
export async function loadAs<T>(
  userId: string | null | undefined,
  load: (api: SidetrackApiClient, userId: string) => Promise<T>,
): Promise<Access<T>> {
  if (!userId) return { state: 'signed-out' };
  try {
    return { state: 'ok', data: await load(apiForUser(userId), userId) };
  } catch (error) {
    const failure = accessFailure(error);
    if (failure.state === 'unavailable') console.error('API unavailable', error);
    return failure;
  }
}
