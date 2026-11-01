import { NextResponse } from 'next/server';

import { apiForUser } from '../../lib/server-api';
import { parseRediscoveryForm, rediscoveryHref } from '../../lib/rediscovery';
import { sessionUserId } from '../../lib/session';

/**
 * Dismiss or restore a forgotten-favourites track for the signed-in user.
 *
 * The user comes from the server session, never the form, and the browser never sees the
 * API token. Posts from other origins are refused.
 */
export async function POST(request: Request) {
  const origin = request.headers.get('origin');
  const site = process.env.NEXTAUTH_URL ? new URL(process.env.NEXTAUTH_URL).origin : null;
  if (origin && origin !== (site ?? new URL(request.url).origin)) {
    return NextResponse.json({ detail: 'Cross-site request refused.' }, { status: 403 });
  }
  const userId = await sessionUserId();
  if (!userId) return NextResponse.json({ detail: 'Sign in first.' }, { status: 401 });
  const parsed = parseRediscoveryForm(await request.formData());
  if (!parsed) return NextResponse.json({ detail: 'Invalid request.' }, { status: 400 });

  const api = apiForUser(userId);
  try {
    if (parsed.action === 'dismiss') {
      await api.dismissRediscoveryTrack(userId, parsed.trackId, parsed.reason);
    } else if (parsed.action === 'restore') {
      await api.restoreRediscoveryTrack(userId, parsed.trackId);
    } else {
      await api.restoreAllRediscoveryTracks(userId);
    }
  } catch (error) {
    console.error('Rediscovery update failed', error);
    return NextResponse.json({ detail: 'The change could not be saved.' }, { status: 502 });
  }
  const base = site ?? new URL(request.url).origin;
  return NextResponse.redirect(new URL(rediscoveryHref(parsed.autoplay), base), 303);
}
