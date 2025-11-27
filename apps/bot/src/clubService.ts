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
} from '@sidetrack/shared';

import { BotConfig } from './config';
import { Logger } from './logger';

export interface ClubPhasePayload {
  week: WeekCreate;
  update?: WeekUpdate;
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export class ClubSyncService {
  constructor(
    private readonly client: SidetrackApiClient,
    private readonly config: BotConfig,
    private readonly logger: Logger,
  ) {}

  async bootstrap(): Promise<WeekDetail[]> {
    this.logger.info('Bootstrapping bot sync service with shared API client.', {
      apiBaseUrl: this.config.api.baseUrl,
    });
    return this.client.listWeeks({ has_winner: false });
  }

  async ensureDiscordUser(discordUserId: string, displayName: string): Promise<UserRead> {
    try {
      return await this.client.lookupUserByProvider(ProviderType.DISCORD, discordUserId);
    } catch (error) {
      if (!(error instanceof ApiError) || error.status !== 404) {
        throw error;
      }
      this.logger.info('Creating Sidetrack user for Discord member.', { discordUserId });

      const user = await this.withRetry('create-user', () =>
        this.client.createUser({ display_name: displayName }),
      );

      await this.withRetry('link-discord-account', async () => {
        try {
          await this.client.linkAccount(user.id, {
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
            (entry) => entry.week_id === weekId && entry.user_id === vote.user_id && entry.rank === vote.rank,
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
          this.logger.warn('Rating already exists; returning previously stored rating.', loggerMeta);
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

  private async withRetry<T>(operation: string, fn: () => Promise<T>): Promise<T> {
    let attempt = 0;
    const { attempts, baseDelayMs } = this.config.retry;

    while (true) {
      try {
        return await fn();
      } catch (error) {
        attempt += 1;
        const isFinal = attempt >= attempts;
        const delayMs = baseDelayMs * attempt;
        this.logger.warn(
          `${operation} failed${isFinal ? '' : ', retrying...'}`,
          { attempt, attempts, error: error instanceof Error ? error.message : String(error) },
        );
        if (isFinal) {
          throw error;
        }
        await sleep(delayMs);
      }
    }
  }
}
