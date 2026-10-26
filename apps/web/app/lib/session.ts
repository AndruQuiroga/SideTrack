import { getServerSession } from 'next-auth/next';

import { authOptions } from './auth';

/** The signed-in user's Sidetrack ID from the server session, or null. */
export async function sessionUserId(): Promise<string | null> {
  const session = await getServerSession(authOptions);
  return session?.user?.id ?? null;
}
