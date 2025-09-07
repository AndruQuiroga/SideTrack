'use client';
import { createContext, useContext } from 'react';

export type NavContextValue = {
  collapsed: boolean;
  setCollapsed: (v: boolean) => void;
};

export const NavContext = createContext<NavContextValue | null>(null);

export function useNav() {
  const ctx = useContext(NavContext);
  if (!ctx) throw new Error('NavContext missing');
  return ctx;
}
