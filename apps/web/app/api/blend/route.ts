import { NextResponse } from 'next/server';
import { ApiError } from '@sidetrack/api-client';

import { createFriendBlend } from '../../lib/api/social';
import { sessionUserId } from '../../lib/session';

/** Generate a blend for the signed-in user; the browser never calls the API directly. */
export async function POST(request: Request) {
  const userId = await sessionUserId();
  if (!userId) return NextResponse.json({ detail: 'Sign in to create a blend.' }, { status: 401 });
  const body = (await request.json().catch(() => ({}))) as { user_a?: string; user_b?: string };
  try {
    return NextResponse.json(
      await createFriendBlend(userId, String(body.user_a ?? ''), String(body.user_b ?? '')),
    );
  } catch (error) {
    const status = error instanceof ApiError && error.status ? error.status : 502;
    return NextResponse.json({ detail: 'Blend failed.' }, { status });
  }
}
