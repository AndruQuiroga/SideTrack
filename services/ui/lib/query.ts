import { QueryClient, useQuery } from '@tanstack/react-query';
import { apiFetch } from './api';
import { showToast } from './toast';

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: (failureCount, error) => failureCount < 2,
      onError: (err: unknown) => {
        const message = err instanceof Error ? err.message : 'Unknown error';
        showToast({ title: 'Request failed', description: message, kind: 'error' });
      },
    },
  },
});

export type TrajectoryPoint = { week: string; x: number; y: number; r?: number };
export type TrajectoryArrow = { from: TrajectoryPoint; to: TrajectoryPoint };
export type TrajectoryData = { points: TrajectoryPoint[]; arrows: TrajectoryArrow[] };

export function useTrajectory() {
  return useQuery<TrajectoryData>({
    queryKey: ['trajectory'],
    queryFn: async () => {
      const res = await apiFetch('/dashboard/trajectory');
      return (await res.json()) as TrajectoryData;
    },
  });
}

export type OutlierTrack = { track_id: number; title: string; artist?: string; distance: number };
export type OutliersResponse = { tracks: OutlierTrack[] };

export function useOutliers(range = '12w') {
  return useQuery<OutliersResponse>({
    queryKey: ['outliers', range],
    queryFn: async () => {
      const res = await apiFetch(`/dashboard/outliers?range=${encodeURIComponent(range)}`);
      return (await res.json()) as OutliersResponse;
    },
  });
}

export type RecentListen = {
  track_id: number;
  title: string;
  artist?: string;
  played_at: string;
};
export type RecentListensResponse = { listens: RecentListen[] };

export function useRecentListens(limit = 50) {
  return useQuery<RecentListensResponse>({
    queryKey: ['recent-listens', limit],
    queryFn: async () => {
      const res = await apiFetch(`/listens/recent?limit=${limit}`);
      return (await res.json()) as RecentListensResponse;
    },
  });
}
