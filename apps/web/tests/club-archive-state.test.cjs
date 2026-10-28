require('./load-ts.cjs');
const assert = require('node:assert/strict');
const { test } = require('node:test');
const React = require('react');
const { renderToStaticMarkup } = require('react-dom/server');
const { makeWeek, albums } = require('./fixtures/club.cjs');
const { parseArchiveState, archiveUrl, filterArchive } = require('../app/lib/club.ts');
const { ClubGallery } = require('../app/components/club-gallery.tsx');
const weeks = [
  makeWeek({ winner_album: albums['album-b'] }),
  makeWeek({
    id: 'older',
    label: 'Week 41',
    discussion_at: '2026-10-21T00:00:00Z',
    winner_album: albums['album-a'],
    aggregates: { rating_average: 4.8, rating_count: 4 },
  }),
];
test('archive state round trips through normalized shareable URLs', () => {
  const state = parseArchiveState(
    new URLSearchParams('q=Ambient&tag=Ambient&sort=rating&view=list'),
  );
  assert.deepEqual(
    parseArchiveState(new URL(archiveUrl(state), 'https://example.test').searchParams),
    state,
  );
  assert.deepEqual(parseArchiveState(new URLSearchParams('sort=bad&view=bad')), {
    q: '',
    tag: '',
    sort: 'newest',
    view: 'grid',
  });
});
test('rating order puts unrated last; latest-winner feature is independent of sorting', () => {
  const state = parseArchiveState(new URLSearchParams('sort=rating&view=list'));
  const unrated = makeWeek({ id: 'unrated', aggregates: { rating_average: null } });
  assert.deepEqual(
    filterArchive([...weeks, unrated], state).map((w) => w.id),
    ['older', 'week-42', 'unrated'],
  );
  const html = renderToStaticMarkup(
    React.createElement(ClubGallery, { weeks, initialState: state }),
  );
  assert.match(html, /Latest winner:[\s\S]*?Night Transit/);
  assert.ok(html.indexOf('Soft Geometry') < html.lastIndexOf('Night Transit'));
  assert.match(html, /from=%2Fclub%3Fsort%3Drating%26view%3Dlist/);
});
test('search includes catalog artist and tags, and no-match state offers clear filters', () => {
  for (const q of ['Mira', 'Ambient'])
    assert.equal(
      filterArchive(weeks, parseArchiveState(new URLSearchParams({ q })))[0].id,
      'week-42',
    );
  const html = renderToStaticMarkup(
    React.createElement(ClubGallery, {
      weeks,
      initialState: parseArchiveState(new URLSearchParams('q=not-here')),
    }),
  );
  assert.match(html, /No weeks match these filters/);
  assert.match(html, /Clear filters/);
  assert.doesNotMatch(html, /No archive weeks yet/);
});
