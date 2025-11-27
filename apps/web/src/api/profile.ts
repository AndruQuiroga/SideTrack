import {
  ArtistStat,
  GenreStat,
  ListeningRange,
  ListeningTimelinePoint,
  ListeningStatsParams,
  NowPlaying,
  ProfileOverview,
  RecentListen,
  SidetrackApiClient,
  TasteMetric,
  TimelineParams,
  UUID,
} from '@sidetrack/shared';

import { createWebApiClient } from './client';

export interface ProfilePageData extends ProfileOverview {
  source: 'api' | 'fallback';
  fetched_at: string;
  private_data_allowed: boolean;
}

export interface ProfileFetchOptions {
  authToken?: string;
  getAuthToken?: () => string | undefined;
  range?: ListeningRange;
  timelineBucket?: TimelineParams['bucket'];
  allowPrivateData?: boolean;
  workerSyncReady?: boolean;
}

const createClient = (options?: ProfileFetchOptions): SidetrackApiClient =>
  createWebApiClient({ authToken: options?.authToken, getAuthToken: options?.getAuthToken });

function createFallbackProfile(userId: UUID, options?: ProfileFetchOptions): ProfilePageData {
  const tasteMetrics: TasteMetric[] = [
    { id: 'energy', label: 'Energy', value: 0.74, unit: 'index', percentile: 0.82 },
    { id: 'mood', label: 'Mood', value: 0.63, unit: 'index', percentile: 0.71 },
    { id: 'tempo', label: 'Tempo', value: 118, unit: 'bpm', percentile: 0.64 },
    { id: 'acousticness', label: 'Acousticness', value: 0.32, unit: 'index', percentile: 0.28 },
  ];

  const topArtists: ArtistStat[] = [
    { id: 'placeholder-1', name: 'The Microphones', play_count: 127 },
    { id: 'placeholder-2', name: 'Little Simz', play_count: 102 },
    { id: 'placeholder-3', name: 'Bjork', play_count: 88 },
    { id: 'placeholder-4', name: 'Danny Brown', play_count: 75 },
    { id: 'placeholder-5', name: 'Ichiko Aoba', play_count: 66 },
  ];

  const topGenres: GenreStat[] = [
    { name: 'Art Pop', play_count: 182 },
    { name: 'Indie Folk', play_count: 151 },
    { name: 'Experimental Hip-Hop', play_count: 134 },
    { name: 'Ambient', play_count: 98 },
    { name: 'Jazz Fusion', play_count: 76 },
  ];

  const timeline: ListeningTimelinePoint[] = Array.from({ length: 8 }).map((_, index) => ({
    date: new Date(Date.now() - index * 7 * 24 * 60 * 60 * 1000).toISOString(),
    play_count: 40 + Math.round(Math.random() * 25),
    minutes_listened: 180 + Math.round(Math.random() * 90),
  }));

  const allowPrivate = Boolean(options?.allowPrivateData && options?.workerSyncReady);
  const nowPlaying: NowPlaying | null = allowPrivate
    ? {
        track_name: 'Placeholder Track',
        artist_name: 'Connected Artist',
        album_name: 'Live Session',
        started_at: new Date().toISOString(),
      }
    : null;

  const recentListens: RecentListen[] = allowPrivate
    ? [
        {
          track_name: 'Hymn to the Pillory',
          artist_name: 'Fire-Toolz',
          listened_at: new Date(Date.now() - 15 * 60 * 1000).toISOString(),
        },
        {
          track_name: 'a lot',
          artist_name: '21 Savage',
          listened_at: new Date(Date.now() - 45 * 60 * 1000).toISOString(),
        },
      ]
    : [];

  return {
    user_id: userId,
    display_name: 'Sidetrack Listener',
    range: options?.range ?? '30d',
    top_artists: topArtists,
    top_genres: topGenres,
    taste_metrics: tasteMetrics,
    timeline,
    now_playing: nowPlaying,
    recent_listens: recentListens,
    visibility: 'public',
    worker_sync_ready: Boolean(options?.workerSyncReady),
    source: 'fallback',
    fetched_at: new Date().toISOString(),
    private_data_allowed: allowPrivate,
  };
}

async function fetchProfileFromApi(userId: UUID, options?: ProfileFetchOptions): Promise<ProfilePageData> {
  const client = createClient(options);
  const listeningParams: ListeningStatsParams = { range: options?.range, limit: 10 };
  const timelineParams: TimelineParams = { range: options?.range, bucket: options?.timelineBucket ?? 'week' };

  const overview = await client.getUserProfileOverview(userId, listeningParams);
  const [timeline, nowPlaying, recentListens] = await Promise.all([
    client.getUserListeningTimeline(userId, timelineParams).catch(() => overview.timeline ?? []),
    options?.allowPrivateData ? client.getUserNowPlaying(userId).catch(() => null) : Promise.resolve(null),
    options?.allowPrivateData
      ? client.getUserRecentListens(userId, listeningParams).catch(() => [])
      : Promise.resolve([]),
  ]);

  return {
    ...overview,
    timeline: timeline ?? overview.timeline ?? [],
    now_playing: options?.allowPrivateData ? nowPlaying : null,
    recent_listens: options?.allowPrivateData ? recentListens : [],
    source: 'api',
    fetched_at: new Date().toISOString(),
    private_data_allowed: Boolean(options?.allowPrivateData),
    worker_sync_ready: overview.worker_sync_ready ?? options?.workerSyncReady,
  };
}

export async function fetchProfileForServer(userId: UUID, options?: ProfileFetchOptions): Promise<ProfilePageData> {
  try {
    return await fetchProfileFromApi(userId, options);
  } catch (error) {
    console.warn('Falling back to local profile data after API error', error);
    return createFallbackProfile(userId, options);
  }
}

export async function fetchProfileForClient(userId: UUID, options?: ProfileFetchOptions): Promise<ProfilePageData> {
  return fetchProfileForServer(userId, options);
}
