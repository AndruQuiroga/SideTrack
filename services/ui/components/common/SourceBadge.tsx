'use client';

import { useRouter } from 'next/navigation';
import * as Tooltip from '@radix-ui/react-tooltip';
import { Radio, Brain, Globe } from 'lucide-react';
import SpotifyIcon from './SpotifyIcon';
import clsx from 'clsx';
import type { Source } from '../../lib/sources';

const icons: Record<Source['type'], React.ElementType> = {
  spotify: SpotifyIcon,
  lastfm: Radio,
  lb: Brain,
  mb: Globe,
};

const titles: Record<Source['type'], string> = {
  spotify: 'Spotify',
  lastfm: 'Last.fm',
  lb: 'ListenBrainz',
  mb: 'MusicBrainz',
};

const statusColors: Record<Source['status'], string> = {
  connected: 'text-emerald-400',
  disconnected: 'text-rose-400',
  syncing: 'text-amber-400 motion-safe:animate-pulse',
};

export default function SourceBadge({ source }: { source: Source }) {
  const router = useRouter();
  const Icon = icons[source.type];
  const color = statusColors[source.status];

  const handleClick = () => {
    router.push(`/settings#${source.type}`);
  };

  return (
    <Tooltip.Root>
      <Tooltip.Trigger asChild>
        <button
          onClick={handleClick}
          aria-label={`${titles[source.type]} ${source.status}`}
          className={clsx(
            'relative inline-flex h-8 w-8 items-center justify-center rounded-full',
            color,
            'hover:bg-white/5 focus:outline-none focus:ring-2 focus:ring-emerald-500'
          )}
        >
          <Icon size={16} />
        </button>
      </Tooltip.Trigger>
      <Tooltip.Portal>
        <Tooltip.Content
          side="bottom"
          sideOffset={4}
          className="rounded-md bg-foreground px-2 py-1 text-xs text-background"
        >
          {titles[source.type]}
        </Tooltip.Content>
      </Tooltip.Portal>
    </Tooltip.Root>
  );
}

