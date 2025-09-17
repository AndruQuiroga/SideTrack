import { NextRequest, NextResponse } from 'next/server';

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'https://sidetrack.network/api';

async function proxy(req: NextRequest) {
  const headers: Record<string, string> = {};
  const uid = req.headers.get('x-user-id') || req.cookies.get('uid')?.value || '';
  if (uid) headers['X-User-Id'] = uid;
  const at = req.headers.get('authorization') || req.cookies.get('at')?.value || '';
  if (at && !headers['Authorization'])
    headers['Authorization'] = at.startsWith('Bearer ') ? at : `Bearer ${at}`;

  const search = req.nextUrl.search;
  const url = `${API_BASE}/api/v1/recs/ranked${search}`;

  const init: RequestInit = { method: req.method, headers };

  const r = await fetch(url, init);
  const data = await r.json().catch(() => ({}));

  return NextResponse.json(data, { status: r.status });
}

export async function GET(req: NextRequest) {
  return proxy(req);
}

