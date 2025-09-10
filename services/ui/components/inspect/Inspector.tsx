"use client";

import ArtistPanel from './ArtistPanel';
import TrackPanel from './TrackPanel';
import { useInspector } from '../../hooks/useInspector';

export default function Inspector() {
  const { target, close } = useInspector();
  const open = Boolean(target);

  return (
    <aside
      className={`fixed right-0 top-0 z-50 h-full w-96 bg-background shadow-lg transition-transform ${
        open ? 'translate-x-0' : 'translate-x-full'
      }`}
    >
      <div className="flex items-center justify-between border-b p-4">
        <h2 className="text-lg font-semibold">
          {target?.type === 'artist' ? 'Artist' : target?.type === 'track' ? 'Track' : ''}
        </h2>
        <button onClick={close} className="text-sm text-muted-foreground">
          Close
        </button>
      </div>
      <div className="h-[calc(100%-57px)] overflow-y-auto">
        {target?.type === 'artist' && <ArtistPanel artistId={target.id} />}
        {target?.type === 'track' && <TrackPanel trackId={target.id} />}
      </div>
    </aside>
  );
}
