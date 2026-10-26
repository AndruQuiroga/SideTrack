// Spec: platform/api-authorization — clients name the acting user explicitly.
const assert = require('node:assert/strict');
const { test } = require('node:test');
const { SidetrackApiClient } = require('../dist');

function capture() {
  const seen = [];
  const adapter = async (config) => {
    seen.push(config.headers);
    return { data: [], status: 200, statusText: 'OK', headers: {}, config };
  };
  return { seen, axiosConfig: { adapter } };
}

test('sends only the client token without an actor', async () => {
  const { seen, axiosConfig } = capture();
  const client = new SidetrackApiClient({
    baseUrl: 'http://api',
    authToken: 'bot-token',
    axiosConfig,
  });
  await client.listWeeks();
  assert.equal(seen[0]['Authorization'], 'Bearer bot-token');
  assert.equal(seen[0]['X-Sidetrack-Act-As'], undefined);
});

test('withActor adds the act-as header and keeps the token', async () => {
  const { seen, axiosConfig } = capture();
  const base = new SidetrackApiClient({
    baseUrl: 'http://api',
    authToken: 'bot-token',
    axiosConfig,
  });
  await base.withActor({ discord: '123456789012345678' }).listWeeks();
  await base.withActor({ user: '6f1c0e3e-0000-4000-8000-000000000000' }).listWeeks();
  await base.listWeeks();
  assert.equal(seen[0]['X-Sidetrack-Act-As'], 'discord:123456789012345678');
  assert.equal(seen[0]['Authorization'], 'Bearer bot-token');
  assert.equal(seen[1]['X-Sidetrack-Act-As'], 'user:6f1c0e3e-0000-4000-8000-000000000000');
  assert.equal(seen[2]['X-Sidetrack-Act-As'], undefined, 'the base client is unchanged');
});
