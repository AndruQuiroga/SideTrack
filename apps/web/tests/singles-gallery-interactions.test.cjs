require('./load-ts.cjs');
const assert = require('node:assert/strict');
const { test } = require('node:test');
const { GalleryStore } = require('../app/lib/singles-gallery.ts');
const { night, group } = require('./fixtures/singles-gallery.cjs');
const initial = () => ({ state: 'ok', data: { groups: [group(night(7))], nextOffset: 8 } });
function deferred() {
  let resolve;
  const promise = new Promise((r) => {
    resolve = r;
  });
  return { promise, resolve };
}

test('duplicate older clicks are suppressed; stable existing groups survive append and deduplication', async () => {
  const store = new GalleryStore(initial()),
    pending = deferred();
  let calls = 0;
  const original = store.getSnapshot().access.data.groups[0];
  const action = () => {
    calls++;
    return pending.promise;
  };
  const first = store.older(action);
  await store.older(action);
  assert.equal(calls, 1);
  pending.resolve({
    state: 'ok',
    data: { groups: [group(night(7)), group(night(6))], nextOffset: 16 },
  });
  await first;
  assert.equal(store.getSnapshot().access.data.groups.length, 2);
  assert.equal(store.getSnapshot().access.data.groups[0], original);
  assert.equal(store.getSnapshot().access.data.nextOffset, 16);
});
test('failed older loads retry in place and a group retry replaces only its own detail', async () => {
  const store = new GalleryStore(initial());
  await store.older(async () => {
    throw new Error('network');
  });
  assert.equal(store.getSnapshot().olderFailed, true);
  await store.older(async () => ({
    state: 'ok',
    data: { groups: [group(night(6))], nextOffset: null },
  }));
  const original = store.getSnapshot().access.data.groups[0];
  await store.retry(night(6).id, async () => ({ state: 'unavailable' }));
  assert.equal(store.getSnapshot().access.data.groups[0], original);
  assert.equal(store.getSnapshot().access.data.groups[1].detail.state, 'unavailable');
  await store.retry(night(6).id, async () => ({ state: 'ok', data: night(6) }));
  assert.equal(store.getSnapshot().access.data.groups[1].detail.state, 'ok');
  assert.equal(store.getSnapshot().access.data.groups.length, 2);
});
test('access loss clears gallery and late successful responses cannot restore it', async () => {
  const store = new GalleryStore(initial()),
    older = deferred();
  const pending = store.older(() => older.promise);
  await store.retry(night(7).id, async () => ({ state: 'forbidden' }));
  assert.deepEqual(store.getSnapshot().access, { state: 'forbidden' });
  older.resolve({ state: 'ok', data: { groups: [group(night(6))], nextOffset: null } });
  await pending;
  assert.deepEqual(store.getSnapshot().access, { state: 'forbidden' });
  assert.deepEqual(store.getSnapshot().pending, []);
});
