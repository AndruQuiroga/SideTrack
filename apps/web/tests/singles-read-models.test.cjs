require('./load-ts.cjs');
const assert = require('node:assert/strict');
const { test } = require('node:test');
const { fetchSinglesNights, fetchSinglesNight } = require('../app/lib/api/singles.ts');
const { loadAs } = require('../app/lib/server-api.ts');
const { session } = require('./fixtures/singles.cjs');
const { fetchSinglesGallery } = require('../app/lib/api/singles.ts');
const { ApiError } = require('@sidetrack/api-client');
const { night, currentNights } = require('./fixtures/singles-gallery.cjs');

test('home batch hydrates all seven nights and44 songs without detail-page navigation', async () => {
  const api = {
    listSinglesNights: async (args) => {
      assert.deepEqual(args, { limit: 9, offset: 0 });
      return currentNights;
    },
    getSinglesNight: async (id) => currentNights.find((n) => n.id === id),
  };
  const batch = await fetchSinglesGallery(api);
  assert.equal(batch.groups.length, 7);
  assert.equal(
    batch.groups.reduce((n, g) => n + g.detail.data.songs.length, 0),
    44,
  );
  assert.equal(batch.nextOffset, null);
  assert.deepEqual(
    batch.groups.map((g) => g.summary.id),
    currentNights.map((n) => n.id),
  );
});

test('lookahead is not hydrated and concurrency never exceeds three', async () => {
  const nights = Array.from({ length: 9 }, (_, i) => night(20 - i));
  let active = 0,
    maximum = 0,
    details = 0;
  const batch = await fetchSinglesGallery(
    {
      listSinglesNights: async () => nights,
      getSinglesNight: async (id) => {
        active++;
        details++;
        maximum = Math.max(maximum, active);
        await new Promise((resolve) => setImmediate(resolve));
        active--;
        return nights.find((n) => n.id === id);
      },
    },
    8,
  );
  assert.equal(maximum, 3);
  assert.equal(details, 8);
  assert.equal(batch.nextOffset, 16);
  assert.deepEqual(
    batch.groups.map((g) => g.summary.id),
    nights.slice(0, 8).map((n) => n.id),
  );
});

test('one failed night stays explicit while successful nights survive; auth fails globally', async () => {
  const nights = [night(3), night(2)];
  const api = {
    listSinglesNights: async () => nights,
    getSinglesNight: async (id) => {
      if (id === nights[0].id) throw new Error('Unavailable');
      return nights[1];
    },
  };
  const batch = await fetchSinglesGallery(api);
  assert.equal(batch.groups[0].detail.state, 'unavailable');
  assert.equal(batch.groups[1].detail.state, 'ok');
  api.getSinglesNight = async () => {
    throw new ApiError('Denied', 403);
  };
  await assert.rejects(fetchSinglesGallery(api), /Denied/);
  assert.deepEqual(await fetchSinglesGallery({ listSinglesNights: async () => [] }), {
    groups: [],
    nextOffset: null,
  });
});

test('list pages through exact read endpoints and detail keeps independent session identity', async () => {
  const calls = [];
  const api = {
    listSinglesNights: async (params) => {
      calls.push(params);
      return params.offset ? [session] : Array(200).fill(session);
    },
    getSinglesNight: async (id) => {
      calls.push(id);
      return session;
    },
  };
  assert.equal((await fetchSinglesNights(api)).length, 201);
  assert.deepEqual(calls.slice(0, 2), [
    { limit: 200, offset: 0 },
    { limit: 200, offset: 200 },
  ]);
  assert.equal((await fetchSinglesNight(api, session.id)).week_number, 7);
  assert.equal(calls[2], session.id);
});

test('anonymous and unavailable states remain distinct and no anonymous API call occurs', async () => {
  let called = false;
  assert.deepEqual(
    await loadAs(null, async () => {
      called = true;
    }),
    { state: 'signed-out' },
  );
  assert.equal(called, false);
  assert.deepEqual(
    await loadAs('session-user', async () => {
      throw new Error('offline');
    }),
    { state: 'unavailable' },
  );
});
