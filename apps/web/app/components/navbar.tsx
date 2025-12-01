'use client';

import clsx from 'clsx';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useEffect, useState } from 'react';
import { CommandPalette } from './command-palette';
import { ThemeToggle } from './theme-toggle';
import type { Route } from 'next';

type NavLink = { href: Route | { pathname: Route; query?: Record<string, string> }; label: string };

const links: NavLink[] = [
  { href: '/discover', label: 'Discover' },
  { href: '/feed', label: 'Feed' },
  { href: { pathname: '/u/[id]' as Route, query: { id: 'demo' } }, label: 'Demo Profile' },
  { href: { pathname: '/compare' as Route, query: { userA: 'demo', userB: 'demo2' } }, label: 'Compatibility' },
  { href: '/club', label: 'Club Archive' },
  { href: '/login', label: 'Sign in' },
];

export function Navbar() {
  const pathname = usePathname();
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        setPaletteOpen(true);
      }
    }
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, []);

  return (
    <header className="sticky top-0 z-40 border-b border-slate-800/80 bg-sidetrack-bg/80 backdrop-blur-xl">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3 lg:px-6">
        <Link href="/" className="flex items-center gap-2 text-slate-100 transition hover:text-white">
          <div className="flex h-9 w-9 items-center justify-center rounded-2xl bg-gradient-to-br from-purple-500 via-fuchsia-500 to-emerald-400 text-sm font-semibold shadow-soft">
            ST
          </div>
          <div className="flex flex-col leading-tight">
            <span className="text-sm font-semibold tracking-tight">Sidetrack</span>
            <span className="text-[0.75rem] text-slate-400">Tracker · Social · Club</span>
          </div>
        </Link>

        <nav className="hidden gap-1 rounded-full border border-slate-800/80 bg-sidetrack-soft/70 p-1 text-xs font-medium text-slate-300 shadow-soft md:flex">
          {links.map((link) => {
            const targetPath =
              typeof link.href === 'string'
                ? link.href.split('?')[0]
                : link.href.pathname ?? '/';
            const normalizedTarget = targetPath.replace(/\[.*?\]/g, '');
            const active = normalizedTarget === '/' ? pathname === '/' : pathname.startsWith(normalizedTarget);
            return (
              <Link
                key={link.label}
                href={link.href}
                className={clsx(
                  'relative rounded-full px-3 py-1.5 transition-colors',
                  active
                    ? 'bg-slate-100 text-sidetrack-bg shadow-soft'
                    : 'hover:bg-slate-700/80 hover:text-slate-50'
                )}
              >
                {link.label}
              </Link>
            );
          })}
        </nav>

        <div className="flex items-center">
          <button
            onClick={() => setPaletteOpen(true)}
            className="ml-3 hidden items-center gap-2 rounded-full border border-slate-800/80 bg-slate-900/70 px-3 py-1.5 text-xs text-slate-300 shadow-soft transition hover:bg-slate-800/80 md:inline-flex"
            aria-label="Open command palette (Ctrl+K)"
          >
            <span className="inline-block h-1.5 w-1.5 rounded-full bg-emerald-400" />
            Search (Ctrl+K)
          </button>
          <ThemeToggle />
          <button
            onClick={() => setMobileOpen((o) => !o)}
            className="ml-2 inline-flex items-center justify-center rounded-xl border border-slate-800/80 bg-slate-900/70 px-2 py-1.5 text-xs text-slate-300 shadow-soft transition hover:bg-slate-800/80 md:hidden"
            aria-label="Open menu"
          >
            Menu
          </button>
        </div>
      </div>
      <CommandPalette open={paletteOpen} onClose={() => setPaletteOpen(false)} />
      {mobileOpen && (
        <div className="md:hidden">
          <div className="mx-4 mb-3 rounded-2xl border border-slate-800/80 bg-slate-950/90 p-2 shadow-2xl">
            {links.map((link) => (
              <Link
                key={typeof link.href === 'string' ? link.href : link.label}
                href={link.href}
                onClick={() => setMobileOpen(false)}
                className="block rounded-lg px-3 py-2 text-sm text-slate-200 hover:bg-slate-900"
              >
                {link.label}
              </Link>
            ))}
            <button
              onClick={() => {
                setPaletteOpen(true);
                setMobileOpen(false);
              }}
              className="mt-1 w-full rounded-lg bg-slate-800 px-3 py-2 text-left text-sm text-slate-200 hover:bg-slate-700"
            >
              Search (Ctrl+K)
            </button>
          </div>
        </div>
      )}
    </header>
  );
}
