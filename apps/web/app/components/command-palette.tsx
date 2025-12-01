'use client';

import { useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { webSearch, SearchResult } from '../../src/api/discover';
import { showToast } from './toast';

interface CommandPaletteProps {
  open: boolean;
  onClose: () => void;
}

export function CommandPalette({ open, onClose }: CommandPaletteProps) {
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<SearchResult | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (open) {
      setTimeout(() => inputRef.current?.focus(), 0);
    } else {
      setQuery('');
      setResults(null);
      setLoading(false);
    }
  }, [open]);

  useEffect(() => {
    const ctrl = new AbortController();
    async function run() {
      if (!query || query.trim().length < 2) {
        setResults(null);
        return;
      }
      setLoading(true);
      try {
        const r = await webSearch(query.trim());
        setResults(r);
      } catch (e) {
        showToast('Search failed. Please try again.', 'error');
      } finally {
        setLoading(false);
      }
    }
    run();
    return () => ctrl.abort();
  }, [query]);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') onClose();
    }
    if (open) window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-[100] flex items-start justify-center bg-black/40 p-4 backdrop-blur-sm">
      <div className="w-full max-w-2xl overflow-hidden rounded-2xl border border-slate-800 bg-slate-950 shadow-2xl">
        <div className="flex items-center gap-2 border-b border-slate-800 bg-slate-900/60 px-3 py-2">
          <span className="inline-block h-1.5 w-1.5 rounded-full bg-emerald-400" />
          <input
            ref={inputRef}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search users, albums, tracks..."
            className="w-full bg-transparent py-2 text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none"
          />
          <button onClick={onClose} className="rounded-md px-2 py-1 text-xs text-slate-300 hover:bg-slate-800">
            Esc
          </button>
        </div>
        <div className="max-h-[60vh] overflow-auto">
          {!results && !loading && (
            <DefaultShortcuts onClose={onClose} />
          )}
          {loading && (
            <div className="p-4 text-sm text-slate-400">Searching…</div>
          )}
          {results && (
            <div className="divide-y divide-slate-800">
              <Section title="Users" emptyText="No users found" items={results.users} render={(u) => (
                <Link href={{ pathname: '/u/[id]', query: { id: u.id } }} onClick={onClose} className="block px-4 py-3 hover:bg-slate-900">
                  <div className="text-sm text-white">{u.display_name}</div>
                  {u.handle && <div className="text-xs text-slate-400">@{u.handle}</div>}
                </Link>
              )} />
              <Section title="Albums" emptyText="No albums found" items={results.albums} render={(a) => (
                <div className="px-4 py-3 text-sm text-slate-200">
                  <div className="text-white">{a.title}</div>
                  <div className="text-xs text-slate-400">{a.artist_name}{a.release_year ? ` • ${a.release_year}` : ''}</div>
                </div>
              )} />
              <Section title="Tracks" emptyText="No tracks found" items={results.tracks} render={(t) => (
                <div className="px-4 py-3 text-sm text-slate-200">
                  <div className="text-white">{t.title}</div>
                  <div className="text-xs text-slate-400">{t.artist_name}{t.album_title ? ` — ${t.album_title}` : ''}</div>
                </div>
              )} />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function Section<T>({ title, items, render, emptyText }: { title: string; items: T[]; render: (item: T) => React.ReactNode; emptyText: string }) {
  return (
    <div>
      <div className="bg-slate-900/50 px-4 py-2 text-xs font-semibold uppercase tracking-wide text-slate-400">{title}</div>
      {items.length === 0 ? (
        <div className="px-4 py-3 text-sm text-slate-500">{emptyText}</div>
      ) : (
        <div>{items.map((i, idx) => (
          <div key={idx}>{render(i)}</div>
        ))}</div>
      )}
    </div>
  );
}

function DefaultShortcuts({ onClose }: { onClose: () => void }) {
  const items = [
    { label: 'Go to Discover', href: '/discover' as const },
    { label: 'Open Feed', href: '/feed' as const },
    { label: 'View Club Archive', href: '/club' as const },
    { label: 'Open Settings', href: '/settings' as const },
    { label: 'Compare tastes', href: '/compare?userA=demo&userB=demo2' },
    { label: 'Friend blend', href: '/blend' as const },
  ];
  return (
    <div className="p-2">
      {items.map((item) => (
        <a
          key={item.href}
          href={item.href}
          onClick={(e) => {
            e.preventDefault();
            window.location.href = item.href;
            onClose();
          }}
          className="block rounded-md px-3 py-2 text-sm text-slate-200 hover:bg-slate-900"
        >
          {item.label}
        </a>
      ))}
    </div>
  );
}
