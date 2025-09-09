import { NextResponse, type NextRequest } from 'next/server';

// Protect all routes except public ones
export function middleware(req: NextRequest) {
  const { pathname } = req.nextUrl;

  // Allow public assets and routes
  const publicPaths = [
    '/login',
    '/api',
    '/_next',
    '/favicon.ico',
    '/robots.txt',
    '/sitemap.xml',
    '/lastfm/callback',
    '/spotify/callback',
  ];
  if (publicPaths.some((p) => pathname.startsWith(p))) {
    return NextResponse.next();
  }

  const uid = req.cookies.get('uid')?.value;
  if (!uid) {
    const url = req.nextUrl.clone();
    url.pathname = '/login';
    url.searchParams.set('next', pathname);
    return NextResponse.redirect(url);
  }

  return NextResponse.next();
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico).*)'],
};

