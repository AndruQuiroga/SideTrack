require('./load-ts.cjs');
const assert = require('node:assert/strict');
const { test } = require('node:test');
const React = require('react');
const { renderToStaticMarkup } = require('react-dom/server');
const { SearchResults } = require('../app/components/command-palette.tsx');
const { searchSidetrack } = require('../app/lib/browser-api.ts');
test('metadata-only search results are readable without dead destination controls', () => {
  const html = renderToStaticMarkup(
    React.createElement(SearchResults, {
      results: {
        users: [{ id: 'u', display_name: 'Listener' }],
        albums: [{ id: 'a', title: 'An album', artist_name: 'An artist' }],
        tracks: [{ id: 't', title: 'A track', artist_name: 'An artist' }],
      },
    }),
  );
  assert.match(html, /An album/);
  assert.match(html, /A track/);
  assert.match(html, /Profile pages are unavailable/);
  assert.doesNotMatch(html, /href=|<button/);
});
test('empty search explicitly says no matching records', () => {
  assert.match(
    renderToStaticMarkup(
      React.createElement(SearchResults, { results: { users: [], albums: [], tracks: [] } }),
    ),
    /No matching records/,
  );
});
test('search uses the local proxy, forwards abort signals and exposes failures', async (t) => {
  const oldFetch = global.fetch;
  t.after(() => {
    global.fetch = oldFetch;
  });
  const controller = new AbortController();
  global.fetch = async (url, options) => {
    assert.equal(url, '/api/search?q=ambient');
    assert.equal(options.signal, controller.signal);
    return new Response(null, { status: 503 });
  };
  await assert.rejects(searchSidetrack('ambient', controller.signal), /Search failed/);
});

test('Escape is consumed by the dialog before a search input can clear its value', (t) => {
  const auth = require('next-auth/react');
  const originals = {
    useState: React.useState,
    useRef: React.useRef,
    useEffect: React.useEffect,
    useSession: auth.useSession,
  };
  t.after(() => {
    React.useState = originals.useState;
    React.useRef = originals.useRef;
    React.useEffect = originals.useEffect;
    auth.useSession = originals.useSession;
  });
  React.useState = (value) => [value, () => {}];
  React.useRef = () => ({ current: null });
  React.useEffect = () => {};
  auth.useSession = () => ({ data: { user: { id: 'owner' } }, status: 'authenticated' });
  let closed = 0,
    prevented = false,
    stopped = false;
  const { CommandPalette } = require('../app/components/command-palette.tsx');
  const tree = CommandPalette({
    open: true,
    onClose: () => {
      closed++;
    },
  });
  tree.props.onKeyDown({
    key: 'Escape',
    preventDefault: () => {
      prevented = true;
    },
    stopPropagation: () => {
      stopped = true;
    },
  });
  assert.equal(closed, 1);
  assert.equal(prevented, true);
  assert.equal(stopped, true);
  tree.props.onKeyDown({ key: 'n' });
  assert.equal(closed, 1);
});
