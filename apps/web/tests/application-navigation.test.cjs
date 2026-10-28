require('./load-ts.cjs');
const { test } = require('node:test');
const assert = require('node:assert/strict');
const React = require('react');
const { renderToStaticMarkup } = require('react-dom/server');
const { navigationItems, isNavigationActive } = require('../app/lib/navigation.ts');
const { NavigationLinks } = require('../app/components/navbar.tsx');
test('navigation exposes supported destinations and marks all club routes current', () => {
  assert.deepEqual(
    navigationItems.map((n) => n.label),
    ['Overview', 'Club', 'Listening', 'Account'],
  );
  const html = renderToStaticMarkup(
    React.createElement(NavigationLinks, { pathname: '/club/weeks/week-1' }),
  );
  assert.match(html.match(/<a[^>]*href="\/club\/current"[^>]*>/)[0], /aria-current="page"/);
  assert.doesNotMatch(html, /Discover|Compatibility|Blend|Feed|\/u\//);
  assert.equal(isNavigationActive('/listening', '/u/someone/listening'), true);
});

test('overview keeps successful listening when club access fails', () => {
  const { OverviewContent } = require('../app/components/overview.tsx');
  const { listens } = require('./fixtures/club.cjs');
  for (const state of ['forbidden', 'unavailable']) {
    const html = renderToStaticMarkup(
      React.createElement(OverviewContent, {
        club: { state },
        listening: { state: 'ok', data: listens },
      }),
    );
    assert.match(html, /Platform Light/);
    assert.match(html, /Mira Vale/);
    assert.match(html, state === 'forbidden' ? /for club members/ : /unavailable right now/);
  }
});
test('signed-out overview makes no data calls and unsupported routes do not invoke APIs', async (t) => {
  const session = require('../app/lib/session.ts');
  const api = require('../app/lib/server-api.ts');
  const oldSession = session.sessionUserId,
    oldLoad = api.loadAs;
  t.after(() => {
    session.sessionUserId = oldSession;
    api.loadAs = oldLoad;
  });
  session.sessionUserId = async () => null;
  api.loadAs = async () => {
    throw new Error('Unexpected API access');
  };
  const home = await require('../app/page.tsx').default();
  assert.match(renderToStaticMarkup(home), /Sign in with Discord/);
  for (const route of ['blend', 'compare', 'discover', 'feed']) {
    const html = renderToStaticMarkup(
      React.createElement(require(`../app/${route}/page.tsx`).default),
    );
    assert.match(html, /unavailable/);
    assert.match(html, /Go to Overview/);
    assert.doesNotMatch(html, /Generate blend|Start discovering/);
  }
});
