import {
  ListeningRange,
  ListeningStatsParams,
  ProfileOverview,
  SidetrackApiClient,
  TimelineParams,
  UUID,
} from '@sidetrack/api-client';

export interface ProfilePageData extends ProfileOverview {
  fetched_at: string;
  private_data_allowed: boolean;
}

export interface ProfileFetchOptions {
  range?: ListeningRange;
  timelineBucket?: TimelineParams['bucket'];
  allowPrivateData?: boolean;
  workerSyncReady?: boolean;
}

async function fetchProfileFromApi(
  client: SidetrackApiClient,
  userId: UUID,
  options?: ProfileFetchOptions,
): Promise<ProfilePageData> {
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
/** `client` acts for the session user, who may differ from the profile's `userId`. */
export async function fetchProfileForServer(
  client: SidetrackApiClient,
  userId: UUID,
  options?: ProfileFetchOptions,
): Promise<ProfilePageData> {
  return fetchProfileFromApi(client, userId, options);
}
