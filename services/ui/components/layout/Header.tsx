'use client';

import { useRef } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Disc3 } from 'lucide-react';

import { apiFetch } from '../../lib/api';
import { useAuth } from '../../lib/auth';
import { useSources } from '../../lib/sources';
import { showToast } from '../../lib/toast';
import Skeleton from '../Skeleton';
import HeaderActions from '../HeaderActions';
import Breadcrumbs from '../common/Breadcrumbs';
import SourceBadge from '../common/SourceBadge';

type NowPlaying = { playing: boolean; title?: string; artist?: string };

const FALLBACK_NOW_PLAYING: NowPlaying = { playing: false };

function parseNowPlaying(value: unknown): NowPlaying {
  if (!value || typeof value !== 'object') {
    return FALLBACK_NOW_PLAYING;
  }

  const record = value as Record<string, unknown>;
  const playing = record.playing === true;
  const title = typeof record.title === 'string' ? record.title : undefined;
  const artist = typeof record.artist === 'string' ? record.artist : undefined;

  return { playing, title, artist };
}

export default function Header() {
  const { data: sources } = useSources();
  const { userId } = useAuth();
  const lastError = useRef<string | null>(null);

  const { data: nowPlaying, isPending } = useQuery<NowPlaying>({
    queryKey: ['nowPlaying'],
    queryFn: async () => {
      try {
        const response = await apiFetch('/api/spotify/now');
        const json = await response.json();
        const result = parseNowPlaying(json);
        lastError.current = null;
        return result;
      } catch (error) {
        const message = error instanceof Error ? error.message : 'Unknown error';
        if (lastError.current !== message) {
          showToast({
            title: 'Unable to load now playing',
            description: message,
            kind: 'error',
          });
          lastError.current = message;
        }
        return FALLBACK_NOW_PLAYING;
      }
    },
    refetchInterval: 20000,
    refetchIntervalInBackground: true,
  });
  const now = nowPlaying ?? FALLBACK_NOW_PLAYING;
  const initials = (userId || 'U').slice(0, 2).toUpperCase();

  return (
    <header className="sticky top-0 z-20 flex items-center justify-between gap-4 border-b border-white/10 bg-white/5 px-4 py-3 backdrop-blur-md supports-[backdrop-filter]:bg-white/5 shadow-[0_10px_30px_-15px_rgba(0,0,0,0.5)]">
      <div className="flex items-center gap-3">
        <Disc3 size={18} className="text-emerald-300" />
        <Breadcrumbs />
      </div>

      <div className="hidden md:flex items-center gap-2 text-xs text-muted-foreground">
        <span className="rounded-full bg-white/5 px-2 py-1">Now playing</span>
        <div className="truncate max-w-[260px]">
          {isPending ? (
            <Skeleton className="h-4 w-40" />
          ) : now.playing && now.title ? (
            <>
              {now.title}
              {now.artist && <span className="text-foreground/70"> — {now.artist}</span>}
            </>
          ) : (
            '— nothing yet'
          )}
        </div>
      </div>

      <div className="ml-auto flex items-center gap-3">
        {sources?.map((s) => (
          <SourceBadge key={s.type} source={s} />
        ))}
        <HeaderActions />
        <div className="ml-1 hidden md:inline-flex h-8 w-8 items-center justify-center rounded-full border border-white/10 bg-white/10 text-xs font-medium">
          {initials}
        </div>
      </div>
    </header>
  );
}
