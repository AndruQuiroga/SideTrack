"use client";

import { useState } from 'react';
import { usePathname } from 'next/navigation';
import { AnimatePresence, motion } from 'framer-motion';
import clsx from 'clsx';

import NavRail from '../components/NavRail';
import ApiStatus from '../app/api-status';
import ToastProvider from './ToastProvider';
import HeaderActions from './HeaderActions';
import MobileNav from './MobileNav';
import { NavContext } from './NavContext';

export default function AppShell({ children }: { children: React.ReactNode }) {
  const [collapsed, setCollapsed] = useState(false);
  const pathname = usePathname();
  return (
    <ToastProvider>
      <NavContext.Provider value={{ collapsed, setCollapsed }}>
        <div className="min-h-dvh md:flex">
          <aside
            className={clsx(
              'hidden md:block transition-all',
              collapsed ? 'w-16' : 'w-60',
            )}
          >
            <NavRail />
          </aside>
          <div className="flex min-h-dvh flex-1 flex-col">
            <header className="sticky top-0 z-10 glass flex items-center justify-between px-4 py-3">
              <div className="flex items-center gap-2">
                <div className="hidden h-8 w-8 rounded-full bg-gradient-to-br from-emerald-400 to-sky-400 md:block" />
                <span className="text-sm text-muted-foreground">Your taste dashboard</span>
              </div>
              <div className="flex items-center gap-3 text-sm text-muted-foreground">
                <HeaderActions />
                <span>
                  API: <ApiStatus />
                </span>
              </div>
            </header>
            <AnimatePresence mode="wait">
              <motion.div
                key={pathname}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                transition={{ duration: 0.2 }}
                className="flex-1"
              >
                <main className="container mx-auto w-full max-w-6xl px-4 py-6">
                  {children}
                </main>
              </motion.div>
            </AnimatePresence>
          </div>
        </div>
        <MobileNav />
      </NavContext.Provider>
    </ToastProvider>
  );
}
