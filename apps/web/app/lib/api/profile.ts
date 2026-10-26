import {
  ListeningRange,
  ListeningStatsParams,
  ProfileOverview,
  SidetrackApiClient,
  TimelineParams,
  UUID,
} from '@sidetrack/api-client';

import { createWebApiClient } from './client';

export interface ProfilePageData extends ProfileOverview {
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

async function fetchProfileFromApi(
  userId: UUID,
  options?: ProfileFetchOptions,
): Promise<ProfilePageData> {
  const client = createClient(options);
  const listeningParams: ListeningStatsParams = { range: options?.range, limit: 10 };
  const timelineParams: TimelineParams = {
    range: options?.range,
    bucket: options?.timelineBucket ?? 'week',
  };

  const overview = await client.getUserProfileOverview(userId, listeningParams);
  const [timeline, nowPlaying, recentListens] = await Promise.all([
    client.getUserListeningTimeline(userId, timelineParams).catch(() => overview.timeline ?? []),
    options?.allowPrivateData
      ? client.getUserNowPlaying(userId).catch(() => null)
      : Promise.resolve(null),
    options?.allowPrivateData
      ? client.getUserRecentListens(userId, listeningParams).catch(() => [])
      : Promise.resolve([]),
  ]);

  return {
    ...overview,
    timeline: timeline ?? overview.timeline ?? [],
    now_playing: options?.allowPrivateData ? nowPlaying : null,
    recent_listens: options?.allowPrivateData ? recentListens : [],
    fetched_at: new Date().toISOString(),
    private_data_allowed: Boolean(options?.allowPrivateData),
    worker_sync_ready: overview.worker_sync_ready ?? options?.workerSyncReady,
  };
}

/** A user's profile. Throws ApiError (status 404 when the user doesn't exist). */
export async function fetchProfileForServer(
  userId: UUID,
  options?: ProfileFetchOptions,
): Promise<ProfilePageData> {
  return fetchProfileFromApi(userId, options);
}

export async function fetchProfileForClient(
  userId: UUID,
  options?: ProfileFetchOptions,
): Promise<ProfilePageData> {
  return fetchProfileForServer(userId, options);
}
