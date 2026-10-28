require('./load-ts.cjs');
const { test } = require('node:test');
const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const React = require('react');
const { renderToStaticMarkup } = require('react-dom/server');
const { PageShell } = require('../app/components/page-shell.tsx');
const { AccessNotice, SectionHeading } = require('../app/components/ui.tsx');
const { AlbumArt } = require('../app/components/album-art.tsx');
const render = (C, p) => renderToStaticMarkup(React.createElement(C, p));
test('Journal shell has a main landmark, editorial title, and quiet sections', () => {
  const html = render(PageShell, {
    title: 'Listening',
    children: React.createElement(SectionHeading, { title: 'Today' }),
  });
  assert.match(html, /id="main-content"/);
  assert.match(html, /<h1>Listening/);
  assert.doesNotMatch(html, /gradient|rounded-full|shadow-soft|bg-emerald/);
  const css = readFileSync(require.resolve('../app/globals.css'), 'utf8');
  assert.match(css, /prefers-reduced-motion/);
  assert.match(css, /theme-light/);
  assert.match(css, /theme-dark/);
  assert.match(css, /max-width: 400px/);
  assert.doesNotMatch(css, /gradient\(/);
});
test('access states distinguish sign-in, refusal and request failure', () => {
  assert.match(
    render(AccessNotice, { state: 'signed-out', what: 'archive', returnTo: '/club?view=list' }),
    /from=%2Fclub%3Fview%3Dlist/,
  );
  const denied = render(AccessNotice, { state: 'forbidden', what: 'archive' });
  assert.match(denied, /for club members/);
  assert.doesNotMatch(denied, /unavailable/);
  assert.match(
    render(AccessNotice, { state: 'unavailable', what: 'archive' }),
    /unavailable right now/,
  );
});
test('missing and invalid artwork remain explicit', () => {
  for (const url of [null, undefined, 'javascript:bad'])
    assert.match(render(AlbumArt, { url, title: 'Album' }), /Artwork unavailable/);
  assert.match(
    render(AlbumArt, { url: 'https://images.example/cover.jpg', title: 'Album' }),
    /alt="Cover of Album"/,
  );
});

test('Journal text and control boundaries meet contrast thresholds in both themes', () => {
  const css = readFileSync(require.resolve('../app/globals.css'), 'utf8');
  const luminance = (hex) => {
    const c = hex
      .slice(1)
      .match(/../g)
      .map((v) => parseInt(v, 16) / 255)
      .map((v) => (v <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4));
    return c[0] * 0.2126 + c[1] * 0.7152 + c[2] * 0.0722;
  };
  const ratio = (a, b) =>
    (Math.max(luminance(a), luminance(b)) + 0.05) / (Math.min(luminance(a), luminance(b)) + 0.05);
  for (const block of [
    css.match(/:root,\s*\.theme-light\s*\{([^}]+)\}/)[1],
    css.match(/\.theme-dark\s*\{([^}]+)\}/)[1],
  ]) {
    const tokens = Object.fromEntries(
      [...block.matchAll(/--([a-z-]+):\s*(#[a-f0-9]+);/g)].map((m) => [m[1], m[2]]),
    );
    for (const foreground of ['ink', 'secondary', 'accent'])
      for (const background of ['canvas', 'surface'])
        assert.ok(
          ratio(tokens[foreground], tokens[background]) >= 4.5,
          `${foreground}/${background} text contrast`,
        );
    for (const background of ['canvas', 'surface'])
      assert.ok(ratio(tokens.line, tokens[background]) >= 3, `control boundary/${background}`);
  }
});

test('loading, not-found and error screens keep the shared layout and safe messages', () => {
  const { PageLoading } = require('../app/components/page-loading.tsx');
  const NotFound = require('../app/not-found.tsx').default;
  const PageError = require('../app/error.tsx').default;
  assert.match(render(PageLoading, {}), /role="status"/);
  assert.match(render(NotFound, {}), /Page not found/);
  const failed = render(PageError, {
    error: new Error('internal-only diagnostic'),
    reset: () => {},
  });
  assert.match(failed, /Try again/);
  assert.doesNotMatch(failed, /internal-only diagnostic|<html|<body/);
});
