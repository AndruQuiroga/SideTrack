import { EmbedBuilder, ColorResolvable } from 'discord.js';

/** Sidetrack brand colors */
export const BRAND_COLORS = {
  primary: 0x5865f2 as ColorResolvable, // Discord blurple
  success: 0x57f287 as ColorResolvable, // Green
  warning: 0xfee75c as ColorResolvable, // Yellow
  danger: 0xed4245 as ColorResolvable, // Red
  info: 0x5865f2 as ColorResolvable, // Blurple
  winner: 0xffd700 as ColorResolvable, // Gold
  nomination: 0x9b59b6 as ColorResolvable, // Purple
  poll: 0x3498db as ColorResolvable, // Blue
  rating: 0xe67e22 as ColorResolvable, // Orange
};

/** Common author header for all embeds */
export const SIDETRACK_AUTHOR = {
  name: 'Sidetrack Club',
  iconURL: 'https://cdn.discordapp.com/embed/avatars/0.png',
};

/**
 * Create a base embed with consistent Sidetrack branding.
 */
export function createBaseEmbed(): EmbedBuilder {
  return new EmbedBuilder()
    .setColor(BRAND_COLORS.primary)
    .setAuthor(SIDETRACK_AUTHOR)
    .setTimestamp();
}

/**
 * Format a week label for display.
 */
export function formatWeekLabel(label: string, weekNumber?: number | null): string {
  if (weekNumber) {
    return `Week ${String(weekNumber).padStart(3, '0')}`;
  }
  return label;
}

/**
 * Format a date for Discord timestamp display.
 */
export function formatDiscordTimestamp(date: string | Date, style: 'R' | 'F' | 'f' | 'D' | 'd' | 'T' | 't' = 'f'): string {
  const timestamp = date instanceof Date ? date.getTime() : new Date(date).getTime();
  const seconds = Math.floor(timestamp / 1000);
  return `<t:${seconds}:${style}>`;
}

/**
 * Generate a star rating string for display (e.g., "⭐⭐⭐⭐☆" for 4.0).
 */
export function formatStarRating(value: number): string {
  const fullStars = Math.floor(value);
  const halfStar = value % 1 >= 0.5;
  const emptyStars = 5 - fullStars - (halfStar ? 1 : 0);

  let result = '⭐'.repeat(fullStars);
  if (halfStar) {
    result += '✦'; // Half-star approximation
  }
  result += '☆'.repeat(emptyStars);
  return result;
}

/**
 * Truncate text to a maximum length with ellipsis.
 */
export function truncate(text: string, maxLength: number): string {
  if (text.length <= maxLength) return text;
  return text.slice(0, maxLength - 3) + '...';
}

/**
 * Create a simple progress bar string.
 */
export function createProgressBar(value: number, max: number, length = 10): string {
  const filled = Math.round((value / max) * length);
  const empty = length - filled;
  return '█'.repeat(filled) + '░'.repeat(empty);
}
