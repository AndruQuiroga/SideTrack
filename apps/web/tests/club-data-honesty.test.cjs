require('./load-ts.cjs');
const assert = require('node:assert/strict');
const { test } = require('node:test');
const React = require('react');
const { renderToStaticMarkup } = require('react-dom/server');
const { ClubGallery } = require('../app/components/club-gallery.tsx');
const { WeekDetailPanel } = require('../app/components/week-detail.tsx');

function week(count, histogram) {
  return {
    id: 'week-1',
    label: 'Week 1',
    created_at: '2026-10-28T00:00:00Z',
    nominations: [],
    ratings: [],
    aggregates: { nomination_count: 0, vote_count: 0, rating_count: count, rating_average: null },
    rating_summary: histogram === undefined ? undefined : { count, average: 3, histogram },
  };
}
const render = (Component, props) => renderToStaticMarkup(React.createElement(Component, props));

test('week count never becomes invented online presence', () => {
  for (const count of [0, 1, 11]) {
    const html = render(ClubGallery, {
      weeks: Array.from({ length: count }, (_, i) => ({ ...week(0), id: `week-${i}` })),
    });
    assert.doesNotMatch(html, /\d+ online|listeners are live|club buzzing/i);
  }
});
test('detail makes no unsupported live-listener or real-time-update claim', () => {
  assert.doesNotMatch(
    render(WeekDetailPanel, { week: week(8) }),
    /live listeners|update in real time|live updates/i,
  );
});
test('missing histogram with positive or unknown count stays unavailable', () => {
  for (const count of [8, undefined]) {
    const html = render(WeekDetailPanel, { week: week(count) });
    assert.match(html, /Distribution unavailable/);
    assert.doesNotMatch(html, /width:/);
  }
});
test('zero ratings produces no distribution bars', () => {
  const html = render(WeekDetailPanel, { week: week(0) });
  assert.match(html, /No ratings yet/);
  assert.doesNotMatch(html, /width:/);
});
test('returned distribution is preserved including zero-width bins', () => {
  const html = render(WeekDetailPanel, {
    week: week(4, [
      { value: 2, count: 0 },
      { value: 3, count: 4 },
    ]),
  });
  assert.match(html, /width:0%/);
  assert.match(html, /width:100%/);
  assert.doesNotMatch(html, /min-width/);
  assert.match(html, /2\.0/);
  assert.match(html, /3\.0/);
});
