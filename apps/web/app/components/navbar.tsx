'use client';

import Link from 'next/link';
import { signOut, useSession } from 'next-auth/react';
import { usePathname } from 'next/navigation';
import { useEffect, useRef, useState } from 'react';
import { navigationItems, isNavigationActive } from '../lib/navigation';
import { CommandPalette } from './command-palette';
import { ThemeToggle } from './theme-toggle';

export function NavigationLinks({
  pathname,
  onNavigate,
}: {
  pathname: string;
  onNavigate?: () => void;
}) {
  return (
    <>
      {navigationItems.map((item) => (
        <Link
          key={item.href}
          href={item.href}
          className="nav-item"
          aria-current={isNavigationActive(item.href, pathname) ? 'page' : undefined}
          onClick={onNavigate}
        >
          <span className="nav-symbol" aria-hidden="true">
            {item.symbol}
          </span>
          {item.label}
        </Link>
      ))}
    </>
  );
}
export function Navbar() {
  const pathname = usePathname();
  const { data: session } = useSession();
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const menuRef = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    function keydown(e: KeyboardEvent) {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        setPaletteOpen(true);
      }
      if (e.key === 'Escape') {
        setMobileOpen(false);
        menuRef.current?.focus();
      }
    }
    window.addEventListener('keydown', keydown);
    return () => window.removeEventListener('keydown', keydown);
  }, []);
  return (
    <aside className="sidebar">
      <div className="brand-line">
        <Link href="/" className="brand" onClick={() => setMobileOpen(false)}>
          side<em>track</em>
          <small>A listening journal</small>
        </Link>
        <button
          ref={menuRef}
          type="button"
          className="button mobile-menu-button"
          aria-expanded={mobileOpen}
          aria-controls="primary-navigation"
          onClick={() => setMobileOpen(!mobileOpen)}
        >
          {mobileOpen ? 'Close menu' : 'Menu'}
        </button>
      </div>
      <nav
        id="primary-navigation"
        className={`primary-nav${mobileOpen ? ' is-open' : ''}`}
        aria-label="Primary"
      >
        <NavigationLinks pathname={pathname} onNavigate={() => setMobileOpen(false)} />
        <button type="button" className="nav-item" onClick={() => setPaletteOpen(true)}>
          <span className="nav-symbol" aria-hidden="true">
            ⌕
          </span>
          Search <span className="small muted">⌘/Ctrl K</span>
        </button>
      </nav>
      <div className="sidebar-footer">
        <strong>{session?.user?.name ?? 'Your listening and album club'}</strong>
        <ThemeToggle />
        {session ? (
          <button
            type="button"
            className="text-button"
            onClick={() => signOut({ callbackUrl: '/' })}
          >
            Sign out
          </button>
        ) : (
          <Link href="/login">Sign in with Discord</Link>
        )}
      </div>
      <CommandPalette open={paletteOpen} onClose={() => setPaletteOpen(false)} />
    </aside>
  );
}
