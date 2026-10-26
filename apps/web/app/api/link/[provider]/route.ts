import { NextResponse } from 'next/server';
import { getServerSession } from 'next-auth/next';

import { authOptions } from '../../../lib/auth';
import { serverApiBaseUrl, serverApiHeaders } from '../../../lib/server-env';

/**
 * Starts linking an external account for the signed-in user.
 *
 * Runs on the server so the API service token never reaches the browser, and so
 * the user being linked is always the session's user, never a value from the client.
 */
export async function POST(request: Request, { params }: { params: { provider: string } }) {
  const session = await getServerSession(authOptions);
  if (!session?.user?.id) {
    return NextResponse.json({ detail: 'Sign in to link accounts.' }, { status: 401 });
  }

  const siteUrl = process.env.NEXTAUTH_URL || new URL(request.url).origin;

  const provider = encodeURIComponent(params.provider);
  const res = await fetch(`${serverApiBaseUrl()}/integrations/${provider}/connect`, {
    method: 'POST',
    // Acts for the session user; the API links accounts only for the acting user.
    headers: serverApiHeaders(process.env, session.user.id),
    cache: 'no-store',
    body: JSON.stringify({ callback_url: `${siteUrl}/auth/${provider}/callback` }),
  });
  const body = await res.json().catch(() => ({}));
  return NextResponse.json(body, { status: res.status });
}
