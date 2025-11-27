export type UUID = string;
export type IsoDateString = string;

export enum ProviderType {
  DISCORD = 'discord',
  SPOTIFY = 'spotify',
  LASTFM = 'lastfm',
  LISTENBRAINZ = 'listenbrainz',
}

export type ListeningRange = '7d' | '30d' | '90d' | 'all';

export interface ArtistStat {
  id?: UUID;
  name: string;
  play_count: number;
  image_url?: string | null;
}

export interface GenreStat {
  name: string;
  play_count: number;
}

export interface TasteMetric {
  id: string;
  label: string;
  value: number;
  unit?: string | null;
  percentile?: number | null;
  description?: string | null;
}

export interface ListeningTimelinePoint {
  date: IsoDateString;
  play_count: number;
  minutes_listened?: number | null;
  highlight_artist?: string | null;
}

export interface NowPlaying {
  track_name: string;
  artist_name: string;
  album_name?: string | null;
  started_at?: IsoDateString | null;
  source?: ProviderType;
  artwork_url?: string | null;
}

export interface RecentListen {
  track_name: string;
  artist_name: string;
  listened_at: IsoDateString;
  source?: ProviderType;
}

export interface ProfileOverview {
  user_id: UUID;
  display_name?: string | null;
  range?: ListeningRange;
  top_artists: ArtistStat[];
  top_genres: GenreStat[];
  taste_metrics: TasteMetric[];
  timeline: ListeningTimelinePoint[];
  now_playing?: NowPlaying | null;
  recent_listens?: RecentListen[];
  visibility: 'public' | 'private';
  worker_sync_ready?: boolean;
export enum ListenSource {
  SPOTIFY = 'spotify',
  LASTFM = 'lastfm',
  LISTENBRAINZ = 'listenbrainz',
  MANUAL = 'manual',
}

export interface UserRead {
  id: UUID;
  display_name: string;
  handle?: string | null;
  created_at: IsoDateString;
  updated_at: IsoDateString;
}

export interface UserCreate {
  display_name: string;
  handle?: string | null;
}

export interface LinkedAccountBase {
  user_id: UUID;
  provider: ProviderType;
  provider_user_id: string;
  display_name?: string | null;
  access_token?: string | null;
  refresh_token?: string | null;
  token_expires_at?: IsoDateString | null;
}

export interface LinkedAccountCreate extends LinkedAccountBase {}

export interface LinkedAccountRead extends LinkedAccountBase {
  id: UUID;
  created_at: IsoDateString;
}

export interface WeekBase {
  label: string;
  week_number?: number | null;
  discussion_at?: IsoDateString | null;
  nominations_close_at?: IsoDateString | null;
  poll_close_at?: IsoDateString | null;
  winner_album_id?: UUID | null;
  nominations_thread_id?: number | null;
  poll_thread_id?: number | null;
  winner_thread_id?: number | null;
  ratings_thread_id?: number | null;
}

export interface WeekCreate extends WeekBase {}

export interface WeekUpdate {
  label?: string | null;
  week_number?: number | null;
  discussion_at?: IsoDateString | null;
  nominations_close_at?: IsoDateString | null;
  poll_close_at?: IsoDateString | null;
  winner_album_id?: UUID | null;
  nominations_thread_id?: number | null;
  poll_thread_id?: number | null;
  winner_thread_id?: number | null;
  ratings_thread_id?: number | null;
}

export interface WeekRead extends WeekBase {
  id: UUID;
  created_at: IsoDateString;
}

export interface VoteAggregate {
  points: number;
  first_place: number;
  second_place: number;
  total_votes: number;
}

export interface RatingAggregate {
  average: number | null;
  count: number;
}

export interface RatingHistogramBin {
  value: number;
  count: number;
}

export interface RatingSummary extends RatingAggregate {
  histogram?: RatingHistogramBin[] | null;
}

export interface NominationBase {
  week_id: UUID;
  user_id: UUID;
  album_id: UUID;
  pitch?: string | null;
  pitch_track_url?: string | null;
  genre?: string | null;
  decade?: string | null;
  country?: string | null;
  submitted_at?: IsoDateString | null;
}

export interface NominationCreate extends NominationBase {}

export interface NominationRead extends NominationBase {
  id: UUID;
}

export interface NominationWithStats extends NominationRead {
  vote_summary: VoteAggregate;
  rating_summary: RatingAggregate;
}

export interface WeekAggregates {
  nomination_count: number;
  vote_count: number;
  rating_count: number;
  rating_average: number | null;
}

export interface WeekDetail extends WeekRead {
  nominations: NominationWithStats[];
  aggregates: WeekAggregates;
}

export interface VoteBase {
  week_id: UUID;
  nomination_id: UUID;
  user_id: UUID;
  rank: number;
  submitted_at?: IsoDateString | null;
}

export interface VoteCreate extends VoteBase {}

export interface VoteRead extends VoteBase {
  id: UUID;
}

export interface RatingBase {
  week_id: UUID;
  user_id: UUID;
  album_id: UUID;
  nomination_id?: UUID | null;
  value: number;
  favorite_track?: string | null;
  review?: string | null;
  created_at?: IsoDateString | null;
  metadata?: Record<string, unknown> | null;
}

export interface RatingCreate extends RatingBase {}

export interface RatingRead extends RatingBase {
  id: UUID;
}

export interface ListenEventBase {
  user_id: UUID;
  track_id: UUID;
  played_at: IsoDateString;
  source: ListenSource;
  metadata?: Record<string, unknown> | null;
  ingested_at?: IsoDateString | null;
}

export interface ListenEventCreate extends ListenEventBase {}

export interface ListenEventRead extends ListenEventBase {
  id: UUID;
}
