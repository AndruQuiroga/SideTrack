import assert from 'node:assert/strict';
import { test } from 'node:test';
import { NotificationDelivery, PermanentDeliveryError } from '../src/notificationDelivery.ts';

const event = { id: 'event', lease_token: 'token', thread_id: '123', message: 'Notice' };
const logger = { info() {}, warn() {}, error() {}, debug() {} };
const settle = () => new Promise<void>((resolve) => setImmediate(resolve));

test('acknowledges only after successful Discord delivery', async () => {
  const actions: string[] = [];
  const api = {
    async claimNotifications() {
      return [event];
    },
    async acknowledgeNotification(id: string, token: string, messageId: string) {
      actions.push(`ack:${id}:${token}:${messageId}`);
    },
    async failNotification() {
      actions.push('fail');
    },
  };
  const pump = new NotificationDelivery(
    api,
    async () => {
      actions.push('send');
      return '456';
    },
    logger,
  );
  pump.start();
  await settle();
  await pump.stop();
  assert.deepEqual(actions, ['send', 'ack:event:token:456']);
});

test('a stopped bot leaves a late claim leased for another bot', async () => {
  let release!: (events: (typeof event)[]) => void;
  let sends = 0;
  const api = {
    claimNotifications: () =>
      new Promise<(typeof event)[]>((resolve) => {
        release = resolve;
      }),
    async acknowledgeNotification() {
      assert.fail('unexpected ack');
    },
    async failNotification() {
      assert.fail('unexpected failure');
    },
  };
  const pump = new NotificationDelivery(
    api,
    async () => {
      sends++;
      return '456';
    },
    logger,
  );
  pump.start();
  const stopping = pump.stop();
  release([event]);
  await stopping;
  assert.equal(sends, 0);
});

test('send success and lost acknowledgment leaves recovery possible', async () => {
  let sends = 0;
  let failures = 0;
  const api = {
    async claimNotifications() {
      return [event];
    },
    async acknowledgeNotification() {
      throw new Error('API unavailable');
    },
    async failNotification() {
      failures++;
    },
  };
  for (let restart = 0; restart < 2; restart++) {
    const pump = new NotificationDelivery(
      api,
      async () => {
        sends++;
        return '456';
      },
      logger,
    );
    pump.start();
    await settle();
    await pump.stop();
  }
  // At-least-once send/ack semantics explicitly allow this duplicate window.
  assert.equal(sends, 2);
  assert.equal(failures, 0);
});

test('transient and permanent target failures are reported separately', async () => {
  for (const permanent of [false, true]) {
    const outcomes: boolean[] = [];
    const api = {
      async claimNotifications() {
        return [event];
      },
      async acknowledgeNotification() {
        assert.fail('failed send was acknowledged');
      },
      async failNotification(_id: string, _token: string, value: boolean) {
        outcomes.push(value);
      },
    };
    const pump = new NotificationDelivery(
      api,
      async () => {
        throw permanent
          ? new PermanentDeliveryError('missing target')
          : new Error('connection reset');
      },
      logger,
    );
    pump.start();
    await settle();
    await pump.stop();
    assert.deepEqual(outcomes, [permanent]);
  }
});
