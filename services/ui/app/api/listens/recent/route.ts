import { NextRequest, NextResponse } from 'next/server';

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'https://sidetrack.network/api';

export async function GET(req: NextRequest) {
  const headers: Record<string, string> = {};
  const uid = req.headers.get('x-user-id') || req.cookies.get('uid')?.value || '';
  if (uid) headers['X-User-Id'] = uid;
  const at = req.headers.get('authorization') || req.cookies.get('at')?.value || '';
  if (at && !headers['Authorization'])
    headers['Authorization'] = at.startsWith('Bearer ') ? at : `Bearer ${at}`;
  const limit = req.nextUrl.searchParams.get('limit') || '50';
  const r = await fetch(`${API_BASE}/v1/listens/recent?limit=${encodeURIComponent(limit)}`, {
    headers,
  });
  const data = await r.json().catch(() => ({}));
  return NextResponse.json(data, { status: r.status });
}
