require('./load-ts.cjs');
const assert = require('node:assert/strict');
const { test } = require('node:test');
const { fetchSinglesNights, fetchSinglesNight } = require('../app/lib/api/singles.ts');
const { loadAs } = require('../app/lib/server-api.ts');
const { session } = require('./fixtures/singles.cjs');

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
