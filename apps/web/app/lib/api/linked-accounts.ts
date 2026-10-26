import { serverApiBaseUrl, serverApiHeaders } from '../server-env';

export type LinkedAccount = { provider: string; username?: string; display_name?: string };

/** The session user's own linked accounts; null when the lookup fails. */
export async function fetchLinkedAccounts(sessionUserId: string): Promise<LinkedAccount[] | null> {
  try {
    const res = await fetch(`${serverApiBaseUrl()}/users/${sessionUserId}/linked-accounts`, {
      headers: serverApiHeaders(process.env, sessionUserId),
      cache: 'no-store',
    });
    if (!res.ok) return null;
    return (await res.json()) as LinkedAccount[];
  } catch {
    return null;
  }
}
