import { useQuery } from '@tanstack/react-query';
import { apiFetch } from './api';

export type TrajectoryPoint = { week: string; x: number; y: number; r?: number };
export type TrajectoryArrow = { from: TrajectoryPoint; to: TrajectoryPoint };
export type TrajectoryData = { points: TrajectoryPoint[]; arrows: TrajectoryArrow[] };

export function useTrajectory() {
  return useQuery<TrajectoryData>({
    queryKey: ['trajectory'],
    queryFn: async () => {
      const res = await apiFetch('/dashboard/trajectory');
      if (!res.ok) throw new Error('Failed to fetch trajectory');
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
      if (!res.ok) throw new Error('Failed to fetch outliers');
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
      if (!res.ok) throw new Error('Failed to fetch recent listens');
      return (await res.json()) as RecentListensResponse;
    },
  });
}
