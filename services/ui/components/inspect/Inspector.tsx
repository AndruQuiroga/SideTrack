"use client";

import { useEffect, useRef } from 'react';
import ArtistPanel from './ArtistPanel';
import TrackPanel from './TrackPanel';
import { useInspector } from '../../hooks/useInspector';

export default function Inspector() {
  const { target, close } = useInspector();
  const open = Boolean(target);
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        close();
      }

      if (e.key === 'Tab' && panelRef.current) {
        const focusable = panelRef.current.querySelectorAll<HTMLElement>(
          'a, button, textarea, input, select, [tabindex]:not([tabindex="-1"])'
        );
        if (!focusable.length) return;
        const first = focusable[0];
        const last = focusable[focusable.length - 1];

        if (e.shiftKey) {
          if (document.activeElement === first) {
            e.preventDefault();
            last.focus();
          }
        } else if (document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
    };

    document.addEventListener('keydown', handleKeyDown);

    const first = panelRef.current?.querySelector<HTMLElement>(
      'a, button, textarea, input, select, [tabindex]:not([tabindex="-1"])'
    );
    first?.focus();

    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [open, close]);

  return (
    <aside
      ref={panelRef}
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
