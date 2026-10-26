/**
 * Minimal environment loader for TypeScript services (core/env-config).
 * Keeps bot/web/worker aligned on required variables and fails fast when a critical value is missing.
 */

export interface EnvSource {
  [key: string]: string | undefined;
}

export interface BaseEnvConfig {
  /** API base URL for server-side clients (bot/worker) or public web calls. */
  apiBaseUrl: string;
  /** This client's own API token (ADR 0009: each client has its own). */
  apiToken?: string;
}

export interface BotEnvConfig extends BaseEnvConfig {
  /** Discord bot token for logging in. */
  discordBotToken: string;
  discordClientId?: string;
  discordGuildId?: string;
}

/**
 * Load core API-related variables. Requires either SIDETRACK_API_BASE_URL or NEXT_PUBLIC_API_BASE_URL.
 */
export function loadBaseEnv(
  env: EnvSource = process.env,
  tokenVariable: 'SIDETRACK_WEB_API_TOKEN' | 'SIDETRACK_BOT_API_TOKEN' = 'SIDETRACK_WEB_API_TOKEN',
): BaseEnvConfig {
  const apiBaseUrl = env.SIDETRACK_API_BASE_URL ?? env.NEXT_PUBLIC_API_BASE_URL;
  if (!apiBaseUrl) {
    throw new Error('Missing SIDETRACK_API_BASE_URL or NEXT_PUBLIC_API_BASE_URL in environment.');
  }

  return {
    apiBaseUrl,
    apiToken: env[tokenVariable],
  };
}

/**
 * Load Discord bot-specific variables on top of the base API config.
 */
export function loadBotEnv(env: EnvSource = process.env): BotEnvConfig {
  const base = loadBaseEnv(env, 'SIDETRACK_BOT_API_TOKEN');
  const discordBotToken = env.DISCORD_BOT_TOKEN;

  if (!discordBotToken) {
    throw new Error('Missing DISCORD_BOT_TOKEN in environment.');
  }

  return {
    ...base,
    discordBotToken,
    discordClientId: env.DISCORD_CLIENT_ID,
    discordGuildId: env.DISCORD_GUILD_ID,
  };
}
