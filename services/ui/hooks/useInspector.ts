"use client";

import {
  createContext,
  ReactNode,
  useCallback,
  useContext,
  useEffect,
  useState,
} from 'react';

export type InspectTarget =
  | { type: 'artist'; id: number }
  | { type: 'track'; id: number };

type InspectorContextValue = {
  target: InspectTarget | null;
  inspect: (t: InspectTarget) => void;
  close: () => void;
};

const InspectorContext = createContext<InspectorContextValue | undefined>(undefined);

export function InspectorProvider({ children }: { children: ReactNode }) {
  const [target, setTarget] = useState<InspectTarget | null>(null);

  const inspect = useCallback((t: InspectTarget) => setTarget(t), []);
  const close = useCallback(() => setTarget(null), []);

  const handleLinkClick = useCallback(
    (e: MouseEvent) => {
      const el = (e.target as HTMLElement).closest<HTMLAnchorElement>('a[data-inspect]');
      if (!el) return;
      const val = el.getAttribute('data-inspect');
      if (!val) return;
      const [type, id] = val.split(':');
      if ((type === 'artist' || type === 'track') && id) {
        e.preventDefault();
        inspect({ type: type as 'artist' | 'track', id: Number(id) });
      }
    },
    [inspect]
  );

  useEffect(() => {
    document.addEventListener('click', handleLinkClick);
    return () => document.removeEventListener('click', handleLinkClick);
  }, [handleLinkClick]);

  return (
    <InspectorContext.Provider value={{ target, inspect, close }}>
      {children}
    </InspectorContext.Provider>
  );
}

export function useInspector() {
  const ctx = useContext(InspectorContext);
  if (!ctx) throw new Error('useInspector must be used within InspectorProvider');
  return ctx;
}
