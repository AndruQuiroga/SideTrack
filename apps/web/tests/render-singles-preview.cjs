// Local visual QA only: render real components with synthetic fixtures and built CSS.
require('./load-ts.cjs');
const fs = require('node:fs');
const path = require('node:path');
const React = require('react');
const { renderToStaticMarkup } = require('react-dom/server');
const { session } = require('./fixtures/singles.cjs');
// Synthetic bitmap for local visual QA; no provider artwork or participant data.
const withArtwork = structuredClone(session);
withArtwork.songs[0].cover_url = 'http://127.0.0.1:8766/cover.svg';
withArtwork.songs[0].artwork_source_url = 'https://open.spotify.com/track/' + 'A'.repeat(22);
withArtwork.songs.push({
  ...structuredClone(session.songs[0]),
  id: 'song-without-artwork',
  title: 'Cover unavailable',
});
const { PageShell } = require('../app/components/page-shell.tsx');
const { ClubTabs } = require('../app/components/club-tabs.tsx');
const { NavigationLinks } = require('../app/components/navbar.tsx');
const { SinglesArchive, SinglesDetail } = require('../app/components/singles-archive.tsx');
const cssDir = path.join(__dirname, '../.next/static/css');
const css = fs
  .readdirSync(cssDir)
  .filter((name) => name.endsWith('.css'))
  .map((name) => fs.readFileSync(path.join(cssDir, name), 'utf8'))
  .join('\n');
const output = path.resolve(__dirname, '../../../.tmp/club-history/ui-preview');
fs.mkdirSync(output, { recursive: true });
fs.writeFileSync(
  path.join(output, 'cover.svg'),
  '<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200"><rect width="200" height="200" fill="#8d4638"/><circle cx="100" cy="85" r="45" fill="#e3c89d"/><text x="100" y="165" text-anchor="middle" fill="#fff" font-size="16">Synthetic cover</text></svg>',
);
for (const [file, component, props] of [
  [
    'archive.html',
    SinglesArchive,
    {
      archive: {
        state: 'ok',
        data: [
          session,
          {
            ...session,
            id: 'another-session',
            week_number: 6,
            event_date: '2025-12-22',
            song_count: 7,
            rating_count: 36,
          },
        ],
      },
    },
  ],
  ['detail.html', SinglesDetail, { session: { state: 'ok', data: withArtwork }, id: session.id }],
]) {
  const content = React.createElement(
    'div',
    { className: 'app-layout' },
    React.createElement(
      'aside',
      { className: 'sidebar' },
      React.createElement(
        'div',
        { className: 'brand-line' },
        React.createElement(
          'a',
          { className: 'brand', href: '#' },
          'side',
          React.createElement('em', null, 'track'),
          React.createElement('small', null, 'A listening journal'),
        ),
      ),
      React.createElement(
        'nav',
        { className: 'primary-nav' },
        React.createElement(NavigationLinks, { pathname: '/club/singles' }),
      ),
    ),
    React.createElement(
      'div',
      { className: 'app-content' },
      React.createElement(
        PageShell,
        {
          title:
            file === 'archive.html' ? 'One song at a time.' : 'The songs. The first impressions.',
          description:
            file === 'archive.html'
              ? 'Singles Night sessions, first impressions, and final ratings.'
              : undefined,
          accent: 'Club / Singles Night',
        },
        React.createElement(ClubTabs, { singles: true }),
        React.createElement(component, props),
      ),
    ),
  );
  fs.writeFileSync(
    path.join(output, file),
    '<!doctype html><html lang="en" class="theme-light"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Synthetic Singles Night visual check</title><style>' +
      css +
      '</style><body class="font-sans">' +
      renderToStaticMarkup(content) +
      '</body></html>',
  );
}
console.log('Rendered synthetic archive/detail views with built CSS.');
