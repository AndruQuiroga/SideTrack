import { NextResponse } from 'next/server';

import { serverApiBaseUrl, serverApiHeaders } from '../../../../lib/server-env';

/**
 * Completes a Last.fm link. The browser posts Last.fm's token and the signed state here;
 * the server forwards them, so the browser never calls the API (ADR 0009). The API
 * authorizes this request by the signed state, not by the session.
 */
export async function POST(request: Request, { params }: { params: { provider: string } }) {
  if (params.provider !== 'lastfm') {
    return NextResponse.json({ detail: 'Not found' }, { status: 404 });
  }
  const body = (await request.json().catch(() => ({}))) as { token?: unknown; state?: unknown };
  const res = await fetch(`${serverApiBaseUrl()}/integrations/lastfm/callback`, {
    method: 'POST',
    headers: serverApiHeaders(),
    cache: 'no-store',
    body: JSON.stringify({ token: body.token, state: body.state }),
  });
  const data = await res.json().catch(() => ({}));
  return NextResponse.json(data, { status: res.status });
}
