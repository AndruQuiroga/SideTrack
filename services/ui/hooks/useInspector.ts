"use client";

import { createContext, ReactNode, useCallback, useContext, useState } from 'react';

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
