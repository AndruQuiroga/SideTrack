import { NextRequest, NextResponse } from 'next/server';

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'https://sidetrack.network/api';

function buildAuthHeaders(req: NextRequest): Record<string, string> {
  const headers: Record<string, string> = {};
  const uid = req.headers.get('x-user-id') || req.cookies.get('uid')?.value || '';
  if (uid) headers['X-User-Id'] = uid;
  const authorization = req.headers.get('authorization') || req.cookies.get('at')?.value || '';
  if (authorization && !headers['Authorization']) {
    headers['Authorization'] = authorization.startsWith('Bearer ')
      ? authorization
      : `Bearer ${authorization}`;
  }
  const contentType = req.headers.get('content-type');
  if (contentType) headers['Content-Type'] = contentType;
  return headers;
}

export async function POST(req: NextRequest) {
  const headers = buildAuthHeaders(req);
  const search = req.nextUrl.searchParams.toString();
  const upstreamUrl = `${API_BASE}/api/v1/ingest/listens${search ? `?${search}` : ''}`;
  const bodyText = await req.text();
  const res = await fetch(upstreamUrl, {
    method: 'POST',
    headers,
    body: bodyText.length ? bodyText : undefined,
  });
  const data = await res.json().catch(() => ({}));
  return NextResponse.json(data, { status: res.status });
}
