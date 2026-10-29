require('./load-ts.cjs');
const assert = require('node:assert/strict');
const { test } = require('node:test');
const React = require('react');
const { renderToStaticMarkup } = require('react-dom/server');
const { SinglesArchive, SinglesDetail } = require('../app/components/singles-archive.tsx');
const { ClubTabs } = require('../app/components/club-tabs.tsx');
const { session } = require('./fixtures/singles.cjs');
const render = (component, props) => renderToStaticMarkup(React.createElement(component, props));

test('verified song covers link to provider while absent covers remain unavailable', () => {
  const event = structuredClone(session);
  event.songs[0].cover_url = 'https://i.scdn.co/image/synthetic';
  event.songs[0].artwork_source_url = 'https://open.spotify.com/track/' + 'A'.repeat(22);
  const html = render(SinglesDetail, { session: { state: 'ok', data: event }, id: event.id });
  assert.match(html, /https:\/\/i.scdn.co\/image\/synthetic/);
  assert.match(html, /Cover of Night Transit by The Paper Satellites/);
  assert.match(html, /Artwork source for Night Transit/);
  event.songs[0].cover_url = null;
  assert.match(
    render(SinglesDetail, { session: { state: 'ok', data: event }, id: event.id }),
    /Artwork unavailable/,
  );
});

test('independent session links and active Singles navigation', () => {
  const html = render(SinglesArchive, { archive: { state: 'ok', data: [session] } });
  assert.match(html, /Singles Night 7/);
  assert.match(html, new RegExp(`/club/singles/${session.id}`));
  assert.doesNotMatch(html, /\/club\/weeks\//);
  const tabs = render(ClubTabs, { singles: true });
  assert.match(tabs, /<a (?=[^>]*href="\/club\/singles")(?=[^>]*aria-current="page")[^>]*>/);
});

test('corrected calendar date, original evidence, absent time and separate first/final sections', () => {
  const html = render(SinglesDetail, { session: { state: 'ok', data: session }, id: session.id });
  assert.match(html, /Jan 14, 2026/);
  assert.match(html, /1-14-2025/);
  assert.doesNotMatch(html, /00:00|12:00|UTC/);
  assert.match(html, /First listen/);
  assert.match(html, /Final ratings/);
  assert.match(html, /3.5 \/ 5/);
  assert.match(html, /4.5 \/ 5/);
  assert.match(html, /Submitted by Synthetic submitter/);
  assert.match(html, /https:\/\/discord.com\/channels\/1\/100\/102/);
});

test('deleted attribution is unavailable while other listeners remain', () => {
  const event = structuredClone(session);
  event.songs[0].submissions = [];
  event.songs[0].ratings = event.songs[0].ratings.slice(1);
  const html = render(SinglesDetail, { session: { state: 'ok', data: event }, id: event.id });
  assert.match(html, /Submitter unavailable/);
  assert.match(html, /Another listener/);
  assert.doesNotMatch(html, /Synthetic submitter|Synthetic listener/);
  assert.match(html, /No first-listen ratings recorded/);
});

test('empty, unavailable, membership and signed-out states stay distinct', () => {
  assert.match(
    render(SinglesArchive, { archive: { state: 'ok', data: [] } }),
    /No Singles Night sessions yet/,
  );
  assert.match(render(SinglesArchive, { archive: { state: 'unavailable' } }), /unavailable/i);
  assert.match(render(SinglesArchive, { archive: { state: 'forbidden' } }), /for club members/);
  assert.match(render(SinglesArchive, { archive: { state: 'signed-out' } }), /Sign in/);
  assert.match(
    render(SinglesDetail, { session: { state: 'not-found' }, id: 'missing' }),
    /Session not found/,
  );
});
