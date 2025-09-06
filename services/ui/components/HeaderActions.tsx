'use client';
import { useToast } from './ToastProvider';
import { Sync } from 'lucide-react';

export default function HeaderActions() {
  const { show } = useToast();
  return (
    <button
      onClick={() =>
        show({ title: 'Sync started', description: 'Fetching listens…', kind: 'info' })
      }
      className="inline-flex items-center gap-2 rounded-full bg-white/5 px-3 py-1 text-xs text-muted-foreground hover:text-foreground"
    >
      <Sync size={14} /> Sync
    </button>
  );
}
