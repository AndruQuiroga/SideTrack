'use client';
import { useState } from 'react';
import { motion } from 'framer-motion';
import * as Tooltip from '@radix-ui/react-tooltip';
import { useToast } from './ToastProvider';
import { useTheme } from './ThemeContext';
import { RefreshCw, Sun, Moon } from 'lucide-react';
import { syncLastfmScrobbles } from '../lib/lastfmSync';

export default function HeaderActions() {
  const toast = useToast();
  const { theme, toggleTheme } = useTheme();
  const [syncing, setSyncing] = useState(false);

  const handleSync = async () => {
    setSyncing(true);
    toast.show({ title: 'Sync started', description: 'Ingesting Last.fm scrobbles…', kind: 'info' });
    try {
      const { ingested } = await syncLastfmScrobbles();
      const description =
        typeof ingested === 'number'
          ? `Ingested ${ingested} ${ingested === 1 ? 'listen' : 'listens'}`
          : 'Scrobbles synced';
      toast.show({ title: 'Sync complete', description, kind: 'success' });
    } catch {
      toast.show({ title: 'Sync failed', description: 'Please try again later', kind: 'error' });
    } finally {
      setSyncing(false);
    }
  };

  return (
    <div className="flex items-center gap-2">
      <Tooltip.Root>
        <Tooltip.Trigger asChild>
          <button
            onClick={toggleTheme}
            className="inline-flex items-center justify-center rounded-full bg-white/5 p-2 text-muted-foreground hover:text-foreground"
            aria-label="Toggle theme"
          >
            {theme === 'dark' ? <Sun size={14} /> : <Moon size={14} />}
          </button>
        </Tooltip.Trigger>
        <Tooltip.Portal>
          <Tooltip.Content
            side="bottom"
            sideOffset={6}
            className="rounded-md bg-foreground px-2 py-1 text-xs text-background"
          >
            Toggle theme
          </Tooltip.Content>
        </Tooltip.Portal>
      </Tooltip.Root>

      <Tooltip.Root>
        <Tooltip.Trigger asChild>
          <button
            onClick={handleSync}
            disabled={syncing}
            className="inline-flex items-center gap-2 rounded-full bg-white/5 px-3 py-1 text-xs text-muted-foreground hover:text-foreground disabled:opacity-50"
            aria-label="Sync listens"
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
        </Tooltip.Trigger>
        <Tooltip.Portal>
          <Tooltip.Content
            side="bottom"
            sideOffset={6}
            className="rounded-md bg-foreground px-2 py-1 text-xs text-background"
          >
            Sync listens
          </Tooltip.Content>
        </Tooltip.Portal>
      </Tooltip.Root>
    </div>
  );
}
