'use client';

import { useEffect, useState } from 'react';

type Toast = { id: number; message: string; type?: 'default' | 'success' | 'error' };

let toastId = 1;

export function showToast(message: string, type: Toast['type'] = 'default') {
  if (typeof window === 'undefined') return;
  const detail: Toast = { id: toastId++, message, type };
  window.dispatchEvent(new CustomEvent('sidetrack-toast', { detail }));
}

export function ToastViewport() {
  const [toasts, setToasts] = useState<Toast[]>([]);

  useEffect(() => {
    function onToast(e: Event) {
      const evt = e as CustomEvent<Toast>;
      const t = evt.detail;
      setToasts((prev) => [...prev, t]);
      setTimeout(() => {
        setToasts((prev) => prev.filter((x) => x.id !== t.id));
      }, 3000);
    }
    window.addEventListener('sidetrack-toast', onToast as EventListener);
    return () => window.removeEventListener('sidetrack-toast', onToast as EventListener);
  }, []);

  if (!toasts.length) return null;

  return (
    <div className="pointer-events-none fixed inset-x-0 bottom-4 z-[200] flex flex-col items-center gap-2 px-4">
      {toasts.map((t) => (
        <div
          key={t.id}
          role={t.type === 'error' ? 'alert' : 'status'}
          className="toast pointer-events-auto w-full max-w-md"
        >
          {t.message}
        </div>
      ))}
    </div>
  );
}
