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
      return {
        source: 'lastfm',
        text: `tag overlap: ${reason.tags.length > 0 ? reason.tags.join(', ') : 'none'}`,
      };
    case 'lb':
      return { source: 'lb', text: `co-listened with ${reason.artist}` };
    case 'mb':
      return { source: 'mb', text: `same label: ${reason.label}, era: ${reason.yearRange}` };
  }

  return assertNever(reason);
}

function assertNever(value: never): never {
  throw new Error(`Unhandled recommendation reason: ${JSON.stringify(value)}`);
}

