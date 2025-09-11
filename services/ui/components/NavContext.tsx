'use client';
import { createContext, useContext, useEffect, useState } from 'react';

export type NavContextValue = {
  collapsed: boolean;
  setCollapsed: (v: boolean) => void;
};

const STORAGE_KEY = 'sidebar-collapsed';

export const NavContext = createContext<NavContextValue | null>(null);

export function NavProvider({ children }: { children: React.ReactNode }) {
  const [collapsed, setCollapsed] = useState(false);

  // Hydrate from localStorage on mount
  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored !== null) {
      setCollapsed(stored === 'true');
    } else if (window.innerWidth < 768) {
      // default to collapsed on small screens
      setCollapsed(true);
    }
  }, []);

  // Persist to localStorage whenever value changes
  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, collapsed.toString());
  }, [collapsed]);

  return <NavContext.Provider value={{ collapsed, setCollapsed }}>{children}</NavContext.Provider>;
}

export function useNav() {
  const ctx = useContext(NavContext);
  if (!ctx) throw new Error('NavContext missing');
  return ctx;
}
