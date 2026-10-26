import { AsyncLocalStorage } from 'node:async_hooks';

import {
  ApiError,
  NominationCreate,
  NominationRead,
  ProviderType,
  RatingCreate,
  RatingRead,
  SidetrackApiClient,
  UUID,
  UserRead,
  VoteCreate,
  VoteRead,
  WeekCreate,
  WeekDetail,
  WeekUpdate,
  AlbumRead,
  ClubRole,
} from '@sidetrack/api-client';

import type { BotConfig } from './config';
import type { Logger } from './logger';

/** The Discord user the current interaction or message acts for (ADR 0009). */
const actingDiscordUser = new AsyncLocalStorage<string>();

/**
 * Run `fn` so that every API call it makes acts for the Discord user, sending
 * `X-Sidetrack-Act-As: discord:<id>`. Outside such a call the bot acts as itself.
 */
export function runAsDiscordUser<T>(discordUserId: string, fn: () => Promise<T>): Promise<T> {
  return actingDiscordUser.run(discordUserId, fn);
}

const MEMBERSHIP_REFRESH_MS = 10 * 60 * 1000;

export interface ClubPhasePayload {
  week: WeekCreate;
  update?: WeekUpdate;
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export class ClubSyncService {
  private readonly starterMessageIds: Map<string, string> = new Map();
  private readonly recordedMembers: Map<string, { role: ClubRole; at: number }> = new Map();

  constructor(
    /** The bot acting as itself; `client` adds the current Discord user. */
    private readonly serviceClient: SidetrackApiClient,
    private readonly config: BotConfig,
    private readonly logger: Logger,
    private readonly nominationsThreadMap: Map<string, WeekDetail> = new Map(),
    private readonly ratingsThreadMap: Map<string, WeekDetail> = new Map(),
  ) {}

  /** The API client for the current context: acting for the Discord user when there is one. */
  private get client(): SidetrackApiClient {
    const discordUserId = actingDiscordUser.getStore();
    return discordUserId
      ? this.serviceClient.withActor({ discord: discordUserId })
      : this.serviceClient;
  }

  /** Get the API client for direct access, acting for the current Discord user if any. */
  getClient(): SidetrackApiClient {
    return this.client;
  }

  /**
   * Make sure the Discord user has a Sidetrack account and record their club role.
   * The bot is the only writer of membership; this runs as the bot itself.
   */
  async recordMember(discordUserId: string, displayName: string, admin: boolean): Promise<void> {
    const role: ClubRole = admin ? 'admin' : 'member';
    const known = this.recordedMembers.get(discordUserId);
    if (known && known.role === role && Date.now() - known.at < MEMBERSHIP_REFRESH_MS) return;
    await this.ensureDiscordUser(discordUserId, displayName);
    await this.withRetry('record-member', () =>
      this.serviceClient.putClubMember(discordUserId, role),
    );
    this.recordedMembers.set(discordUserId, { role, at: Date.now() });
  }

  /** Record that a member left the guild; their club history is kept. */
  async recordDeparture(discordUserId: string): Promise<void> {
    this.recordedMembers.delete(discordUserId);
    try {
      await this.serviceClient.removeClubMember(discordUserId);
    } catch (error) {
      if (!(error instanceof ApiError) || error.status !== 404) throw error;
    }
  }

  async bootstrap(): Promise<WeekDetail[]> {
    this.logger.info('Bootstrapping bot sync service with shared API client.', {
      apiBaseUrl: this.config.api.baseUrl,
    });
    const weeks = await this.serviceClient.listWeeks({ has_winner: false });
    weeks.forEach((week) => {
      if (week.nominations_thread_id) {
        this.nominationsThreadMap.set(String(week.nominations_thread_id), week);
      }
      if (week.ratings_thread_id) {
        this.ratingsThreadMap.set(String(week.ratings_thread_id), week);
      }
    });
    return weeks;
  }

  async ensureAlbumFromForm(details: {
    title: string;
    artist_name: string;
    release_year?: number | null;
  }): Promise<AlbumRead> {
    const existing = await this.client.searchAlbums({
      title: details.title,
      artist_name: details.artist_name,
      release_year: details.release_year ?? undefined,
      limit: 1,
    });
    if (existing.length > 0) {
      return existing[0];
    }

    this.logger.info('Creating album from nomination form.', {
      title: details.title,
      artist: details.artist_name,
      year: details.release_year,
    });
    return this.client.createAlbum(details);
  }

  async ensureDiscordUser(discordUserId: string, displayName: string): Promise<UserRead> {
    try {
      // Provisioning runs as the bot itself: the user may not exist yet.
      return await this.serviceClient.lookupUserByProvider(ProviderType.DISCORD, discordUserId);
    } catch (error) {
      if (!(error instanceof ApiError) || error.status !== 404) {
        throw error;
      }
      this.logger.info('Creating Sidetrack user for Discord member.', { discordUserId });

      const user = await this.withRetry('create-user', () =>
        this.serviceClient.createUser({ display_name: displayName }),
      );

      await this.withRetry('link-discord-account', async () => {
        try {
          await this.serviceClient.linkAccount(user.id, {
            provider: ProviderType.DISCORD,
            provider_user_id: discordUserId,
            display_name: displayName,
            user_id: user.id,
          });
        } catch (linkError) {
          if (linkError instanceof ApiError && linkError.status === 409) {
            this.logger.warn('Discord account already linked; proceeding.', { discordUserId });
            return;
          }
          throw linkError;
        }
      });

      return user;
    }
  }

  async ensureWeek(payload: ClubPhasePayload): Promise<WeekDetail> {
    return this.withRetry('ensure-week', async () => {
      try {
        const created = await this.client.createWeek(payload.week);
        if (payload.update) {
          return this.client.updateWeek(created.id, payload.update);
        }
        return created;
      } catch (error) {
        if (error instanceof ApiError && error.status === 409) {
          this.logger.warn('Week already exists; attempting to reuse existing record.', {
            label: payload.week.label,
            week_number: payload.week.week_number,
          });
          const existingWeeks = await this.client.listWeeks();
          const match = existingWeeks.find(
            (week) =>
              week.week_number === payload.week.week_number ||
              week.label.toLowerCase() === payload.week.label.toLowerCase(),
          );
          if (match) {
            return payload.update ? this.client.updateWeek(match.id, payload.update) : match;
          }
        }
        throw error;
      }
    });
  }

  async recordNomination(
    weekId: UUID,
    nomination: NominationCreate,
    loggerMeta?: Record<string, unknown>,
  ): Promise<NominationRead> {
    return this.withRetry('record-nomination', async () => {
      try {
        return await this.client.createWeekNomination(weekId, nomination);
      } catch (error) {
        if (error instanceof ApiError && error.status === 409) {
          this.logger.warn('Nomination already exists; returning existing value.', loggerMeta);
          const week = await this.client.getWeek(weekId);
          const existing = week.nominations.find(
            (item) => item.user_id === nomination.user_id && item.album_id === nomination.album_id,
          );
          if (existing) return existing;
        }
        throw error;
      }
    });
  }

  async recordVote(
    weekId: UUID,
    vote: VoteCreate,
    loggerMeta?: Record<string, unknown>,
  ): Promise<VoteRead> {
    return this.withRetry('record-vote', async () => {
      try {
        return await this.client.createWeekVote(weekId, vote);
      } catch (error) {
        if (error instanceof ApiError && error.status === 409) {
          this.logger.warn('Vote already recorded; returning existing vote.', loggerMeta);
          const votes = await this.client.listVotes();
          const voteMatch = votes.find(
            (entry) =>
              entry.week_id === weekId &&
              entry.user_id === vote.user_id &&
              entry.rank === vote.rank,
          );
          if (voteMatch) return voteMatch;
        }
        throw error;
      }
    });
  }

  async recordRating(
    weekId: UUID,
    rating: RatingCreate,
    loggerMeta?: Record<string, unknown>,
  ): Promise<RatingRead> {
    return this.withRetry('record-rating', async () => {
      try {
        return await this.client.upsertRating(weekId, rating);
      } catch (error) {
        if (error instanceof ApiError && error.status === 409) {
          this.logger.warn(
            'Rating already exists; returning previously stored rating.',
            loggerMeta,
          );
          const ratings = await this.client.listRatings();
          const existing = ratings.find(
            (entry) => entry.week_id === weekId && entry.user_id === rating.user_id,
          );
          if (existing) return existing;
        }
        throw error;
      }
    });
  }

  setStarterMessageId(threadId: string, messageId: string): void {
    this.starterMessageIds.set(threadId, messageId);
  }

  getStarterMessageId(threadId: string): string | undefined {
    return this.starterMessageIds.get(threadId);
  }

  async attachNominationsThread(weekId: UUID, threadId: string): Promise<WeekDetail> {
    const updated = await this.withRetry('attach-nominations-thread', () =>
      // Thread IDs are the one week field the bot may set as itself.
      this.serviceClient.updateWeek(weekId, { nominations_thread_id: threadId }),
    );
    this.nominationsThreadMap.set(threadId, updated);
    return updated;
  }

  getWeekForNominationsThread(threadId: string): WeekDetail | undefined {
    return this.nominationsThreadMap.get(threadId);
  }

  async attachRatingsThread(weekId: UUID, threadId: string): Promise<WeekDetail> {
    const updated = await this.withRetry('attach-ratings-thread', () =>
      this.serviceClient.updateWeek(weekId, { ratings_thread_id: threadId }),
    );
    this.ratingsThreadMap.set(threadId, updated);
    return updated;
  }

  getWeekForRatingsThread(threadId: string): WeekDetail | undefined {
    return this.ratingsThreadMap.get(threadId);
  }

  private async withRetry<T>(operation: string, fn: () => Promise<T>): Promise<T> {
    let attempt = 0;
    const { attempts, baseDelayMs } = this.config.retry;

    for (;;) {
      try {
        return await fn();
      } catch (error) {
        attempt += 1;
        const isFinal = attempt >= attempts;
        const delayMs = baseDelayMs * attempt;
        this.logger.warn(`${operation} failed${isFinal ? '' : ', retrying...'}`, {
          attempt,
          attempts,
          error: error instanceof Error ? error.message : String(error),
        });
        if (isFinal) {
          throw error;
        }
        await sleep(delayMs);
      }
    }
  }
}
