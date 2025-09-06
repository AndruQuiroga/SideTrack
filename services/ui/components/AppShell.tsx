'use client';

import { useState, useEffect } from 'react';
import clsx from 'clsx';

import NavRail from '../components/NavRail';
import ApiStatus from '../app/api-status';
import ToastProvider from './ToastProvider';
import HeaderActions from './HeaderActions';
import MobileNav from './MobileNav';
import { NavContext } from './NavContext';
import Avatar from './ui/Avatar';

export default function AppShell({ children }: { children: React.ReactNode }) {
  const [collapsed, setCollapsed] = useState(false);

  useEffect(() => {
    const stored = localStorage.getItem('nav-collapsed');
    if (stored !== null) {
      setCollapsed(stored === 'true');
    }
  }, []);

  useEffect(() => {
    localStorage.setItem('nav-collapsed', collapsed.toString());
  }, [collapsed]);
  return (
    <ToastProvider>
      <NavContext.Provider value={{ collapsed, setCollapsed }}>
        <div className="min-h-dvh md:flex">
          <aside className={clsx('hidden md:block transition-all', collapsed ? 'w-16' : 'w-60')}>
            <NavRail />
          </aside>
          <div className="flex min-h-dvh flex-1 flex-col">
            <header className="sticky top-0 z-10 glass flex items-center justify-between px-4 py-3">
              <div className="flex items-center gap-2">
                <Avatar size={32} className="hidden md:block" />
                <span className="text-sm text-muted-foreground">Your taste dashboard</span>
              </div>
              <div className="flex items-center gap-3 text-sm text-muted-foreground">
                <HeaderActions />
                <span>
                  API: <ApiStatus />
                </span>
              </div>
            </header>
            <main className="container mx-auto w-full max-w-6xl flex-1 px-4 py-6">{children}</main>
          </div>
        </div>
        <MobileNav />
      </NavContext.Provider>
    </ToastProvider>
  );
}
