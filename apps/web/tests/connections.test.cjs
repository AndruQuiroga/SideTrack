require('./load-ts.cjs');
const assert = require('node:assert/strict');
const { test } = require('node:test');
const React = require('react');
const { renderToStaticMarkup } = require('react-dom/server');
const { ConnectionsGrid } = require('../app/components/connections-grid.tsx');
const { fetchLinkedAccounts } = require('../app/lib/api/linked-accounts.ts');

const lastfm = (linked) => ({
  name: 'Last.fm',
  key: 'lastfm',
  status: 'Account status',
  linked,
  cta: linked ? 'Reconnect' : 'Connect Last.fm',
});

test('missing account data renders unavailable, never a fabricated connection', () => {
  for (const props of [{ connections: null }, {}]) {
    const html = renderToStaticMarkup(React.createElement(ConnectionsGrid, props));
    assert.match(html, /Linked accounts are unavailable/);
    assert.doesNotMatch(html, /Reconnect|>Linked</);
  }
});

test('successful empty account lookup displays not linked', () => {
  const html = renderToStaticMarkup(
    React.createElement(ConnectionsGrid, { connections: [lastfm(false)] }),
  );
  assert.match(html, /Not linked/);
  assert.match(html, /Connect Last.fm/);
  assert.doesNotMatch(html, /Reconnect|>Linked</);
});

test('supplied Last.fm linkage displays linked', () => {
  const html = renderToStaticMarkup(
    React.createElement(ConnectionsGrid, { connections: [lastfm(true)] }),
  );
  assert.match(html, />Linked</);
  assert.match(html, /Reconnect/);
});

test('account lookup distinguishes success, HTTP failure and network failure', async (t) => {
  const originalFetch = global.fetch;
  t.after(() => {
    global.fetch = originalFetch;
  });
  global.fetch = async () => Response.json([]);
  assert.deepEqual(await fetchLinkedAccounts('user'), []);
  global.fetch = async () => Response.json([{ provider: 'lastfm', display_name: 'listener' }]);
  assert.deepEqual(await fetchLinkedAccounts('user'), [
    { provider: 'lastfm', display_name: 'listener' },
  ]);
  global.fetch = async () => new Response(null, { status: 503 });
  assert.equal(await fetchLinkedAccounts('user'), null);
  global.fetch = async () => {
    throw new Error('offline');
  };
  assert.equal(await fetchLinkedAccounts('user'), null);
});
