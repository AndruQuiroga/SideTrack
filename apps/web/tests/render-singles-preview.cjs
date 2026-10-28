// Local visual QA only: render real components with synthetic fixtures and built CSS.
require('./load-ts.cjs');
const fs = require('node:fs');
const path = require('node:path');
const React = require('react');
const { renderToStaticMarkup } = require('react-dom/server');
const { session } = require('./fixtures/singles.cjs');
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
  ['detail.html', SinglesDetail, { session: { state: 'ok', data: session }, id: session.id }],
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
