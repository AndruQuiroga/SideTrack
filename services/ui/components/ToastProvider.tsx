'use client';
import { createContext, useCallback, useContext, useMemo, useState } from 'react';
import {
  ToastProvider as RadixToastProvider,
  ToastViewport,
  Toast,
  ToastTitle,
  ToastDescription,
} from './ui/Toast';

type Toast = {
  id: number;
  title: string;
  description?: string;
  kind?: 'success' | 'error' | 'info';
};
type Ctx = { show: (t: Omit<Toast, 'id'>) => void; dismiss: (id: number) => void };

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
  }, []);
  const dismiss = useCallback(
    (id: number) => setList((prev) => prev.filter((x) => x.id !== id)),
    [],
  );
  const value = useMemo(() => ({ show, dismiss }), [show, dismiss]);

  return (
    <ToastCtx.Provider value={value}>
      <RadixToastProvider duration={3500}>
        {children}
        {list.map((t) => (
          <Toast
            key={t.id}
            onOpenChange={(open) => {
              if (!open) dismiss(t.id);
            }}
          >
            <ToastTitle>{t.title}</ToastTitle>
            {t.description && <ToastDescription>{t.description}</ToastDescription>}
          </Toast>
        ))}
        <ToastViewport />
      </RadixToastProvider>
    </ToastCtx.Provider>
  );
}
