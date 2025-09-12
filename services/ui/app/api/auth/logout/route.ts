import { NextResponse } from 'next/server';

export async function POST(req: Request) {
  const res = NextResponse.json({ ok: true });
  // Clear auth cookie
  const url = new URL(req.url);
  res.cookies.set('uid', '', {
    path: '/',
    httpOnly: true,
    maxAge: 0,
    sameSite: 'lax',
    domain: url.hostname,
    secure: url.protocol === 'https:',
  });
  return res;
}
