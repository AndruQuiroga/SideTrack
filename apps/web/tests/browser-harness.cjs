/* Isolated review only. All identities, records and artwork in this harness are test fixtures. */
const http = require('node:http');
const net = require('node:net');
const path = require('node:path');
const { spawn } = require('node:child_process');
const { encode } = require('next-auth/jwt');
const { albums, makeWeek, ratings, listens } = require('./fixtures/club.cjs');
const secret = 'sidetrack-local-browser-test-secret-only';
const counts = {};
let reviewOrigin;
const json = (res, data, status = 200) => {
  res.writeHead(status, { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' });
  res.end(JSON.stringify(data));
};
const listen = (server) =>
  new Promise((resolve) => server.listen(0, '127.0.0.1', () => resolve(server.address().port)));
async function freePort() {
  const server = net.createServer();
  const port = await listen(server);
  await new Promise((resolve) => server.close(resolve));
  return port;
}

function testWeeks() {
  return [
    makeWeek(),
    makeWeek({
      id: 'week-41',
      week_number: 41,
      label: 'Week 41',
      discussion_at: '2026-10-21T02:00:00Z',
      winner_album_id: 'album-a',
      aggregates: { nomination_count: 2, vote_count: 9, rating_count: 10, rating_average: 4.5 },
    }),
    makeWeek({
      id: 'week-40',
      week_number: 40,
      label: 'Week 40',
      discussion_at: '2026-10-14T02:00:00Z',
      winner_album_id: 'album-c',
      aggregates: { nomination_count: 2, vote_count: 7, rating_count: 6, rating_average: 3.9 },
    }),
  ];
}

const api = http.createServer((req, res) => {
  const url = new URL(req.url, 'http://test.invalid');
  const route = url.pathname.replace(/\/$/, '');
  counts[route] = (counts[route] || 0) + 1;
  const actor = String(req.headers['x-sidetrack-act-as'] || '').replace('user:', '');
  if (actor === 'offline') return json(res, { detail: 'Test API unavailable' }, 503);
  if (
    (actor === 'outsider' || actor === 'partial') &&
    (route.startsWith('/weeks') || route === '/ratings')
  )
    return json(res, { error: 'not_a_club_member' }, 403);
  if (route === '/weeks') return json(res, actor === 'empty' ? [] : testWeeks());
  if (route.startsWith('/weeks/')) {
    const week = testWeeks().find((w) => w.id === route.split('/')[2]);
    if (!week) return json(res, { detail: 'Not found' }, 404);
    if (route.endsWith('/ratings/summary'))
      return json(res, {
        average: 4.25,
        count: 2,
        histogram: [
          { value: 3, count: 0 },
          { value: 4, count: 1 },
          { value: 4.5, count: 1 },
        ],
      });
    return json(res, week);
  }
  if (route.startsWith('/albums/')) {
    const album = albums[route.split('/')[2]];
    if (!album) return json(res, { detail: 'Not found' }, 404);
    return json(res, {
      ...album,
      cover_url:
        actor === 'missing-art'
          ? `${reviewOrigin}/__review/broken.jpg`
          : `${reviewOrigin}/__review/cover.svg?album=${album.id}`,
    });
  }
  if (route === '/ratings')
    return actor === 'ratings-failed'
      ? json(res, { detail: 'Test ratings unavailable' }, 503)
      : json(res, ratings);
  if (/\/users\/[^/]+\/listening\/recent$/.test(route)) {
    if (!route.includes(`/users/${actor}/`)) return json(res, { detail: 'Not found' }, 404);
    const offset = Number(url.searchParams.get('offset') || 0),
      limit = Number(url.searchParams.get('limit') || 50);
    if (actor === 'empty') return json(res, []);
    const data = Array.from({ length: 53 }, (_, i) => ({ ...listens[i % listens.length] }));
    return json(res, data.slice(offset, offset + limit));
  }
  if (/\/users\/[^/]+\/linked-accounts$/.test(route)) {
    if (actor === 'empty') return json(res, []);
    return json(res, [
      { provider: 'discord', display_name: 'Alex' },
      { provider: 'lastfm', display_name: 'alex_listens' },
      { provider: 'spotify', display_name: 'legacy' },
    ]);
  }
  if (route === '/search') {
    if (url.searchParams.get('q') === 'fail')
      return json(res, { detail: 'Test search unavailable' }, 503);
    const q = (url.searchParams.get('q') || '').toLowerCase();
    return json(res, {
      users: [],
      albums: Object.values(albums).filter((a) =>
        (a.title + a.artist_name).toLowerCase().includes(q),
      ),
      tracks: [],
    });
  }
  if (route === '/integrations/lastfm/connect')
    return json(res, { detail: 'Test connection unavailable' }, 503);
  return json(res, { detail: 'No test handler' }, 404);
});

let nextPort;
const proxy = http.createServer(async (req, res) => {
  const url = new URL(req.url, 'http://review.invalid');
  if (url.pathname === '/__review/session') {
    const actor = url.searchParams.get('as') || 'member';
    const token =
      actor === 'signed-out'
        ? ''
        : await encode({
            secret,
            token: { userId: actor, name: 'Alex', handle: 'alex', sub: actor },
            maxAge: 3600,
          });
    const to = url.searchParams.get('to') || '/';
    res.writeHead(302, {
      'Set-Cookie': `next-auth.session-token=${token}; Path=/; HttpOnly; SameSite=Lax${token ? '' : '; Max-Age=0'}`,
      Location: to.startsWith('/') && !to.startsWith('//') ? to : '/',
    });
    res.end();
    return;
  }
  if (url.pathname === '/__review/stats') return json(res, counts);
  if (url.pathname === '/__review/frame') {
    const width = ['320', '390', '1024'].includes(url.searchParams.get('width'))
      ? url.searchParams.get('width')
      : '390';
    const theme = url.searchParams.get('theme') === 'light' ? 'light' : 'dark';
    const actor = [
      'member',
      'empty',
      'offline',
      'outsider',
      'partial',
      'missing-art',
      'ratings-failed',
      'signed-out',
    ].includes(url.searchParams.get('as'))
      ? url.searchParams.get('as')
      : 'member';
    const to = url.searchParams.get('to') || '/';
    const target = `/__review/session?as=${actor}&to=${encodeURIComponent(to)}`;
    res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
    res.end(
      `<!doctype html><html><head><title>SideTrack isolated browser review</title><meta name="viewport" content="width=device-width,initial-scale=1"></head><body style="margin:0;background:#282828"><p style="font:12px Arial;color:#ddd;text-align:center">LOCAL TEST DATA · ${width}px · ${theme}</p><script>localStorage.setItem('sidetrack-theme', '${theme}')</script><iframe title="SideTrack application" src="${target.replace(/&/g, '&amp;')}" style="display:block;width:${width}px;height:2000px;border:0;margin:0 auto"></iframe></body></html>`,
    );
    return;
  }
  if (url.pathname === '/__review/cover.svg') {
    const key = url.searchParams.get('album');
    const palettes = {
      'album-a': ['#b65c44', '#ead6ae', '#32463e'],
      'album-b': ['#c4cbb7', '#2f504a', '#e69372'],
      'album-c': ['#cbc2a8', '#435b6b', '#dfb547'],
    };
    const [bg, shape, accent] = palettes[key] || palettes['album-b'];
    const title = albums[key]?.title || 'Test artwork';
    res.writeHead(200, { 'Content-Type': 'image/svg+xml' });
    res.end(
      `<svg xmlns="http://www.w3.org/2000/svg" width="400" height="400" viewBox="0 0 400 400"><rect width="400" height="400" fill="${bg}"/><circle cx="250" cy="280" r="125" fill="none" stroke="${shape}" stroke-width="25"/><path d="M310 -30L130 450" stroke="${accent}" stroke-width="18"/><text x="20" y="43" font-family="Arial" font-size="30" font-weight="700" fill="#1d302a">${title.toUpperCase()}</text><text x="20" y="380" font-family="Arial" font-size="10" fill="#1d302a">ILLUSTRATIVE TEST ARTWORK</text></svg>`,
    );
    return;
  }
  if (url.pathname === '/__review/broken.jpg') {
    res.writeHead(404);
    res.end();
    return;
  }
  if (url.pathname.startsWith('/api/auth/signin/') && req.method === 'POST') {
    let body = '';
    for await (const chunk of req) body += chunk;
    const callback = new URLSearchParams(body).get('callbackUrl');
    counts.lastOAuthReturn = callback;
    return json(res, { url: `${reviewOrigin}/login?review=oauth-return-checked` });
  }
  const upstream = http.request(
    {
      hostname: '127.0.0.1',
      port: nextPort,
      path: req.url,
      method: req.method,
      headers: {
        ...req.headers,
        host: `127.0.0.1:${nextPort}`,
        'x-forwarded-host': new URL(reviewOrigin).host,
        'x-forwarded-proto': 'http',
      },
    },
    (response) => {
      res.writeHead(response.statusCode, response.headers);
      response.pipe(res);
    },
  );
  upstream.on('error', () => {
    res.writeHead(503);
    res.end('Local test server is starting.');
  });
  req.pipe(upstream);
});

(async () => {
  const apiPort = await listen(api);
  nextPort = await freePort();
  reviewOrigin = `http://127.0.0.1:${await listen(proxy)}`;
  const env = {
    ...process.env,
    NODE_ENV: 'production',
    NEXTAUTH_URL: reviewOrigin,
    NEXTAUTH_SECRET: secret,
    SIDETRACK_API_BASE_URL: `http://127.0.0.1:${apiPort}`,
    SIDETRACK_WEB_API_TOKEN: 'local-test-token-only',
    DISCORD_CLIENT_ID: 'local-test-client',
    DISCORD_CLIENT_SECRET: 'local-test-secret-only',
    NEXT_PUBLIC_DISCORD_GUILD_ID: '111111111111111111',
    SIDETRACK_DISCORD_GUILD_ID: '111111111111111111',
  };
  delete env.NEXTAUTH_SECRET_FILE;
  delete env.SIDETRACK_WEB_API_TOKEN_FILE;
  delete env.DISCORD_CLIENT_SECRET_FILE;
  const child = spawn(
    process.execPath,
    [require.resolve('next/dist/bin/next'), 'start', '-H', '127.0.0.1', '-p', String(nextPort)],
    {
      cwd: path.resolve(__dirname, '..'),
      env,
      windowsHide: true,
      stdio: ['ignore', 'pipe', 'pipe'],
    },
  );
  child.stdout.on('data', (chunk) => {
    if (chunk.toString().includes('Ready')) console.log(`REVIEW_URL=${reviewOrigin}`);
  });
  child.stderr.on('data', (chunk) => process.stderr.write(chunk));
  const stop = () => {
    child.kill();
    api.close();
    proxy.close();
  };
  process.on('SIGINT', () => {
    stop();
    process.exit(0);
  });
  process.on('SIGTERM', () => {
    stop();
    process.exit(0);
  });
  child.on('exit', () => {
    api.close();
    proxy.close();
  });
})().catch((error) => {
  console.error(error.message);
  process.exitCode = 1;
});
