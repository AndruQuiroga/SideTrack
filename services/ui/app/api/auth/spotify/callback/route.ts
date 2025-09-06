import { NextRequest, NextResponse } from 'next/server';

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8000';

export async function GET(req: NextRequest) {
  const code = req.nextUrl.searchParams.get('code') || '';
  const callback = req.nextUrl.searchParams.get('callback') || '';
  const headers: Record<string, string> = {};
  const uid = req.headers.get('x-user-id');
  if (uid) headers['X-User-Id'] = uid;
  const r = await fetch(
    `${API_BASE}/auth/spotify/callback?code=${encodeURIComponent(code)}&callback=${encodeURIComponent(callback)}`,
    { headers }
  );
  const data = await r.json().catch(() => ({}));
  return NextResponse.json(data, { status: r.status });
}
