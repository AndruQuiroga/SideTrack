import assert from 'node:assert/strict';
import { test } from 'node:test';

import { readSecret, serverApiBaseUrl, serverApiHeaders } from './server-env.ts';

const files: Record<string, string> = { '/run/secrets/token': 'from-file\n' };
const readFile = (path: string) => {
  const content = files[path];
  if (content === undefined) throw new Error(`ENOENT: ${path}`);
  return content;
};

test('env var wins over file', () => {
  const env = { TOKEN: 'from-env', TOKEN_FILE: '/run/secrets/token' };
  assert.equal(readSecret('TOKEN', env, readFile), 'from-env');
});

test('file used when env var is unset, trailing newline dropped', () => {
  assert.equal(readSecret('TOKEN', { TOKEN_FILE: '/run/secrets/token' }, readFile), 'from-file');
});

test('missing value is undefined', () => {
  assert.equal(readSecret('TOKEN', {}, readFile), undefined);
});

test('configured but missing file throws', () => {
  assert.throws(() => readSecret('TOKEN', { TOKEN_FILE: '/run/secrets/absent' }, readFile));
});

test('server base URL prefers the internal address', () => {
  const env = {
    SIDETRACK_API_BASE_URL: 'http://api:8000',
    NEXT_PUBLIC_API_BASE_URL: 'https://api.sidetrack.network',
  };
  assert.equal(serverApiBaseUrl(env), 'http://api:8000');
});

test('server headers carry the token only when configured', () => {
  assert.equal(serverApiHeaders({}).Authorization, undefined);
  assert.equal(serverApiHeaders({ SIDETRACK_API_TOKEN: 't' }).Authorization, 'Bearer t');
});
