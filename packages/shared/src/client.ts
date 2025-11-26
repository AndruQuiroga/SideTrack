import axios, { AxiosHeaders, AxiosInstance, AxiosRequestConfig } from 'axios';

import {
  LinkedAccountCreate,
  LinkedAccountRead,
  ProviderType,
  UserCreate,
  RatingCreate,
  RatingRead,
  RatingSummary,
  UserRead,
  UUID,
  WeekCreate,
  WeekDetail,
  WeekUpdate,
  NominationRead,
  NominationCreate,
  VoteRead,
  VoteCreate,
  RatingBase,
  WeekRead,
  ProfileOverview,
  ArtistStat,
  GenreStat,
  TasteMetric,
  ListeningRange,
  ListeningTimelinePoint,
  NowPlaying,
  RecentListen,
  ListenEventCreate,
  ListenEventRead,
} from './types';
import { ApiError, toApiError } from './errors';

export interface WeekListParams {
  discussion_start?: Date | string | null;
  discussion_end?: Date | string | null;
  has_winner?: boolean;
}

export interface RatingSummaryParams {
  include_histogram?: boolean;
  bin_size?: number;
}

export interface SidetrackClientOptions {
  baseUrl: string;
  authToken?: string;
  getAuthToken?: () => string | undefined;
  axiosConfig?: AxiosRequestConfig;
}

export interface ListeningStatsParams {
  range?: ListeningRange;
  limit?: number;
}

export interface TimelineParams {
  range?: ListeningRange;
  bucket?: 'day' | 'week' | 'month';
}

export class SidetrackApiClient {
  private readonly axios: AxiosInstance;
  private readonly getAuthToken?: () => string | undefined;

  constructor(options: SidetrackClientOptions) {
    this.getAuthToken = options.getAuthToken;
    this.axios = axios.create({
      baseURL: this.normalizeBaseUrl(options.baseUrl),
      ...options.axiosConfig,
    });

    this.axios.interceptors.request.use((config) => {
      const token = this.getAuthToken?.() ?? options.authToken;
      if (token) {
        const headers = AxiosHeaders.from(config.headers);
        headers.set('Authorization', `Bearer ${token}`);
        config.headers = headers;
      }
      return config;
    });
  }

  async listWeeks(params?: WeekListParams): Promise<WeekDetail[]> {
    const query = {
      discussion_start: this.formatDateParam(params?.discussion_start),
      discussion_end: this.formatDateParam(params?.discussion_end),
      has_winner: params?.has_winner,
    };

    return this.request<WeekDetail[]>({ method: 'GET', url: '/weeks', params: query });
  }

  async getWeek(weekId: UUID): Promise<WeekDetail> {
    return this.request<WeekDetail>({ method: 'GET', url: `/weeks/${weekId}` });
  }

  async createWeek(payload: WeekCreate): Promise<WeekDetail> {
    return this.request<WeekDetail>({ method: 'POST', url: '/weeks', data: payload });
  }

  async updateWeek(weekId: UUID, payload: WeekUpdate): Promise<WeekDetail> {
    return this.request<WeekDetail>({ method: 'PATCH', url: `/weeks/${weekId}`, data: payload });
  }

  async listNominations(): Promise<NominationRead[]> {
    return this.request<NominationRead[]>({ method: 'GET', url: '/nominations' });
  }

  async getNomination(nominationId: UUID): Promise<NominationRead> {
    return this.request<NominationRead>({ method: 'GET', url: `/nominations/${nominationId}` });
  }

  async listVotes(): Promise<VoteRead[]> {
    return this.request<VoteRead[]>({ method: 'GET', url: '/votes' });
  }

  async getVote(voteId: UUID): Promise<VoteRead> {
    return this.request<VoteRead>({ method: 'GET', url: `/votes/${voteId}` });
  }

  async listListenEvents(): Promise<ListenEventRead[]> {
    return this.request<ListenEventRead[]>({ method: 'GET', url: '/listen-events' });
  }

  async getListenEvent(listenEventId: UUID): Promise<ListenEventRead> {
    return this.request<ListenEventRead>({ method: 'GET', url: `/listen-events/${listenEventId}` });
  }

  async upsertListenEvents(payload: ListenEventCreate[]): Promise<ListenEventRead[]> {
    return this.request<ListenEventRead[]>({
      method: 'POST',
      url: '/listen-events',
      data: { listens: payload },
    });
  }

  async listRatings(): Promise<RatingRead[]> {
    return this.request<RatingRead[]>({ method: 'GET', url: '/ratings' });
  }

  async getRating(ratingId: UUID): Promise<RatingRead> {
    return this.request<RatingRead>({ method: 'GET', url: `/ratings/${ratingId}` });
  }

  async upsertRating(weekId: UUID, payload: RatingCreate): Promise<RatingRead> {
    try {
      return await this.request<RatingRead>({
        method: 'POST',
        url: `/weeks/${weekId}/ratings`,
        data: payload,
      });
    } catch (error) {
      if (error instanceof ApiError && error.status === 409) {
        throw new ApiError('User has already submitted a rating for this week.', error.status, error.data, false);
      }
      throw error;
    }
  }

  async getWeekRatingSummary(weekId: UUID, params?: RatingSummaryParams): Promise<RatingSummary> {
    return this.request<RatingSummary>({
      method: 'GET',
      url: `/weeks/${weekId}/ratings/summary`,
      params: {
        include_histogram: params?.include_histogram,
        bin_size: params?.bin_size,
      },
    });
  }

  async listUsers(): Promise<UserRead[]> {
    return this.request<UserRead[]>({ method: 'GET', url: '/users' });
  }

  async getUser(userId: UUID): Promise<UserRead> {
    return this.request<UserRead>({ method: 'GET', url: `/users/${userId}` });
  }

  async createUser(payload: UserCreate): Promise<UserRead> {
    return this.request<UserRead>({ method: 'POST', url: '/users', data: payload });
  }

  async listLinkedAccounts(userId: UUID): Promise<LinkedAccountRead[]> {
    return this.request<LinkedAccountRead[]>({ method: 'GET', url: `/users/${userId}/linked-accounts` });
  }

  async linkAccount(userId: UUID, payload: LinkedAccountCreate): Promise<LinkedAccountRead> {
    return this.request<LinkedAccountRead>({
      method: 'POST',
      url: `/users/${userId}/linked-accounts`,
      data: payload,
    });
  }

  async unlinkAccount(userId: UUID, provider: ProviderType, providerUserId: string): Promise<void> {
    await this.request<void>({
      method: 'DELETE',
      url: `/users/${userId}/linked-accounts/${provider}/${providerUserId}`,
    });
  }

  async lookupUserByProvider(provider: ProviderType, providerUserId: string): Promise<UserRead> {
    return this.request<UserRead>({
      method: 'GET',
      url: `/users/lookup/by-provider/${provider}/${providerUserId}`,
    });
  }

  async getUserProfileOverview(userId: UUID, params?: ListeningStatsParams): Promise<ProfileOverview> {
    return this.request<ProfileOverview>({
      method: 'GET',
      url: `/users/${userId}/profile`,
      params: { range: params?.range },
    });
  }

  async getUserTopArtists(userId: UUID, params?: ListeningStatsParams): Promise<ArtistStat[]> {
    return this.request<ArtistStat[]>({
      method: 'GET',
      url: `/users/${userId}/listening/top-artists`,
      params: { range: params?.range, limit: params?.limit },
    });
  }

  async getUserTopGenres(userId: UUID, params?: ListeningStatsParams): Promise<GenreStat[]> {
    return this.request<GenreStat[]>({
      method: 'GET',
      url: `/users/${userId}/listening/top-genres`,
      params: { range: params?.range, limit: params?.limit },
    });
  }

  async getUserTasteMetrics(userId: UUID, params?: ListeningStatsParams): Promise<TasteMetric[]> {
    return this.request<TasteMetric[]>({
      method: 'GET',
      url: `/users/${userId}/taste`,
      params: { range: params?.range },
    });
  }

  async getUserListeningTimeline(userId: UUID, params?: TimelineParams): Promise<ListeningTimelinePoint[]> {
    return this.request<ListeningTimelinePoint[]>({
      method: 'GET',
      url: `/users/${userId}/listening/timeline`,
      params: { range: params?.range, bucket: params?.bucket },
    });
  }

  async getUserNowPlaying(userId: UUID): Promise<NowPlaying | null> {
    return this.request<NowPlaying | null>({ method: 'GET', url: `/users/${userId}/listening/now-playing` });
  }

  async getUserRecentListens(userId: UUID, params?: ListeningStatsParams): Promise<RecentListen[]> {
    return this.request<RecentListen[]>({
      method: 'GET',
      url: `/users/${userId}/listening/recent`,
      params: { range: params?.range, limit: params?.limit },
    });
  }

  async createWeekNomination(weekId: UUID, payload: NominationCreate): Promise<NominationRead> {
    try {
      return await this.request<NominationRead>({
        method: 'POST',
        url: `/weeks/${weekId}/nominations`,
        data: payload,
      });
    } catch (error) {
      if (error instanceof ApiError && error.status === 409) {
        throw new ApiError('Nomination already exists for this user and album.', error.status, error.data, false);
      }
      throw error;
    }
  }

  async createWeekVote(weekId: UUID, payload: VoteCreate): Promise<VoteRead> {
    try {
      return await this.request<VoteRead>({
        method: 'POST',
        url: `/weeks/${weekId}/votes`,
        data: payload,
      });
    } catch (error) {
      if (error instanceof ApiError && error.status === 409) {
        throw new ApiError('Vote already exists for this user and rank.', error.status, error.data, false);
      }
      throw error;
    }
  }

  private normalizeBaseUrl(baseUrl: string): string {
    return baseUrl.endsWith('/') ? baseUrl.slice(0, -1) : baseUrl;
  }

  private formatDateParam(input?: Date | string | null): string | undefined {
    if (!input) return undefined;
    return input instanceof Date ? input.toISOString() : input;
  }

  private async request<T>(config: AxiosRequestConfig): Promise<T> {
    try {
      const response = await this.axios.request<T>(config);
      return response.data;
    } catch (error) {
      throw toApiError(error);
    }
  }
}

export type {
  LinkedAccountCreate,
  LinkedAccountRead,
  RatingCreate,
  RatingRead,
  WeekDetail,
  WeekRead,
  WeekCreate,
  WeekUpdate,
  NominationRead,
  NominationCreate,
  VoteRead,
  VoteCreate,
  RatingSummary,
  UserRead,
  UserCreate,
  ProfileOverview,
  ArtistStat,
  GenreStat,
  TasteMetric,
  ListeningRange,
  ListeningTimelinePoint,
  NowPlaying,
  RecentListen,
  ListenEventCreate,
  ListenEventRead,
};
export type { ProviderType };
export type { RatingBase };
