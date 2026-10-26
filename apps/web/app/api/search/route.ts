import { NextResponse } from 'next/server';
import { ApiError } from '@sidetrack/api-client';

import { webSearch } from '../../lib/api/discover';
import { sessionUserId } from '../../lib/session';

/** Search for the signed-in user; the browser never calls the API directly. */
export async function GET(request: Request) {
  const userId = await sessionUserId();
  if (!userId) return NextResponse.json({ detail: 'Sign in to search.' }, { status: 401 });
  const query = new URL(request.url).searchParams.get('q') ?? '';
  try {
    return NextResponse.json(await webSearch(userId, query));
  } catch (error) {
    const status = error instanceof ApiError && error.status ? error.status : 502;
    return NextResponse.json({ detail: 'Search failed.' }, { status });
  }
}
