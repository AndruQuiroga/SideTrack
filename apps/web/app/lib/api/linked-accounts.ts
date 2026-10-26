import { serverApiBaseUrl, serverApiHeaders } from '../server-env';

export type LinkedAccount = { provider: string; username?: string; display_name?: string };

export async function fetchLinkedAccounts(userId: string): Promise<LinkedAccount[] | null> {
  try {
    const res = await fetch(`${serverApiBaseUrl()}/users/${userId}/linked-accounts`, {
      headers: serverApiHeaders(),
      cache: 'no-store',
    });
    if (!res.ok) return null;
    return (await res.json()) as LinkedAccount[];
  } catch {
    return null;
  }
}
