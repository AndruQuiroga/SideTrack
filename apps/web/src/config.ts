export function getApiBaseUrl(): string {
  return process.env.NEXT_PUBLIC_API_BASE_URL || process.env.SIDETRACK_API_BASE_URL || 'http://localhost:8000';
}

export function getDiscordGuildId(): string | undefined {
  return process.env.NEXT_PUBLIC_DISCORD_GUILD_ID || process.env.SIDETRACK_DISCORD_GUILD_ID;
}
