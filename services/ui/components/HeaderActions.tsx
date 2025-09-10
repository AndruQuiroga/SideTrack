'use client';
import { useState } from 'react';
import { motion } from 'framer-motion';
import { useToast } from './ToastProvider';
import { useTheme } from './ThemeContext';
import { RefreshCw, Sun, Moon } from 'lucide-react';

export default function HeaderActions() {
  const toast = useToast();
  const { theme, toggleTheme } = useTheme();
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
    <div className="flex items-center gap-2">
      <button
        onClick={toggleTheme}
        className="inline-flex items-center justify-center rounded-full bg-white/5 p-2 text-muted-foreground hover:text-foreground"
      >
        {theme === 'dark' ? <Sun size={14} /> : <Moon size={14} />}
        <span className="sr-only">Toggle theme</span>
      </button>
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
          <RefreshCw size={14} />
        </motion.span>
        Sync
      </button>
    </div>
  );
}
