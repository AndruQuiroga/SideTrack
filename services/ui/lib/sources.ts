import { useQuery } from '@tanstack/react-query';
import { apiFetch } from './api';

export type Source = {
  type: 'spotify' | 'lastfm' | 'lb' | 'mb';
  status: 'connected' | 'disconnected' | 'syncing';
};

export function useSources() {
  return useQuery<Source[]>({
    queryKey: ['sources'],
    queryFn: async () => {
      const res = await apiFetch('/api/sources');
      return (await res.json()) as Source[];
    },
  });
}

export type Reason =
  | { source: 'spotify' }
  | { source: 'lastfm'; tags: string[] }
  | { source: 'lb'; artist: string }
  | { source: 'mb'; label: string; yearRange: string };

export function chipFromReason(reason: Reason): { source: Source['type']; text: string } {
  switch (reason.source) {
    case 'spotify':
      return { source: 'spotify', text: 'vibe match: energy + tempo' };
    case 'lastfm':
      return { source: 'lastfm', text: `tag overlap: ${(reason as any).tags?.join(', ')}` };
    case 'lb':
      return { source: 'lb', text: `co-listened with ${(reason as any).artist}` };
    case 'mb':
      const r = reason as any;
      return { source: 'mb', text: `same label: ${r.label}, era: ${r.yearRange}` };
    default:
      return { source: 'spotify', text: '' };
  }
}

