require('./load-ts.cjs');
const assert = require('node:assert/strict');
const { test } = require('node:test');
const React = require('react');
const { renderToStaticMarkup } = require('react-dom/server');
const { RediscoveryPage } = require('../app/components/rediscovery.tsx');
const {
  describePeak,
  parseAutoplay,
  parseRediscoveryForm,
  rediscoveryHref,
} = require('../app/lib/rediscovery.ts');

const TRACK_A = '3f2c1a10-0000-4000-8000-000000000001';
const TRACK_B = '3f2c1a10-0000-4000-8000-000000000002';
const rules = {
  rule_version: 'forgotten-v1',
  min_plays: 8,
  window_days: 90,
  forgotten_days: 365,
  min_recent_plays: 50,
  min_recent_days: 20,
};
const track = (id, title, overrides = {}) => ({
  track_id: id,
  title,
  artist_name: 'Synthetic Artist',
  peak_plays: 10,
  peak_start: '2021-03-01T12:00:00Z',
  peak_end: '2021-03-10T12:00:00Z',
  last_played_at: '2021-03-10T12:00:00Z',
  total_plays: 12,
  ...overrides,
});
const data = (overrides = {}) => ({
  state: 'found',
  rules,
  include_autoplay: false,
  coverage_start: '2019-01-05T00:00:00Z',
  coverage_end: '2026-10-30T00:00:00Z',
  recent_plays: 120,
  recent_days: 40,
  excluded_autoplay_plays: 31,
  unknown_session_plays: 7,
  dismissed_hidden: 0,
  tracks: [track(TRACK_A, 'First Song'), track(TRACK_B, 'Second Song')],
  ...overrides,
});
const dismissal = {
  track_id: TRACK_B,
  title: 'Hidden Song',
  artist_name: 'Synthetic Artist',
  reason: 'not_now',
  created_at: '2026-10-01T00:00:00Z',
};
const none = { state: 'ok', data: [] };
const render = (result, props = {}) =>
  renderToStaticMarkup(
    React.createElement(RediscoveryPage, { dismissals: none, autoplay: false, result, ...props }),
  );
const ok = (overrides) => ({ state: 'ok', data: data(overrides) });

test('the list shows each track with its peak, last play and total, plus the disclosure block', () => {
  const html = render(ok());
  assert.match(html, /First Song/);
  assert.match(html, /Second Song/);
  assert.match(html, /Played a lot in March 2021: 10 plays within 90 days/);
  assert.match(html, /last played Mar 10, 2021 UTC/);
  assert.match(html, /12 plays in total/);
  assert.match(html, /Imported history covers Jan 5, 2019 UTC to Oct 30, 2026 UTC\./);
  assert.match(html, /at least 8 times within 90 days/);
  assert.match(html, /not been played for 365 days/);
  assert.match(html, /31 plays from sessions marked as autoplay were left out/);
  assert.match(html, /7 plays came from sessions that could not be classified/);
  assert.match(html, /Different versions or uploads of the same song may be counted separately/);
  assert.match(html, /forgotten-v1/);
});

test('the autoplay toggle links to the opposite choice and the forms keep it', () => {
  const off = render(ok());
  assert.match(off, /href="\/listening\/rediscover\?autoplay=1"/);
  assert.match(off, />Include autoplay sessions</);
  const on = render(ok({ include_autoplay: true }), { autoplay: true });
  assert.match(on, /href="\/listening\/rediscover"/);
  assert.match(on, />Leave out autoplay sessions</);
  assert.match(on, /Plays from sessions marked as autoplay are included/);
  assert.doesNotMatch(on, /were left out/);
  assert.match(on, /name="autoplay" value="1"/);
  assert.equal(rediscoveryHref(true), '/listening/rediscover?autoplay=1');
  assert.equal(parseAutoplay('1'), true);
  for (const value of [undefined, '', '0', 'true', 'yes'])
    assert.equal(parseAutoplay(value), false);
});

test('each state has its own message and no track rows', () => {
  const states = {
    not_imported: /No listening history has been imported/,
    coverage_gap: /Your imported history stops too early/,
    insufficient_history: /Not enough recent listening to judge/,
    none_found: /Nothing matches/,
  };
  const seen = new Set();
  for (const [state, pattern] of Object.entries(states)) {
    const html = render(ok({ state, tracks: [], recent_plays: 30, recent_days: 12 }));
    assert.match(html, pattern, state);
    assert.doesNotMatch(html, /Played a lot, not lately<\/h2>/, state);
    seen.add(html);
  }
  assert.equal(seen.size, 4);
  const gap = render(
    ok({ state: 'coverage_gap', tracks: [], coverage_end: '2026-03-14T00:00:00Z' }),
  );
  assert.match(gap, /ends Mar 14, 2026 UTC,/);
  const quiet = render(
    ok({ state: 'insufficient_history', tracks: [], recent_plays: 30, recent_days: 12 }),
  );
  assert.match(quiet, /30 plays on 12 days; at least 50 plays on 20 days/);
  const empty = render(
    ok({ state: 'not_imported', tracks: [], coverage_start: null, coverage_end: null }),
  );
  assert.doesNotMatch(empty, /How this list is made/);
  assert.doesNotMatch(empty, /Imported history covers/);
});

test('access failures are distinct from empty states', () => {
  assert.match(render({ state: 'unavailable' }), /unavailable right now/);
  assert.match(render({ state: 'signed-out' }), /Sign in to see the rediscovery list/);
  const denied = render({ state: 'not-found' });
  assert.match(denied, /is for its owner/);
  assert.doesNotMatch(denied, /Nothing matches|No listening history/);
});

test('dismiss and restore are plain posts to this site with the reason and track', () => {
  const html = render(ok(), { dismissals: { state: 'ok', data: [dismissal] } });
  assert.match(html, /<form method="post" action="\/api\/rediscovery"/);
  assert.match(html, /name="track_id" value="3f2c1a10-0000-4000-8000-000000000001"/);
  assert.match(html, /name="reason" value="not_now"/);
  assert.match(html, /name="reason" value="not_a_favourite"/);
  assert.match(html, /Hidden Song/);
  assert.match(html, /value="restore"/);
  assert.match(html, /value="restore_all"/);
  assert.match(html, />Restore all</);
  assert.doesNotMatch(render(ok()), /Restore all/);
  assert.match(
    render(ok(), { dismissals: { state: 'unavailable' } }),
    /dismissed tracks is unavailable/,
  );
});

test('posted forms are validated before they can reach the API', () => {
  const form = (fields) => {
    const body = new FormData();
    for (const [key, value] of Object.entries(fields)) body.set(key, value);
    return body;
  };
  assert.deepEqual(
    parseRediscoveryForm(
      form({ action: 'dismiss', track_id: TRACK_A, reason: 'not_now', autoplay: '1' }),
    ),
    { action: 'dismiss', trackId: TRACK_A, reason: 'not_now', autoplay: true },
  );
  assert.deepEqual(parseRediscoveryForm(form({ action: 'restore', track_id: TRACK_A })), {
    action: 'restore',
    trackId: TRACK_A,
    autoplay: false,
  });
  assert.deepEqual(parseRediscoveryForm(form({ action: 'restore_all', autoplay: '1' })), {
    action: 'restore_all',
    autoplay: true,
  });
  for (const bad of [
    {},
    { action: 'dismiss', track_id: TRACK_A },
    { action: 'dismiss', track_id: TRACK_A, reason: 'loved' },
    { action: 'dismiss', track_id: 'not-a-uuid', reason: 'not_now' },
    { action: 'restore', track_id: '../../users' },
    { action: 'delete', track_id: TRACK_A },
  ])
    assert.equal(parseRediscoveryForm(form(bad)), null);
});

test('peaks are described by period, in UTC', () => {
  assert.equal(describePeak(track(TRACK_A, 'x')), 'Played a lot in March 2021');
  assert.equal(
    describePeak(track(TRACK_A, 'x', { peak_end: '2021-05-02T00:00:00Z' })),
    'Played a lot from March 2021 to May 2021',
  );
  assert.equal(
    describePeak(
      track(TRACK_A, 'x', { peak_start: '2021-04-30T23:30:00Z', peak_end: '2021-04-30T23:59:00Z' }),
    ),
    'Played a lot in April 2021',
  );
});

test('wording and media guard: nothing is called loved, liked or your favourite, and no audio', () => {
  const pages = [
    render(ok(), { dismissals: { state: 'ok', data: [dismissal] } }),
    render(ok({ include_autoplay: true }), { autoplay: true }),
    ...['not_imported', 'coverage_gap', 'insufficient_history', 'none_found'].map((state) =>
      render(ok({ state, tracks: [] })),
    ),
    render({ state: 'unavailable' }),
    render({ state: 'signed-out' }),
    render({ state: 'not-found' }),
  ];
  for (const html of pages) {
    assert.doesNotMatch(html, /\bloved?\b|\bliked?\b|your favou?rites?\b/i);
    assert.doesNotMatch(html, /<(audio|video|source|embed|iframe|object)\b/i);
    assert.doesNotMatch(
      html,
      /\.(mp3|m4a|wav|flac|ogg|m3u8?)\b|spotify\.com|youtube\.com|youtu\.be/i,
    );
  }
  assert.match(pages[0], /Played a lot in March 2021/);
});
