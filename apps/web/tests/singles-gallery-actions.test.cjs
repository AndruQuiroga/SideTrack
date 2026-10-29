require('./load-ts.cjs');
const assert = require('node:assert/strict');
const { test } = require('node:test');
const Module = require('node:module');
const path = require('node:path');
const { night } = require('./fixtures/singles-gallery.cjs');
const axios = require(
  require.resolve('axios', { paths: [path.dirname(require.resolve('@sidetrack/api-client'))] }),
);
let user = null;
const originalLoad = Module._load;
Module._load = function (request, ...args) {
  if (request === '../../lib/session') return { sessionUserId: async () => user };
  return originalLoad.call(this, request, ...args);
};
let actions;
try {
  actions = require('../app/club/singles/actions.ts');
} finally {
  Module._load = originalLoad;
}

test('actions re-read the session and reject missing users and invalid inputs before API calls', async (t) => {
  const original = axios.defaults.adapter;
  t.after(() => {
    axios.defaults.adapter = original;
  });
  const calls = [];
  const event = night(7);
  axios.defaults.adapter = async (config) => {
    calls.push({ url: config.url, actor: config.headers['X-Sidetrack-Act-As'] });
    return {
      data: config.url.endsWith(event.id) ? event : [],
      status: 200,
      statusText: 'OK',
      headers: {},
      config,
    };
  };
  user = null;
  assert.equal((await actions.loadOlderSinglesNights(0)).state, 'signed-out');
  assert.equal((await actions.retrySinglesNight(event.id)).state, 'signed-out');
  user = 'member-a';
  for (const offset of [-1, 1.2, '0', Infinity, Number.MAX_VALUE])
    assert.equal((await actions.loadOlderSinglesNights(offset)).state, 'unavailable');
  assert.equal((await actions.retrySinglesNight('https://evil.test/')).state, 'unavailable');
  assert.equal(calls.length, 0);
  assert.equal((await actions.loadOlderSinglesNights(8)).state, 'ok');
  assert.equal(calls[0].actor, 'user:member-a');
  user = 'member-b';
  assert.equal((await actions.retrySinglesNight(event.id)).state, 'ok');
  assert.equal(calls.at(-1).actor, 'user:member-b');
  axios.defaults.adapter = async (config) => {
    const error = new axios.AxiosError('Denied', undefined, config, undefined, {
      status: 403,
      data: {},
      headers: {},
      statusText: 'Forbidden',
      config,
    });
    throw error;
  };
  assert.equal((await actions.retrySinglesNight(event.id)).state, 'forbidden');
});
