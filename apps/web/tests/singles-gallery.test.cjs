require('./load-ts.cjs');
const assert = require('node:assert/strict');
const { test } = require('node:test');
const fs = require('node:fs');
const path = require('node:path');
const React = require('react');
const { renderToStaticMarkup } = require('react-dom/server');
const { SinglesGallery } = require('../app/components/singles-gallery.tsx');
const { SinglesSongCard } = require('../app/components/singles-song-gallery.tsx');
const { currentBatch, night } = require('./fixtures/singles-gallery.cjs');
const actions = {
  older: async () => ({ state: 'unavailable' }),
  retry: async () => ({ state: 'unavailable' }),
};
const render = (initial) =>
  renderToStaticMarkup(React.createElement(SinglesGallery, { initial, actions }));

test('home gallery renders44 cards across seven nights immediately in source order', () => {
  const html = render({ state: 'ok', data: currentBatch });
  assert.equal((html.match(/class="singles-pick"/g) || []).length, 44);
  assert.equal((html.match(/class="singles-gallery-night"/g) || []).length, 7);
  assert.ok(html.indexOf('Singles Night 7') < html.indexOf('Singles Night 6'));
  assert.ok(html.indexOf('Night Transit') < html.indexOf('Soft Landing'));
  assert.match(html, /Night details/);
  assert.doesNotMatch(html, /Show older nights/);
  const route = fs.readFileSync(path.join(__dirname, '../app/club/singles/page.tsx'), 'utf8');
  assert.match(route, /fetchSinglesGallery/);
  assert.match(route, /<SinglesGallery/);
  assert.doesNotMatch(route, /<SinglesArchive/);
});

test('card has native inline impressions, precise source scores and no empty final column', () => {
  const song = night(7).songs[0];
  song.submissions = [];
  song.ratings[0].value = 3.75;
  song.ratings[0].review = 'A long review.\nAnother thought.';
  song.rating_summary.first = { count: 1, average: 3.75 };
  const html = renderToStaticMarkup(
    React.createElement(SinglesSongCard, { song, sessionId: 'night-7' }),
  );
  assert.match(html, /<details[^>]*class="singles-impressions"/);
  assert.match(html, /<summary>Listener impressions<\/summary>/);
  assert.match(html, /3.8/);
  assert.match(html, /3.75 \/ 5/);
  assert.match(html, /Submitter unavailable/);
  assert.match(html, /Artwork unavailable/);
  assert.match(html, /Another thought/);
  assert.doesNotMatch(html, /Final ratings/);
  song.ratings.push({ ...song.ratings[0], id: 'final', phase: 'final', value: 5 });
  assert.match(
    renderToStaticMarkup(React.createElement(SinglesSongCard, { song, sessionId: 'night-7' })),
    /Final ratings/,
  );
  song.rating_summary.first = { count: 0, average: null };
  assert.match(
    renderToStaticMarkup(React.createElement(SinglesSongCard, { song, sessionId: 'night-7' })),
    /Not rated yet/,
  );
});

test('empty, partial, missing, unavailable and access states stay distinct', () => {
  for (const state of ['signed-out', 'forbidden', 'unavailable'])
    assert.match(
      render({ state }),
      state === 'signed-out'
        ? /Sign in/
        : state === 'forbidden'
          ? /for club members/
          : /unavailable/i,
    );
  assert.match(
    render({ state: 'ok', data: { groups: [], nextOffset: null } }),
    /No Singles Night sessions yet/,
  );
  const data = structuredClone(currentBatch);
  data.groups[0].detail = { state: 'unavailable' };
  const html = render({ state: 'ok', data });
  assert.match(html, /Retry this night/);
  assert.match(html, /Singles Night 6/);
  assert.equal((html.match(/class="singles-pick"/g) || []).length, 37);
});
