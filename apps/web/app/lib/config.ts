/**
 * Public, browser-safe configuration. The API base URL is deliberately absent: only the
 * web server calls the API (see server-env.ts and server-api.ts, ADR 0009).
 */
export function getDiscordGuildId(): string | undefined {
  return process.env.NEXT_PUBLIC_DISCORD_GUILD_ID || process.env.SIDETRACK_DISCORD_GUILD_ID;
}
