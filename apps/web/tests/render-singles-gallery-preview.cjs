// Synthetic-only browser QA. Real components hydrate using local React dependencies.
require('./load-ts.cjs');
const fs = require('node:fs');
const path = require('node:path');
const ts = require('typescript');
const React = require('react');
const { renderToString, renderToStaticMarkup } = require('react-dom/server');
const { currentBatch } = require('./fixtures/singles-gallery.cjs');
const { SinglesGallery } = require('../app/components/singles-gallery.tsx');
const { PageShell } = require('../app/components/page-shell.tsx');
const { ClubTabs } = require('../app/components/club-tabs.tsx');
const { NavigationLinks } = require('../app/components/navbar.tsx');
const root = path.resolve(__dirname, '..');
const output = path.resolve(__dirname, '../../../.tmp/gallery/ui-preview');
fs.mkdirSync(output, { recursive: true });
const css = fs
  .readdirSync(path.join(root, '.next/static/css'))
  .filter((n) => n.endsWith('.css'))
  .map((n) => fs.readFileSync(path.join(root, '.next/static/css', n), 'utf8'))
  .join('\n');
for (const [name, packageName] of [
  ['react', 'react'],
  ['react-dom', 'react-dom'],
]) {
  const base = path.dirname(require.resolve(packageName + '/package.json'));
  fs.copyFileSync(
    path.join(base, 'umd', name + '.production.min.js'),
    path.join(output, name + '.js'),
  );
}
const colors = ['#8d4638', '#2f504b', '#c6b991', '#3f494f', '#6f5b69'];
colors.forEach((color, i) =>
  fs.writeFileSync(
    path.join(output, `cover-${i}.svg`),
    `<svg xmlns="http://www.w3.org/2000/svg" width="400" height="400"><rect width="400" height="400" fill="${color}"/><circle cx="${100 + i * 35}" cy="180" r="110" fill="#e8dcc2"/><rect x="50" y="270" width="300" height="18" fill="#232622"/><text x="200" y="350" text-anchor="middle" font-size="20" fill="#ffffff">Synthetic cover ${i + 1}</text></svg>`,
  ),
);
const data = structuredClone(currentBatch);
for (const g of data.groups)
  g.detail.data.songs.forEach((s, i) => {
    s.cover_url =
      i === 5
        ? 'http://127.0.0.1:8766/missing-image.svg'
        : i === 4
          ? null
          : `http://127.0.0.1:8766/cover-${i % 5}.svg`;
    s.artwork_source_url = 'https://open.spotify.com/track/' + 'A'.repeat(22);
  });
// Stress text wrapping in the actual card and expanded review layout.
data.groups[0].detail.data.songs[0].title =
  'Night Transit (A Long Way Home Through the Midnight City)';
data.groups[0].detail.data.songs[0].ratings[0].review =
  'A quiet opening that builds into a bright, layered chorus. '.repeat(12) +
  '\nA second paragraph from the same first listen.';
const files = [
  'app/components/singles-gallery.tsx',
  'app/components/singles-song-gallery.tsx',
  'app/components/album-art.tsx',
  'app/components/ui.tsx',
  'app/lib/navigation.ts',
  'app/lib/singles-gallery.ts',
  'app/lib/singles-display.ts',
];
const definitions = files
  .map((file) => {
    const source = ts.transpileModule(fs.readFileSync(path.join(root, file), 'utf8'), {
      compilerOptions: {
        module: ts.ModuleKind.CommonJS,
        jsx: ts.JsxEmit.React,
        target: ts.ScriptTarget.ES2022,
        esModuleInterop: true,
      },
    }).outputText;
    return (
      JSON.stringify(file.replace(/\.tsx?$/, '')) +
      ':function(module,exports,require){\n' +
      source +
      '\n}'
    );
  })
  .join(',\n');
const boot = `const modules={${definitions}};
const cache={};
function resolve(id,from){if(!id.startsWith('.'))return id;const p=from.split('/');p.pop();for(const part of id.split('/')){if(part==='..')p.pop();else if(part!=='.')p.push(part);}return p.join('/');}
function load(id,from=''){id=resolve(id,from);if(id==='react')return window.React;if(id==='next/link')return function Link(props){return React.createElement('a',props,props.children);};if(id==='clsx')return (...parts)=>parts.filter(Boolean).join(' ');if(cache[id])return cache[id].exports;const m={exports:{}};cache[id]=m;modules[id](m,m.exports,(name)=>load(name,id));return m.exports;}
const initial=JSON.parse(document.getElementById('fixture-data').textContent);
let denied=false,requests=0;
document.getElementById('deny-next').addEventListener('click',()=>{denied=true;document.getElementById('qa-status').textContent='Next request will deny access';});
document.getElementById('toggle-theme').addEventListener('click',()=>{document.documentElement.className=document.documentElement.className==='theme-light'?'theme-dark':'theme-light';});
const actions={older:async()=>{requests++;document.getElementById('qa-status').textContent='Older requests: '+requests;await new Promise(r=>setTimeout(r,80));return denied?{state:'forbidden'}:{state:'ok',data:{groups:${JSON.stringify([data.groups[1], data.groups[2]])},nextOffset:3}};},retry:async(id)=>denied?{state:'forbidden'}:{state:'ok',data:${JSON.stringify(data.groups.map((g) => g.detail.data))}.find(g=>g.id===id)}};
const Gallery=load('app/components/singles-gallery').SinglesGallery;
ReactDOM.hydrateRoot(document.getElementById('gallery-root'),React.createElement(Gallery,{initial,actions}));
`;
fs.writeFileSync(path.join(output, 'gallery.js'), boot);
for (const [name, batch] of [
  ['index', data],
  ['interactive', { groups: data.groups.slice(0, 2), nextOffset: 2 }],
]) {
  const initial = { state: 'ok', data: batch };
  const gallery = renderToString(
    React.createElement(SinglesGallery, {
      initial,
      actions: {
        older: async () => ({ state: 'unavailable' }),
        retry: async () => ({ state: 'unavailable' }),
      },
    }),
  );
  const layout = React.createElement(
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
          title: 'Singles Night.',
          description: 'Every pick, night by night.',
          accent: 'Club / Singles Night',
        },
        React.createElement(ClubTabs, { singles: true }),
        React.createElement(
          'p',
          { className: 'small muted' },
          'Synthetic UI verification — no participant data',
        ),
        React.createElement('div', {
          id: 'gallery-root',
          dangerouslySetInnerHTML: { __html: gallery },
        }),
      ),
    ),
  );
  fs.writeFileSync(
    path.join(output, name + '.html'),
    '<!doctype html><html lang="en" class="theme-light"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Synthetic Singles Night gallery</title><style>' +
      css +
      '</style><body><div style="padding:8px 16px"><button id="toggle-theme">Toggle theme</button> <button id="deny-next">Deny next request</button> <span id="qa-status" role="status">Local interaction fixture</span></div>' +
      renderToStaticMarkup(layout) +
      '<script id="fixture-data" type="application/json">' +
      JSON.stringify(initial).replace(/</g, '\\u003c') +
      '</script><script src="/react.js"></script><script src="/react-dom.js"></script><script src="/gallery.js"></script></body></html>',
  );
}
console.log('Rendered hydrated, synthetic home-gallery and interaction previews.');
