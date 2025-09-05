import { NextRequest, NextResponse } from 'next/server';

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8000';

export async function GET(req: NextRequest) {
  const headers: Record<string, string> = {};
  const uid = req.headers.get('x-user-id');
  if (uid) headers['X-User-Id'] = uid;
  const r = await fetch(`${API_BASE}/settings`, { headers });
  const data = await r.json().catch(() => ({}));
  return NextResponse.json(data, { status: r.status });
}

export async function POST(req: NextRequest) {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  const uid = req.headers.get('x-user-id');
  if (uid) headers['X-User-Id'] = uid;
  const body = await req.json();
  const r = await fetch(`${API_BASE}/settings`, {
    method: 'POST',
    headers,
    body: JSON.stringify(body),
  });
  const data = await r.json().catch(() => ({}));
  return NextResponse.json(data, { status: r.status });
}
