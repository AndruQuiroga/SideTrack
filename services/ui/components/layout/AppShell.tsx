'use client';

import { useState, useEffect } from 'react';
import Header from './Header';
import Sidebar from './Sidebar';

export default function AppShell({ children }: { children: React.ReactNode }) {
  const [collapsed, setCollapsed] = useState(false);

  useEffect(() => {
    const stored = localStorage.getItem('sidebar-collapsed');
    if (stored !== null) {
      setCollapsed(stored === 'true');
    } else if (window.innerWidth < 768) {
      setCollapsed(true);
    }
  }, []);

  useEffect(() => {
    localStorage.setItem('sidebar-collapsed', collapsed.toString());
  }, [collapsed]);

  return (
    <div className="min-h-dvh overflow-x-hidden flex bg-gradient-to-b from-background to-background/95 bg-grid">
      <Sidebar collapsed={collapsed} setCollapsed={setCollapsed} />
      <div className="flex min-h-dvh flex-1 flex-col">
        <Header />
        <main className="w-full flex-1 overflow-x-hidden px-4 py-6 md:px-6">
          <div className="mx-auto max-w-6xl">{children}</div>
        </main>
      </div>
    </div>
  );
}
