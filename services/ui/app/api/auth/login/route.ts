import { NextRequest, NextResponse } from 'next/server';

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'https://sidetrack.network/api';

export async function POST(req: NextRequest) {
  const body = await req.json();
  const r = await fetch(`${API_BASE}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  const data = (await r.json().catch(() => ({}))) as { user_id?: string };
  const res = NextResponse.json(data, { status: r.status });
  if (r.ok && data?.user_id) {
    const host = req.nextUrl.hostname;
    const secure = req.nextUrl.protocol === 'https:';
    res.cookies.set('uid', String(data.user_id), {
      httpOnly: true,
      sameSite: 'lax',
      path: '/',
      maxAge: 60 * 60 * 24 * 30, // 30 days
      domain: host,
      secure,
    });
    // Exchange to a bearer token for Authorization header usage
    const tokenRes = await fetch(`${API_BASE}/auth/token/exchange`, {
      method: 'POST',
      headers: { 'X-User-Id': String(data.user_id) },
    });
    const tokenData = (await tokenRes.json().catch(() => ({}))) as {
      access_token?: string;
    };
    if (tokenRes.ok && tokenData.access_token) {
      res.cookies.set('at', tokenData.access_token, {
        httpOnly: true,
        sameSite: 'lax',
        path: '/',
        maxAge: 60 * 60 * 24 * 30,
        domain: host,
        secure,
      });
    }
  }
  return res;
}
