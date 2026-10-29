require('./load-ts.cjs');
const assert = require('node:assert/strict');
const { test } = require('node:test');
const React = require('react');
const { renderToStaticMarkup } = require('react-dom/server');
const { AlbumArt } = require('../app/components/album-art.tsx');

test('a failed image becomes unavailable and a different cover can load', () => {
  const original = React.useState;
  let failed = null;
  React.useState = () => [
    failed,
    (value) => {
      failed = value;
    },
  ];
  try {
    const props = { url: 'https://i.scdn.co/image/synthetic', title: 'Synthetic Song' };
    const first = AlbumArt(props);
    assert.equal(first.props.children.type, 'img');
    first.props.children.props.onError();
    assert.match(renderToStaticMarkup(AlbumArt(props)), /Artwork unavailable/);
    const changed = AlbumArt({ ...props, url: 'https://i.scdn.co/image/another' });
    assert.equal(changed.props.children.type, 'img');
  } finally {
    React.useState = original;
  }
});
