require('./load-ts.cjs');
const assert = require('node:assert/strict');
const { test } = require('node:test');
const React = require('react');
const { renderToStaticMarkup } = require('react-dom/server');
const { listens } = require('./fixtures/club.cjs');
const { groupListensByUtcDay, parseListenPage } = require('../app/lib/listening.ts');
const { ListeningHistory } = require('../app/components/listening-history.tsx');
const render = (props) =>
  renderToStaticMarkup(
    React.createElement(ListeningHistory, { page: 0, path: '/listening', ...props }),
  );
test('UTC groups and displayed times agree across midnight and offsets', () => {
  const records = [
    { ...listens[0], listened_at: '2026-10-28T00:01:00Z' },
    { ...listens[0], listened_at: '2026-10-28T01:59:00+02:00' },
  ];
  assert.deepEqual(
    groupListensByUtcDay(records).map((g) => g.date),
    ['2026-10-28', '2026-10-27'],
  );
  const html = render({ result: { state: 'ok', data: records } });
  assert.match(html, /00:01/);
  assert.match(html, /23:59/);
  assert.match(html, /UTC/);
});
test('history validates page values and preserves the selected user in 50-row pagination', () => {
  for (const value of ['-1', 'bad', '2bad', '1.5', 'Infinity', '99999999999999999999'])
    assert.equal(parseListenPage(value), 0);
  assert.equal(parseListenPage('2'), 2);
  const html = render({
    page: 2,
    path: '/u/another/listening',
    result: { state: 'ok', data: Array.from({ length: 50 }, () => listens[0]) },
  });
  assert.match(html, /\/u\/another\/listening\?page=1/);
  assert.match(html, /\/u\/another\/listening\?page=3/);
});
test('empty, failed, signed-out and private histories have distinct outcomes', () => {
  assert.match(render({ result: { state: 'ok', data: [] } }), /No stored listens/);
  const failed = render({ result: { state: 'unavailable' } });
  assert.match(failed, /unavailable right now/);
  assert.doesNotMatch(failed, /No stored listens/);
  const denied = render({ result: { state: 'not-found' }, own: false });
  assert.match(denied, /for its owner/);
  assert.doesNotMatch(denied, /Platform Light|Connect Last.fm/);
  assert.match(render({ result: { state: 'signed-out' } }), /from=%2Flistening/);
});
test('history avoids complete-coverage, live-presence, and unsupported source promises', () => {
  const html = render({ result: { state: 'ok', data: listens } });
  assert.doesNotMatch(html, /Full listen log|last.sync|import progress|live presence|Link Spotify/);
  assert.match(html, /coverage can be incomplete/);
});
test('personal history entry uses the session owner without profile analytics', async (t) => {
  const session = require('../app/lib/session.ts');
  const server = require('../app/lib/server-api.ts');
  const oldSession = session.sessionUserId,
    oldLoad = server.loadAs;
  t.after(() => {
    session.sessionUserId = oldSession;
    server.loadAs = oldLoad;
  });
  const calls = [];
  session.sessionUserId = async () => 'owner';
  server.loadAs = async (id, load) => ({
    state: 'ok',
    data: await load(
      {
        getUserRecentListens: async (target, params) => {
          calls.push({ id, target, params });
          return [];
        },
      },
      id,
    ),
  });
  await require('../app/listening/page.tsx').default({ searchParams: { page: '2' } });
  assert.deepEqual(calls, [{ id: 'owner', target: 'owner', params: { limit: 50, offset: 100 } }]);
});
