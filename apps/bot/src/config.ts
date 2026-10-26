import { readSecret } from './secrets';

export interface ApiConfig {
  baseUrl: string;
  /** The bot's own API token (SIDETRACK_BOT_API_TOKEN); never shared with the web app. */
  token?: string;
}

export interface DiscordConfig {
  token: string;
  clientId?: string;
  guildId?: string;
  /** Privileged Server Members intent, needed to hear members leave the guild. */
  membersIntent: boolean;
}

export interface RetryConfig {
  attempts: number;
  baseDelayMs: number;
}

export interface BotConfig {
  api: ApiConfig;
  discord: DiscordConfig;
  retry: RetryConfig;
  club: ClubConfig;
}

export interface ClubConfig {
  nominationsForumId?: string;
  adminRoleIds?: string[];
}

const DEFAULT_RETRY: RetryConfig = {
  attempts: 3,
  baseDelayMs: 250,
};

export function loadBotConfig(env: NodeJS.ProcessEnv = process.env): BotConfig {
  const baseUrl = env.SIDETRACK_API_BASE_URL || env.API_BASE_URL;
  if (!baseUrl) {
    throw new Error('SIDETRACK_API_BASE_URL is required to start the bot.');
  }

  const discordToken = readSecret('DISCORD_BOT_TOKEN', env) || env.DISCORD_TOKEN;
  if (!discordToken) {
    throw new Error('DISCORD_BOT_TOKEN is required to start the bot.');
  }

  const retryAttempts = env.SIDETRACK_RETRY_ATTEMPTS
    ? Number(env.SIDETRACK_RETRY_ATTEMPTS)
    : DEFAULT_RETRY.attempts;
  const retryDelayMs = env.SIDETRACK_RETRY_DELAY_MS
    ? Number(env.SIDETRACK_RETRY_DELAY_MS)
    : DEFAULT_RETRY.baseDelayMs;

  return {
    api: {
      baseUrl,
      token: readSecret('SIDETRACK_BOT_API_TOKEN', env),
    },
    discord: {
      token: discordToken,
      clientId: env.DISCORD_CLIENT_ID,
      guildId: env.DISCORD_GUILD_ID,
      membersIntent: env.DISCORD_MEMBERS_INTENT === 'true',
    },
    retry: {
      attempts: Number.isFinite(retryAttempts) ? retryAttempts : DEFAULT_RETRY.attempts,
      baseDelayMs: Number.isFinite(retryDelayMs) ? retryDelayMs : DEFAULT_RETRY.baseDelayMs,
    },
    club: {
      nominationsForumId:
        env.SIDETRACK_NOMINATIONS_FORUM_ID || env.NOMINATIONS_FORUM_ID || env.DISCORD_NOMINATIONS_FORUM_ID,
      adminRoleIds:
        env.SIDETRACK_ADMIN_ROLE_IDS || env.DISCORD_ADMIN_ROLE_IDS
          ? (env.SIDETRACK_ADMIN_ROLE_IDS || env.DISCORD_ADMIN_ROLE_IDS || '')
              .split(',')
              .map((value) => value.trim())
              .filter(Boolean)
          : undefined,
    },
  };
}
