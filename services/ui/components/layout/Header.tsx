'use client';

import { useEffect } from 'react';
import { Search } from 'lucide-react';
import { useSources } from '../../lib/sources';
import Breadcrumbs from '../common/Breadcrumbs';
import SourceBadge from '../common/SourceBadge';

export default function Header() {
  const { data: sources } = useSources();

  const openSearch = () => {
    window.dispatchEvent(new CustomEvent('open-search'));
  };

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        openSearch();
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, []);

  return (
    <header className="sticky top-0 z-10 flex items-center justify-between gap-4 border-b bg-background/80 px-4 py-3 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <Breadcrumbs />
      <button
        onClick={openSearch}
        aria-label="Open search (⌘K)"
        className="flex flex-1 items-center gap-2 rounded-md bg-muted px-3 py-2 text-sm text-muted-foreground hover:text-foreground focus:outline-none focus:ring-2 focus:ring-emerald-500 md:max-w-sm"
      >
        <Search size={16} />
        <span className="hidden sm:inline">Search</span>
        <kbd className="ml-auto hidden text-xs sm:inline">⌘K</kbd>
      </button>
      <div className="flex items-center gap-2">
        {sources?.map((s) => (
          <SourceBadge key={s.type} source={s} />
        ))}
      </div>
    </header>
  );
}

