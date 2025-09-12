import { NextResponse } from 'next/server';

export async function POST(req: Request) {
  const res = NextResponse.json({ ok: true });
  // Clear auth cookie
  const url = new URL(req.url);
  const host = url.hostname;
  const secure = url.protocol === 'https:';
  const configuredDomain = process.env.AUTH_COOKIE_DOMAIN || '';
  const isLocal = host === 'localhost' || /^\d+\.\d+\.\d+\.\d+$/.test(host);
  const baseClear = {
    path: '/',
    httpOnly: true,
    maxAge: 0,
    sameSite: 'lax',
    ...(secure ? { secure: true } : {}),
    ...(configuredDomain ? { domain: configuredDomain } : !isLocal ? { domain: host } : {}),
  } as const;
  res.cookies.set('uid', '', baseClear);
  res.cookies.set('at', '', baseClear);
  return res;
}
