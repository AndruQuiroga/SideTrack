import path from 'node:path';

export function getApiBaseUrl(): string {
  return process.env.NEXT_PUBLIC_API_BASE_URL || process.env.SIDETRACK_API_BASE_URL || 'http://localhost:8000';
}

export function getLegacyDataPath(): string {
  return path.resolve(__dirname, 'legacy', 'legacy-weeks.json');
}

export function getDiscordGuildId(): string | undefined {
  return process.env.NEXT_PUBLIC_DISCORD_GUILD_ID || process.env.SIDETRACK_DISCORD_GUILD_ID;
}
