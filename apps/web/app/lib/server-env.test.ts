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

test('server base URL is the internal address, never a public one', () => {
  assert.equal(serverApiBaseUrl({ SIDETRACK_API_BASE_URL: 'http://api:8000' }), 'http://api:8000');
  assert.equal(
    serverApiBaseUrl({ NEXT_PUBLIC_API_BASE_URL: 'https://api.sidetrack.network' }),
    'http://localhost:8000',
  );
});

test('server headers carry the web token only when configured', () => {
  assert.equal(serverApiHeaders({}).Authorization, undefined);
  assert.equal(serverApiHeaders({ SIDETRACK_WEB_API_TOKEN: 't' }).Authorization, 'Bearer t');
  // The retired shared token is not sent.
  assert.equal(serverApiHeaders({ SIDETRACK_API_TOKEN: 't' }).Authorization, undefined);
});

test('server headers name the acting session user', () => {
  const headers = serverApiHeaders({ SIDETRACK_WEB_API_TOKEN: 't' }, 'user-1');
  assert.equal(headers['X-Sidetrack-Act-As'], 'user:user-1');
  assert.equal(serverApiHeaders({ SIDETRACK_WEB_API_TOKEN: 't' })['X-Sidetrack-Act-As'], undefined);
});
