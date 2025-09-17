import { NextRequest, NextResponse } from 'next/server';

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'https://sidetrack.network/api';

export async function GET(req: NextRequest) {
  const headers: Record<string, string> = {};
  const uid = req.headers.get('x-user-id') || req.cookies.get('uid')?.value || '';
  if (uid) headers['X-User-Id'] = uid;
  const at = req.headers.get('authorization') || req.cookies.get('at')?.value || '';
  if (at && !headers['Authorization'])
    headers['Authorization'] = at.startsWith('Bearer ') ? at : `Bearer ${at}`;
  const upstreamUrl = new URL(`${API_BASE}/api/v1/dashboard/outliers`);
  req.nextUrl.searchParams.forEach((value, key) => {
    upstreamUrl.searchParams.set(key, value);
  });
  if (!upstreamUrl.searchParams.has('range')) {
    upstreamUrl.searchParams.set('range', '12w');
  }

  const r = await fetch(upstreamUrl, {
    headers,
  });
  const data = await r.json().catch(() => ({}));
  return NextResponse.json(data, { status: r.status });
}
