require('./load-ts.cjs');
const assert = require('node:assert/strict');
const { test } = require('node:test');
const React = require('react');
const { renderToStaticMarkup } = require('react-dom/server');
const { makeWeek, albums, ratings } = require('./fixtures/club.cjs');
const { WeekDetailPanel, DiscordLinks } = require('../app/components/week-detail.tsx');
const { AlbumFeature } = require('../app/components/album-feature.tsx');
const render = (C, p) => renderToStaticMarkup(React.createElement(C, p));
const week = { ...makeWeek(), winner_album: albums['album-b'], ratings, ratings_state: 'ok' };
test('album and schedule display actual metadata with explicit UTC and no phase permissions', () => {
  const html = render(AlbumFeature, { week });
  assert.match(html, /Night Transit/);
  assert.doesNotMatch(html, /My pitch is not/);
  assert.match(html, /Artwork unavailable/);
  assert.match(html, /UTC/);
  assert.doesNotMatch(html, /Voting open|Vote now|Submit rating/);
});
test('Discord links use stored destinations and missing destinations stay unavailable', () => {
  assert.match(
    render(DiscordLinks, { week, guildId: '111111111111111111' }),
    /channels\/111111111111111111\/222222222222222222/,
  );
  assert.match(
    render(DiscordLinks, { week: { ...week, ratings_thread_id: null }, guildId: '111' }),
    /Discussion link unavailable/,
  );
});
test('week detail orders reviews before results, exposes full reviews and preserves archive return', () => {
  const html = render(WeekDetailPanel, {
    week: { ...week, ratings: [{ ...ratings[0], review: 'Long review. '.repeat(50) }] },
    returnTo: '/club?q=ambient&view=list',
  });
  assert.ok(html.indexOf('Night Transit') < html.indexOf('Listener notes'));
  assert.ok(html.indexOf('Listener notes') < html.indexOf('Nomination results'));
  assert.match(html, /Read full review/);
  assert.match(html, /href="\/club\?q=ambient&amp;view=list"/);
});
test('failed reviews remain unavailable while successful empty reviews remain empty', () => {
  assert.match(
    render(WeekDetailPanel, {
      week: { ...week, ratings: undefined, ratings_state: 'unavailable' },
    }),
    /Ratings unavailable/,
  );
  assert.match(
    render(WeekDetailPanel, { week: { ...week, ratings: [], ratings_state: 'ok' } }),
    /No ratings yet/,
  );
});

test('current-week entry renders an honest empty schedule', async (t) => {
  const session = require('../app/lib/session.ts'),
    server = require('../app/lib/server-api.ts');
  const oldSession = session.sessionUserId,
    oldLoad = server.loadAs;
  t.after(() => {
    session.sessionUserId = oldSession;
    server.loadAs = oldLoad;
  });
  session.sessionUserId = async () => 'member';
  server.loadAs = async () => ({ state: 'ok', data: [] });
  const tree = await require('../app/club/current/page.tsx').default();
  const html = renderToStaticMarkup(tree);
  assert.match(html, /No weeks have been scheduled/);
  assert.doesNotMatch(html, /Open week/);
});
