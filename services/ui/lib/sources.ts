import { useQuery } from '@tanstack/react-query';
import { apiFetch } from './api';

export type Source = {
  type: 'spotify' | 'lastfm' | 'lb' | 'mb';
  status: 'connected' | 'disconnected' | 'syncing';
};

export function useSources() {
  return useQuery<Source[]>({
    queryKey: ['sources'],
    queryFn: async () => apiFetch('/api/sources'),
  });
}

