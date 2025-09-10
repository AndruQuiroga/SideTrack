'use client';

import { useEffect } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Search, Bell, ChevronRight } from 'lucide-react';
import { useSources } from '../../lib/sources';
import SourceBadge from './SourceBadge';

export default function Header() {
  const pathname = usePathname();
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

  const segments = pathname.split('/').filter(Boolean);

  return (
    <header className="sticky top-0 z-10 glass flex items-center justify-between gap-4 px-4 py-3">
      <nav aria-label="Breadcrumb" className="hidden text-sm text-muted-foreground md:block">
        <ol className="flex items-center gap-1">
          <li>
            <Link href="/" className="hover:underline">
              Home
            </Link>
          </li>
          {segments.map((seg, idx) => (
            <li key={seg} className="flex items-center gap-1">
              <ChevronRight size={12} aria-hidden="true" />
              {idx === segments.length - 1 ? (
                <span className="capitalize" aria-current="page">
                  {seg.replace(/-/g, ' ')}
                </span>
              ) : (
                <Link
                  href={`/${segments.slice(0, idx + 1).join('/')}`}
                  className="hover:underline capitalize"
                >
                  {seg.replace(/-/g, ' ')}
                </Link>
              )}
            </li>
          ))}
        </ol>
      </nav>
      <button
        onClick={openSearch}
        aria-label="Open search (⌘K)"
        className="flex flex-1 items-center gap-2 rounded-md bg-white/5 px-3 py-2 text-sm text-muted-foreground hover:text-foreground focus:outline-none focus:ring-2 focus:ring-emerald-500 md:mx-8 md:flex-none md:w-72"
      >
        <Search size={16} />
        <span className="hidden sm:inline">Search</span>
        <kbd className="ml-auto hidden text-xs sm:inline">⌘K</kbd>
      </button>
      <div className="flex items-center gap-2">
        {sources?.map((s) => (
          <SourceBadge key={s.type} source={s} />
        ))}
        <button
          aria-label="Notifications"
          className="relative inline-flex h-8 w-8 items-center justify-center rounded-full text-muted-foreground hover:text-foreground focus:outline-none focus:ring-2 focus:ring-emerald-500"
        >
          <Bell size={16} />
        </button>
      </div>
    </header>
  );
}

