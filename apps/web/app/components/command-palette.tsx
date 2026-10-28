'use client';
import { useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { useSession } from 'next-auth/react';
import type { SearchResult } from '../lib/api/discover';
import { searchSidetrack } from '../lib/browser-api';

export function SearchResults({ results }: { results: SearchResult }) {
  const count = results.users.length + results.albums.length + results.tracks.length;
  if (!count)
    return (
      <p role="status" className="muted">
        No matching records.
      </p>
    );
  return (
    <>
      {results.users.length > 0 && (
        <section>
          <h3>People</h3>
          {results.users.map((user) => (
            <div className="search-result" key={user.id}>
              <p>{user.display_name}</p>
              {user.handle && <span className="small muted">@{user.handle}</span>}
              <p className="small muted">Profile pages are unavailable.</p>
            </div>
          ))}
        </section>
      )}
      {results.albums.length > 0 && (
        <section>
          <h3>Albums</h3>
          {results.albums.map((album) => (
            <div className="search-result" key={album.id}>
              <p>{album.title}</p>
              <span className="small muted">
                {album.artist_name}
                {album.release_year ? ` · ${album.release_year}` : ''}
              </span>
            </div>
          ))}
        </section>
      )}
      {results.tracks.length > 0 && (
        <section>
          <h3>Tracks</h3>
          {results.tracks.map((track) => (
            <div className="search-result" key={track.id}>
              <p>{track.title}</p>
              <span className="small muted">
                {track.artist_name}
                {track.album_title ? ` · ${track.album_title}` : ''}
              </span>
            </div>
          ))}
        </section>
      )}
    </>
  );
}
export function CommandPalette({ open, onClose }: { open: boolean; onClose: () => void }) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const { data: session, status } = useSession();
  const [query, setQuery] = useState('');
  const [state, setState] = useState<'idle' | 'loading' | 'error' | 'ok'>('idle');
  const [results, setResults] = useState<SearchResult | null>(null);
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    const dialog = dialogRef.current;
    if (!open || !dialog) return;
    const invoker = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    setQuery('');
    setResults(null);
    setState('idle');
    dialog.showModal();
    inputRef.current?.focus();
    return () => {
      dialog.close();
      invoker?.focus();
    };
  }, [open]);
  useEffect(() => {
    const controller = new AbortController();
    if (!open || !session?.user?.id || query.trim().length < 2) {
      setResults(null);
      setState('idle');
      return;
    }
    setState('loading');
    setResults(null);
    const timer = setTimeout(() => {
      searchSidetrack(query.trim(), controller.signal)
        .then((data) => {
          if (!controller.signal.aborted) {
            setResults(data);
            setState('ok');
          }
        })
        .catch(() => {
          if (!controller.signal.aborted) setState('error');
        });
    }, 200);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [query, open, session?.user?.id, retry]);
  return (
    <dialog
      className="search-dialog"
      ref={dialogRef}
      aria-labelledby="search-heading"
      onKeyDown={(event) => {
        if (event.key === 'Escape') {
          event.preventDefault();
          event.stopPropagation();
          onClose();
        }
      }}
      onCancel={(event) => {
        event.preventDefault();
        onClose();
      }}
      onClick={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <div className="section-heading">
        <h2 id="search-heading">Search SideTrack</h2>
        <button type="button" className="button" onClick={onClose}>
          Close
        </button>
      </div>
      {status === 'loading' ? (
        <p role="status">Checking your session…</p>
      ) : !session?.user?.id ? (
        <p>
          Search is available after{' '}
          <Link href="/login" onClick={onClose}>
            signing in with Discord
          </Link>
          .
        </p>
      ) : (
        <>
          <label className="field">
            Albums, artists and people
            <input
              ref={inputRef}
              type="search"
              value={query}
              maxLength={160}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search your catalog"
            />
          </label>
          <div aria-live="polite">
            {state === 'idle' && <p className="muted">Enter at least two characters.</p>}
            {state === 'loading' && <p>Searching…</p>}
            {state === 'error' && (
              <>
                <p className="error-text">Search unavailable. Please try again.</p>
                <button
                  type="button"
                  className="button"
                  onClick={() => setRetry((value) => value + 1)}
                >
                  Retry search
                </button>
              </>
            )}
            {results && <SearchResults results={results} />}
          </div>
        </>
      )}
    </dialog>
  );
}
