import assert from 'node:assert/strict';
import { test } from 'node:test';

import { readSecret } from './secrets.ts';

const files: Record<string, string> = { '/run/secrets/discord': 'bot-token\r\n' };
const readFile = (path: string) => {
  const content = files[path];
  if (content === undefined) throw new Error(`ENOENT: ${path}`);
  return content;
};

test('env var wins over file', () => {
  const env = { DISCORD_BOT_TOKEN: 'env-token', DISCORD_BOT_TOKEN_FILE: '/run/secrets/discord' };
  assert.equal(readSecret('DISCORD_BOT_TOKEN', env, readFile), 'env-token');
});

test('file used when env var is unset, CRLF dropped', () => {
  const env = { DISCORD_BOT_TOKEN_FILE: '/run/secrets/discord' };
  assert.equal(readSecret('DISCORD_BOT_TOKEN', env, readFile), 'bot-token');
});

test('missing value is undefined', () => {
  assert.equal(readSecret('DISCORD_BOT_TOKEN', {}, readFile), undefined);
});

test('configured but missing file throws', () => {
  const env = { DISCORD_BOT_TOKEN_FILE: '/run/secrets/absent' };
  assert.throws(() => readSecret('DISCORD_BOT_TOKEN', env, readFile));
});
