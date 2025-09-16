import { QueryClient, useQuery } from '@tanstack/react-query';
import { ApiError, apiFetch } from './api';

let sessionRedirected = false;

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: (failureCount) => failureCount < 2,
      onError: (err: unknown) => {
        if (err instanceof ApiError && err.status === 401) {
          if (!sessionRedirected && typeof window !== 'undefined') {
            sessionRedirected = true;
            const next = encodeURIComponent(window.location.pathname + window.location.search);
            window.location.assign(`/login?next=${next}`);
          }
        }
      },
    },
  },
});

export type TrajectoryPoint = { week: string; x: number; y: number; r?: number };
export type TrajectoryArrow = { from: TrajectoryPoint; to: TrajectoryPoint };
export type TrajectoryData = { points: TrajectoryPoint[]; arrows: TrajectoryArrow[] };

export type DashboardKpi = {
  id: string;
  title: string;
  value?: string | number | null;
  delta?: { value: number; suffix?: string };
  series?: number[];
  error?: string;
};

export type DashboardInsight = {
  id: string;
  summary?: string;
  error?: string;
};

export type DashboardData = {
  lastArtist: string;
  kpis: DashboardKpi[];
  insights: DashboardInsight[];
};

export function useDashboard() {
  return useQuery<DashboardData>({
    queryKey: ['dashboard-summary'],
    queryFn: async () => {
      const res = await apiFetch('/api/dashboard/summary');
      const json = await res.json();
      return {
        lastArtist: json.last_artist ?? '',
        kpis: json.kpis ?? [],
        insights: json.insights ?? [],
      } as DashboardData;
    },
  });
}

export function useTrajectory() {
  return useQuery<TrajectoryData>({
    queryKey: ['trajectory'],
    queryFn: async () => {
      const res = await apiFetch('/api/dashboard/trajectory');
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
      const res = await apiFetch(`/api/dashboard/outliers?range=${encodeURIComponent(range)}`);
      return (await res.json()) as OutliersResponse;
    },
  });
}

export type TopTag = { name: string; count: number };
export type TopTagsResponse = { tags: TopTag[] };

export function useTopTags(limit = 12, days = 90) {
  return useQuery<TopTagsResponse>({
    queryKey: ['top-tags', limit, days],
    queryFn: async () => {
      const res = await apiFetch(`/api/dashboard/tags?limit=${limit}&days=${days}`);
      return (await res.json()) as TopTagsResponse;
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
      const res = await apiFetch(`/api/listens/recent?limit=${limit}`);
      return (await res.json()) as RecentListensResponse;
    },
  });
}
