import { NextResponse } from 'next/server';
import { getServerSession } from 'next-auth/next';

import { authOptions } from '../../../lib/auth';

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

  const apiBase =
    process.env.SIDETRACK_API_BASE_URL ||
    process.env.NEXT_PUBLIC_API_BASE_URL ||
    'http://localhost:8000';
  const siteUrl = process.env.NEXTAUTH_URL || new URL(request.url).origin;

  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (process.env.SIDETRACK_API_TOKEN) {
    headers['Authorization'] = `Bearer ${process.env.SIDETRACK_API_TOKEN}`;
  }

  const provider = encodeURIComponent(params.provider);
  const res = await fetch(`${apiBase}/integrations/${provider}/connect`, {
    method: 'POST',
    headers,
    cache: 'no-store',
    body: JSON.stringify({
      user_id: session.user.id,
      callback_url: `${siteUrl}/auth/${provider}/callback`,
    }),
  });
  const body = await res.json().catch(() => ({}));
  return NextResponse.json(body, { status: res.status });
}
