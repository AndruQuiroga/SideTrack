'use client';

import Link from 'next/link';
import { useState, useSyncExternalStore } from 'react';
import type { Access } from '../lib/server-api';
import type { GalleryActions, GalleryBatch, GalleryGroup } from '../lib/singles-gallery';
import { GalleryStore } from '../lib/singles-gallery';
import { sessionTitle, singlesDate } from '../lib/singles-display';
import { AccessNotice } from './ui';
import { SinglesSongGrid } from './singles-song-gallery';

function NightGroup({
  group,
  retry,
  busy,
}: {
  group: GalleryGroup;
  retry: () => void;
  busy: boolean;
}) {
  const event = group.detail.state === 'ok' ? group.detail.data : group.summary;
  return (
    <section className="singles-gallery-night" aria-labelledby={`night-${event.id}`}>
      <header className="singles-gallery-night-heading">
        <div>
          <p className="eyebrow">{singlesDate(event.event_date)}</p>
          <h2 id={`night-${event.id}`}>{sessionTitle(event)}</h2>
        </div>
        <div className="singles-night-meta">
          {group.detail.state === 'ok' && (
            <span>
              {event.song_count} {event.song_count === 1 ? 'song' : 'songs'}
            </span>
          )}
          <Link href={`/club/singles/${event.id}`}>Night details ↗</Link>
          <a href={event.source_url} target="_blank" rel="noreferrer">
            Discord thread ↗
          </a>
        </div>
      </header>
      {group.detail.state === 'ok' ? (
        <SinglesSongGrid event={group.detail.data} />
      ) : (
        <div className="singles-night-unavailable" role="status">
          <p>
            {group.detail.state === 'not-found'
              ? 'This night is no longer available. Refresh to update the archive.'
              : 'Songs are temporarily unavailable for this night.'}
          </p>
          <button className="button button-quiet" type="button" onClick={retry} disabled={busy}>
            {busy ? 'Retrying…' : 'Retry this night'}
          </button>
        </div>
      )}
    </section>
  );
}

export function SinglesGallery({
  initial,
  actions,
}: {
  initial: Access<GalleryBatch>;
  actions: GalleryActions;
}) {
  const [store] = useState(() => new GalleryStore(initial));
  const state = useSyncExternalStore(store.subscribe, store.getSnapshot, store.getSnapshot);
  const access = initial.state === 'ok' ? state.access : initial;
  if (access.state !== 'ok')
    return (
      <AccessNotice
        state={access.state === 'not-found' ? 'unavailable' : access.state}
        what="Singles Night gallery"
        returnTo="/club/singles"
      />
    );
  if (!access.data.groups.length)
    return (
      <section className="access-state">
        <h2>No Singles Night sessions yet</h2>
        <p>The club’s song picks will appear here.</p>
      </section>
    );
  return (
    <div className="singles-gallery">
      {access.data.groups.map((group) => (
        <NightGroup
          key={group.summary.id}
          group={group}
          busy={state.pending.includes(group.summary.id)}
          retry={() => {
            void store.retry(group.summary.id, actions.retry);
          }}
        />
      ))}
      {access.data.nextOffset !== null && (
        <div className="singles-older" aria-busy={state.pending.includes('older')}>
          {state.olderFailed && (
            <p role="status">
              Older nights could not be loaded. Your current songs are still here.
            </p>
          )}
          <button
            className="button button-quiet"
            type="button"
            disabled={state.pending.includes('older')}
            onClick={() => {
              void store.older(actions.older);
            }}
          >
            {state.pending.includes('older')
              ? 'Loading older nights…'
              : state.olderFailed
                ? 'Retry older nights'
                : 'Show older nights'}
          </button>
          <span className="sr-only" role="status">
            {state.pending.includes('older') ? 'Loading older nights' : ''}
          </span>
        </div>
      )}
    </div>
  );
}
