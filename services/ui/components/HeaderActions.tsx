'use client';
import { useState } from 'react';
import { motion } from 'framer-motion';
import { useToast } from './ToastProvider';
import dynamic from 'next/dynamic';

const Sync = dynamic(() => import('lucide-react/lib/esm/icons/sync'));

export default function HeaderActions() {
  const toast = useToast();
  const [syncing, setSyncing] = useState(false);

  const handleSync = async () => {
    setSyncing(true);
    toast.show({ title: 'Sync started', description: 'Fetching listens…', kind: 'info' });
    try {
      await fetch('/api/lastfm/sync', { method: 'POST' });
      toast.show({ title: 'Sync complete', description: 'Listens updated', kind: 'success' });
    } catch {
      toast.show({ title: 'Sync failed', description: 'Please try again later', kind: 'error' });
    } finally {
      setSyncing(false);
    }
  };

  return (
    <button
      onClick={handleSync}
      disabled={syncing}
      className="inline-flex items-center gap-2 rounded-full bg-white/5 px-3 py-1 text-xs text-muted-foreground hover:text-foreground disabled:opacity-50"
    >
      <motion.span
        animate={syncing ? { rotate: 360 } : { rotate: 0 }}
        transition={{ repeat: syncing ? Infinity : 0, duration: 1, ease: 'linear' }}
        className="inline-block"
      >
        <Sync size={14} />
      </motion.span>
      Sync
    </button>
  );
}
