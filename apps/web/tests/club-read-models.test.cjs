require('./load-ts.cjs');
const assert = require('node:assert/strict');
const { test } = require('node:test');
const { makeWeek, albums, ratings } = require('./fixtures/club.cjs');
const { fetchWeekList, fetchScheduledWeeks, fetchWeekDetail } = require('../app/lib/api/weeks.ts');
const { latestScheduled } = require('../app/lib/club.ts');
function client(weeks) {
  const calls = [];
  return {
    calls,
    listWeeks: async (params) => {
      calls.push(['weeks', params]);
      return weeks;
    },
    getWeek: async () => weeks[0],
    getAlbum: async (id) => {
      calls.push(['album', id]);
      return albums[id];
    },
    getWeekRatingSummary: async () => {
      calls.push(['summary']);
      return { average: 4.25, count: 2 };
    },
    listRatings: async () => ratings,
  };
}
test('archive resolves the stored winner and deduplicates catalog reads without summary fan-out', async () => {
  const api = client([makeWeek(), makeWeek({ id: 'another' })]);
  const result = await fetchWeekList(api);
  assert.equal(result[0].winner_album.title, 'Night Transit');
  assert.equal(api.calls.filter((c) => c[0] === 'album').length, 1);
  assert.equal(api.calls.filter((c) => c[0] === 'summary').length, 0);
  assert.deepEqual(api.calls[0], ['weeks', { has_winner: true }]);
});
test('admin override resolves an album absent from nominations; catalog failures remain missing', async () => {
  const api = client([makeWeek({ winner_album_id: 'album-c' })]);
  assert.equal((await fetchWeekList(api))[0].winner_album.title, 'Open Water');
  api.getAlbum = async () => {
    throw new Error('offline');
  };
  assert.equal((await fetchWeekList(api))[0].winner_album, null);
});
test('latest scheduled includes future pending weeks and orders nulls and ties deterministically', async () => {
  const past = makeWeek({ id: 'past' });
  const future = makeWeek({
    id: 'future',
    week_number: 43,
    winner_album_id: null,
    discussion_at: '2027-01-01T00:00:00Z',
  });
  const noNumber = makeWeek({
    id: 'no-number',
    week_number: null,
    created_at: '2029-01-01T00:00:00Z',
  });
  const api = client([noNumber, past, future]);
  assert.equal(latestScheduled(await fetchScheduledWeeks(api)).id, 'future');
  assert.deepEqual(api.calls[0], ['weeks', undefined]);
  assert.equal(latestScheduled([makeWeek({ id: 'b' }), makeWeek({ id: 'a' })]).id, 'a');
  assert.equal(latestScheduled([]), undefined);
});
test('detail separates optional failures from successful empty data', async () => {
  const api = client([makeWeek()]);
  api.listRatings = async () => {
    throw new Error('offline');
  };
  api.getWeekRatingSummary = async () => {
    throw new Error('offline');
  };
  const failed = await fetchWeekDetail(api, 'week-42');
  assert.equal(failed.ratings_state, 'unavailable');
  assert.equal(failed.ratings, undefined);
  assert.equal(failed.rating_summary_state, 'unavailable');
  api.listRatings = async () => [];
  assert.deepEqual((await fetchWeekDetail(api, 'week-42')).ratings, []);
  assert.equal(failed.nomination_albums['album-a'].title, 'Soft Geometry');
});
