export function getApiBaseUrl(): string {
  const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || process.env.SIDETRACK_API_BASE_URL;
  if (!baseUrl) {
    throw new Error('API base URL is not configured. Set NEXT_PUBLIC_API_BASE_URL or SIDETRACK_API_BASE_URL.');
  }
  return baseUrl;
}

export function getDiscordGuildId(): string | undefined {
  return process.env.NEXT_PUBLIC_DISCORD_GUILD_ID || process.env.SIDETRACK_DISCORD_GUILD_ID;
}
