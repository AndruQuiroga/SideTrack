// Issue #296; specs: web/authenticated-pages and identity/linked-accounts.
require('./load-ts.cjs');
const assert = require('node:assert/strict');
const { test } = require('node:test');
const path = require('node:path');
const React = require('react');
const { renderToStaticMarkup } = require('react-dom/server');
const authRoot = path.resolve(path.dirname(require.resolve('next-auth/providers/discord')), '..');
const parseProviders = require(path.join(authRoot, 'core/lib/providers.js')).default;
const { openidClient } = require(path.join(authRoot, 'core/lib/oauth/client.js'));
const { authOptions } = require('../app/lib/auth.ts');
const LoginPage = require('../app/login/page.tsx').default;

async function discordClient() {
  const { provider } = parseProviders({
    providers: authOptions.providers,
    providerId: 'discord',
    url: 'https://example.test/api/auth',
  });
  assert.deepEqual(provider.checks, ['state']);
  // Synthetic credentials only; access_denied callbacks never contact a token endpoint.
  return openidClient({ provider: { ...provider, clientId: 'test', clientSecret: 'test' } });
}

test('Discord issuer is accepted before handling provider denial', async () => {
  const client = await discordClient();
  await assert.rejects(
    client.oauthCallback('https://example.test/api/auth/callback/discord', {
      iss: 'https://discord.com', state: 'expected', error: 'access_denied',
    }, { state: 'expected' }),
    (error) => error.error === 'access_denied',
  );
});

test('Discord callbacks still reject foreign issuers and incorrect state', async () => {
  const client = await discordClient();
  const callback = (iss, state) => client.oauthCallback(
    'https://example.test/api/auth/callback/discord',
    { iss, state, error: 'access_denied' }, { state: 'expected' },
  );
  await assert.rejects(callback('https://example.test', 'expected'), /iss mismatch/);
  await assert.rejects(callback('https://discord.com', 'wrong'), /state mismatch/);
});

test('login offers Discord sign-in and explains signed-in Last.fm linking', () => {
  const html = renderToStaticMarkup(React.createElement(LoginPage, { searchParams: {} }));
  assert.match(html, /Continue with Discord/);
  assert.doesNotMatch(html, /Continue with (Last.fm|Spotify|email)/);
  assert.match(html, /Last.fm/);
  assert.doesNotMatch(html, /role="alert"/);
});

test('failed callbacks display a safe message without reflecting query input', () => {
  for (const error of ['OAuthCallback', '<script>untrusted</script>']) {
    const html = renderToStaticMarkup(React.createElement(LoginPage, { searchParams: { error } }));
    assert.match(html, /role="alert"/);
    assert.match(html, /Discord sign-in did not finish/);
    assert.doesNotMatch(html, /untrusted/);
  }
});
