import { NextRequest, NextResponse } from 'next/server';

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE || 'https://sidetrack.network/api';

export async function GET(req: NextRequest) {
  const headers: Record<string, string> = {};
  const uid = req.headers.get('x-user-id');
  if (uid) headers['X-User-Id'] = uid;
  const r = await fetch(`${API_BASE}/auth/me`, { headers });
  const data = await r.json().catch(() => ({}));
  return NextResponse.json(data, { status: r.status });
}
