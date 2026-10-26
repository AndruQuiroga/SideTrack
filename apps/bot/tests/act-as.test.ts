// Spec: platform/api-authorization and club/membership-access — the bot acts for the
// Discord user of each interaction and maintains membership as itself.
import assert from 'node:assert/strict';
import { test } from 'node:test';
import { ApiError } from '@sidetrack/api-client';
// Built output: the service uses parameter properties, which strip-only mode rejects.
import { ClubSyncService, runAsDiscordUser } from '../dist/clubService.js';

type Call = { actor: string | null; method: string; args: unknown[] };

/** Test double for SidetrackApiClient: records which actor made each call. */
function fakeClient(calls: Call[], actor: string | null = null, users = new Set<string>()): any {
  const record =
    (method: string, result: (...args: any[]) => unknown = () => ({})) =>
    async (...args: unknown[]) => {
      calls.push({ actor, method, args });
      return result(...args);
    };
  return {
    withActor: ({ discord }: { discord: string }) => fakeClient(calls, discord, users),
    lookupUserByProvider: record('lookupUserByProvider', (_provider, id: string) => {
      if (!users.has(id)) throw new ApiError('not found', 404);
      return { id: `user-${id}` };
    }),
    createUser: record('createUser', () => ({ id: 'new-user' })),
    linkAccount: record('linkAccount', (_userId, payload: { provider_user_id: string }) => {
      users.add(payload.provider_user_id);
      return {};
    }),
    putClubMember: record('putClubMember'),
    removeClubMember: record('removeClubMember'),
    createWeekNomination: record('createWeekNomination'),
    updateWeek: record('updateWeek', () => ({ id: 'week' })),
    listWeeks: record('listWeeks', () => []),
  };
}

const config = { api: { baseUrl: 'http://api' }, retry: { attempts: 1, baseDelayMs: 0 } } as any;
const logger = { info() {}, warn() {}, error() {}, debug() {} } as any;

test('calls inside an interaction act for its Discord user', async () => {
  const calls: Call[] = [];
  const service = new ClubSyncService(fakeClient(calls), config, logger);
  await runAsDiscordUser('123456789012345678', () =>
    service.recordNomination('week', { week_id: 'week', album_id: 'album' }),
  );
  await service.bootstrap();
  assert.deepEqual(
    calls.map((c) => [c.method, c.actor]),
    [
      ['createWeekNomination', '123456789012345678'],
      ['listWeeks', null],
    ],
  );
});

test('thread IDs and provisioning run as the bot itself, even inside an interaction', async () => {
  const calls: Call[] = [];
  const service = new ClubSyncService(fakeClient(calls), config, logger);
  await runAsDiscordUser('123456789012345678', async () => {
    await service.attachNominationsThread('week', '555');
    await service.recordMember('123456789012345678', 'Member', true);
  });
  assert.ok(
    calls.every((c) => c.actor === null),
    JSON.stringify(calls),
  );
  assert.deepEqual(
    calls.map((c) => c.method),
    ['updateWeek', 'lookupUserByProvider', 'createUser', 'linkAccount', 'putClubMember'],
  );
  assert.deepEqual(calls.at(-1)?.args, ['123456789012345678', 'admin']);
});

test('membership is re-recorded when the role changes, not on every interaction', async () => {
  const calls: Call[] = [];
  const service = new ClubSyncService(fakeClient(calls), config, logger);
  await service.recordMember('123456789012345678', 'Member', false);
  await service.recordMember('123456789012345678', 'Member', false);
  await service.recordMember('123456789012345678', 'Member', true);
  const puts = calls.filter((c) => c.method === 'putClubMember').map((c) => c.args[1]);
  assert.deepEqual(puts, ['member', 'admin']);
});

test('a member leaving the guild is recorded as the bot', async () => {
  const calls: Call[] = [];
  const service = new ClubSyncService(fakeClient(calls), config, logger);
  await service.recordDeparture('123456789012345678');
  assert.deepEqual(calls, [
    { actor: null, method: 'removeClubMember', args: ['123456789012345678'] },
  ]);
});
