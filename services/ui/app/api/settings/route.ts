import { NextRequest, NextResponse } from 'next/server';

export async function GET(req: NextRequest) {
  const cookie = req.cookies.get('settings');
  let data = {};
  if (cookie) {
    try {
      data = JSON.parse(cookie.value);
    } catch {
      data = {};
    }
  }
  return NextResponse.json(data);
}

export async function POST(req: NextRequest) {
  const body = await req.json();
  const res = NextResponse.json({ ok: true });
  res.cookies.set('settings', JSON.stringify(body), {
    httpOnly: false,
    path: '/',
  });
  return res;
}
