/**
 * Browser-safe calls. They reach only this site's own /api routes, which act for the
 * session user on the server; the browser never calls the Sidetrack API (ADR 0009).
 */
import type { SearchResult } from './api/discover';
import type { BlendPreview } from './api/social';

async function json<T>(res: Response, what: string): Promise<T> {
  if (!res.ok) throw new Error(`${what} failed with status ${res.status}`);
  return (await res.json()) as T;
}

/** Start linking an external account for the signed-in user. */
export async function requestIntegrationConnect(provider: 'spotify' | 'lastfm' | 'discord') {
  const res = await fetch(`/api/link/${provider}`, { method: 'POST' });
  return json<{ status: string; url?: string }>(res, `Connect ${provider}`);
}

/** Complete a Last.fm link with the token and signed state from Last.fm's redirect. */
export async function completeLastfmLink(token: string, state: string): Promise<Response> {
  return fetch('/api/link/lastfm/callback', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ token, state }),
  });
}

export async function searchSidetrack(query: string, signal?: AbortSignal): Promise<SearchResult> {
  const res = await fetch(`/api/search?q=${encodeURIComponent(query)}`, {
    cache: 'no-store',
    signal,
  });
  return json<SearchResult>(res, 'Search');
}

export async function createFriendBlend(userA: string, userB: string): Promise<BlendPreview> {
  const res = await fetch('/api/blend', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_a: userA, user_b: userB }),
  });
  return json<BlendPreview>(res, 'Blend');
}
