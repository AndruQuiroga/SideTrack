// Spec: web/authenticated-pages (add-per-user-authorization).
require('./load-ts.cjs');
const assert = require('node:assert/strict');
const { test } = require('node:test');
const { existsSync, readdirSync, readFileSync, statSync } = require('node:fs');
const path = require('node:path');
const React = require('react');
const { renderToStaticMarkup } = require('react-dom/server');
// The api-client's own axios instance, so its defaults apply to the client under test.
const axios = require(
  require.resolve('axios', { paths: [path.dirname(require.resolve('@sidetrack/api-client'))] }),
);

const { loadAs } = require('../app/lib/server-api.ts');
const { fetchProfileForServer } = require('../app/lib/api/profile.ts');
const { ClubArchive } = require('../app/components/club-archive.tsx');

const APP = path.join(__dirname, '..', 'app');
const STATIC = path.join(__dirname, '..', '.next', 'static');

function files(dir, keep) {
  return readdirSync(dir).flatMap((name) => {
    const full = path.join(dir, name);
    if (statSync(full).isDirectory()) return files(full, keep);
    return keep(full) ? [full] : [];
  });
}

test('built client bundle holds no API token, act-as header or API address', () => {
  assert.ok(existsSync(STATIC), 'Build the web app first (pnpm --filter @sidetrack/web build).');
  for (const file of files(STATIC, (f) => f.endsWith('.js'))) {
    const text = readFileSync(file, 'utf8');
    for (const forbidden of [
      'X-Sidetrack-Act-As',
      'SIDETRACK_WEB_API_TOKEN',
      'SIDETRACK_API_BASE_URL',
      'localhost:8000',
    ]) {
      assert.ok(!text.includes(forbidden), `${path.relative(STATIC, file)} contains ${forbidden}`);
    }
  }
});

test('client components import only browser-safe modules', () => {
  const serverOnly =
    /from '[./]*(lib\/)?(server-env|server-api|session|auth)'|from '[./]*lib\/api\/[a-z-]+'/;
  for (const file of files(APP, (f) => /\.tsx?$/.test(f))) {
    const source = readFileSync(file, 'utf8');
    if (!source.startsWith("'use client'")) continue;
    for (const line of source.split('\n').filter((l) => l.startsWith('import '))) {
      if (line.startsWith('import type ')) continue;
      assert.ok(!serverOnly.test(line), `${path.relative(APP, file)}: ${line}`);
    }
  }
});

test('the acting user is never taken from a URL or request', () => {
  for (const file of files(APP, (f) => /\.tsx?$/.test(f))) {
    const source = readFileSync(file, 'utf8');
    assert.doesNotMatch(source, /loadAs\(\s*(params|searchParams|request|body)/, file);
    assert.doesNotMatch(source, /serverApiHeaders\([^)]*(params|searchParams|body)/, file);
    assert.doesNotMatch(source, /apiForUser\(\s*(params|searchParams|request|body)/, file);
  }
});

test('a profile for another user is fetched acting as the session user', async (t) => {
  const seen = [];
  const original = axios.defaults.adapter;
  t.after(() => {
    axios.defaults.adapter = original;
  });
  axios.defaults.adapter = async (config) => {
    seen.push({ url: config.url, actor: config.headers['X-Sidetrack-Act-As'] });
    return { data: { timeline: [] }, status: 200, statusText: 'OK', headers: {}, config };
  };

  const result = await loadAs('session-user', (api) => fetchProfileForServer(api, 'other-user'));

  assert.equal(result.state, 'ok');
  assert.ok(seen.length > 0);
  assert.ok(seen.some((r) => r.url.includes('/users/other-user/')));
  assert.ok(
    seen.every((r) => r.actor === 'user:session-user'),
    JSON.stringify(seen),
  );
});

test('anonymous visitors see a sign-in prompt and no weeks, without an API call', async () => {
  let called = false;
  const archive = await loadAs(null, async () => {
    called = true;
    return [];
  });
  assert.equal(called, false);
  const html = renderToStaticMarkup(React.createElement(ClubArchive, { archive }));
  assert.match(html, /Sign in to see the club archive/);
  assert.doesNotMatch(html, /WEEK|Week \d/);
});

test('a signed-in non-member is told the archive is for club members', async () => {
  const { ApiError } = require('@sidetrack/api-client');
  const archive = await loadAs('outsider', async () => {
    throw new ApiError('not a member', 403, { error: 'not_a_club_member' });
  });
  assert.equal(archive.state, 'forbidden');
  const html = renderToStaticMarkup(React.createElement(ClubArchive, { archive }));
  assert.match(html, /club archive is for club members/);
  assert.doesNotMatch(html, /unavailable/);
});
