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

export function useOutliers() {
  return useQuery<OutliersResponse>({
    queryKey: ['outliers'],
    queryFn: async () => {
      const res = await apiFetch('/dashboard/outliers');
      if (!res.ok) throw new Error('Failed to fetch outliers');
      return (await res.json()) as OutliersResponse;
    },
  });
}
