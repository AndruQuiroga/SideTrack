'use client';
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import {
  ToastProvider as RadixToastProvider,
  ToastViewport,
  Toast,
  ToastTitle,
  ToastDescription,
} from './ui/Toast';
import { setToastListener, type Toast as ToastType } from '../lib/toast';
import { cn } from '../lib/utils';

type Toast = ToastType & { id: number };
type Ctx = { show: (t: Omit<Toast, 'id'>) => void; dismiss: (id: number) => void };

const VARIANT_STYLES: Record<NonNullable<ToastType['kind']>, { root: string; title: string; description: string }> = {
  success: {
    root: 'border-emerald-500/50 bg-emerald-500/10 text-emerald-100',
    title: 'text-emerald-100',
    description: 'text-emerald-100/80',
  },
  error: {
    root: 'border-red-500/60 bg-red-500/10 text-red-100',
    title: 'text-red-100',
    description: 'text-red-100/80',
  },
  info: {
    root: 'border-sky-500/60 bg-sky-500/10 text-sky-100',
    title: 'text-sky-100',
    description: 'text-sky-100/80',
  },
};

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

  useEffect(() => {
    setToastListener(show);
  }, [show]);

  return (
    <ToastCtx.Provider value={value}>
      <RadixToastProvider duration={3500}>
        {children}
        {list.map((t) => {
          const variant = t.kind ? VARIANT_STYLES[t.kind] : undefined;
          return (
            <Toast
              key={t.id}
              className={cn(variant?.root)}
              onOpenChange={(open) => {
                if (!open) dismiss(t.id);
              }}
            >
              <ToastTitle className={cn(variant?.title)}>{t.title}</ToastTitle>
              {t.description && (
                <ToastDescription className={cn(variant?.description)}>
                  {t.description}
                </ToastDescription>
              )}
            </Toast>
          );
        })}
        <ToastViewport />
      </RadixToastProvider>
    </ToastCtx.Provider>
  );
}
