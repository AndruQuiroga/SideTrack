'use client';
import { createContext, useCallback, useContext, useMemo, useState } from 'react';

type Toast = {
  id: number;
  title: string;
  description?: string;
  kind?: 'success' | 'error' | 'info';
};
type Ctx = { toasts: Toast[]; show: (t: Omit<Toast, 'id'>) => void; dismiss: (id: number) => void };

const ToastCtx = createContext<Ctx | null>(null);

export function useToast() {
  const ctx = useContext(ToastCtx);
  if (!ctx) throw new Error('ToastProvider missing');
  return ctx;
}

export default function ToastProvider({ children }: { children: React.ReactNode }) {
  const [list, setList] = useState<Toast[]>([]);
  const show = useCallback((t: Omit<Toast, 'id'>) => {
    const id = Date.now() + Math.random();
    setList((prev) => [...prev, { id, ...t }]);
    setTimeout(() => setList((prev) => prev.filter((x) => x.id !== id)), 3500);
  }, []);
  const dismiss = useCallback(
    (id: number) => setList((prev) => prev.filter((x) => x.id !== id)),
    [],
  );
  const value = useMemo(() => ({ toasts: list, show, dismiss }), [list, show, dismiss]);

  return (
    <ToastCtx.Provider value={value}>
      {children}
      <div className="pointer-events-none fixed right-4 top-4 z-50 flex w-80 flex-col gap-2">
        {list.map((t) => (
          <div
            key={t.id}
            className="pointer-events-auto rounded-md border border-white/10 bg-black/70 p-3 shadow-soft"
          >
            <div className="text-sm font-medium">{t.title}</div>
            {t.description && <div className="text-xs text-muted-foreground">{t.description}</div>}
          </div>
        ))}
      </div>
    </ToastCtx.Provider>
  );
}
