import { NextResponse } from 'next/server';

export async function POST() {
  const res = NextResponse.json({ ok: true });
  // Clear auth cookie
  res.cookies.set('uid', '', { path: '/', httpOnly: true, maxAge: 0, sameSite: 'lax' });
  return res;
}

