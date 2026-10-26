import {
  EmbedBuilder,
  ActionRowBuilder,
  ButtonBuilder,
  ButtonStyle,
  ColorResolvable,
} from 'discord.js';
import { NominationRead, NominationWithStats, AlbumRead } from '@sidetrack/api-client';
import { createBaseEmbed, BRAND_COLORS, truncate, formatWeekLabel } from './common';

export interface NominationEmbedOptions {
  nomination: NominationRead | NominationWithStats;
  album?: AlbumRead | null;
  nominatorName?: string;
  nominatorAvatarURL?: string;
  weekLabel?: string;
  weekNumber?: number | null;
  nominationIndex?: number | null;
  showVoteStats?: boolean;
  /** Dominant color extracted from album art (if available) */
  accentColor?: ColorResolvable | null;
  /** Resolved pitch track info (name + artist from Spotify) */
  pitchTrackInfo?: { name: string; artist: string } | null;
}

/**
 * Build a beautiful, modern Nomination Card embed.
 *
 * Features:
 * - Dominant color from album art as embed accent
 * - Album cover as thumbnail (right-aligned)
 * - Clean typography with typographic quotes for pitch
 * - Auto-populated genres from enrichment
 * - Resolved pitch track name (not just a raw URL)
 * - Nomination index in footer
 */
export function buildNominationEmbed(options: NominationEmbedOptions): EmbedBuilder {
  const {
    nomination,
    album,
    nominatorName,
    nominatorAvatarURL,
    weekLabel,
    weekNumber,
    nominationIndex,
    showVoteStats,
    accentColor,
    pitchTrackInfo,
  } = options;

  const albumTitle = album?.title ?? 'Unknown Album';
  const artistName = album?.artist_name ?? 'Unknown Artist';
  const releaseYear = album?.release_year;
  const coverUrl = album?.cover_url;
  const genres = album?.genres ?? [];
  const spotifyUrl = album?.spotify_url;

  // --- Color ---
  const color = accentColor ?? BRAND_COLORS.nomination;

  // --- Title: clean album name ---
  const embed = new EmbedBuilder().setColor(color).setTitle(`${albumTitle}`).setTimestamp();

  // Link title to Spotify album page if available
  if (spotifyUrl) {
    embed.setURL(spotifyUrl);
  }

  // --- Author: nominator ---
  if (nominatorName) {
    embed.setAuthor({
      name: `Nominated by ${nominatorName}`,
      iconURL: nominatorAvatarURL ?? undefined,
    });
  }

  // --- Thumbnail: album cover (right-aligned) ---
  if (coverUrl) {
    embed.setThumbnail(coverUrl);
  }

  // --- Description: artist · year, genres, then pitch ---
  const descParts: string[] = [];

  // Line 1: Artist · Year
  const artistLine = releaseYear ? `**${artistName}** · ${releaseYear}` : `**${artistName}**`;
  descParts.push(artistLine);

  // Line 2: Genre tags (from auto-enrichment)
  const tagParts: string[] = [];
  if (genres.length > 0) {
    // Capitalize and take top 3 genres
    const displayGenres = genres.slice(0, 3).map((g) => g.charAt(0).toUpperCase() + g.slice(1));
    tagParts.push(...displayGenres);
  }
  // Include nomination-level tags if no album genres
  if (tagParts.length === 0) {
    if (nomination.genre) tagParts.push(nomination.genre);
    if (nomination.decade) tagParts.push(nomination.decade);
    if (nomination.country) tagParts.push(nomination.country);
  }
  if (tagParts.length > 0) {
    descParts.push(tagParts.join(' · '));
  }

  // Separator
  descParts.push('');

  // Pitch with typographic quotes
  if (nomination.pitch) {
    const pitch = truncate(nomination.pitch, 400);
    descParts.push(`*\u201C${pitch}\u201D*`);
  }

  embed.setDescription(descParts.join('\n'));

  // --- Fields ---
  const fields: { name: string; value: string; inline: boolean }[] = [];

  // Pitch track — resolved name or raw link
  if (nomination.pitch_track_url) {
    let trackValue: string;
    if (pitchTrackInfo) {
      trackValue = `[**${pitchTrackInfo.name}** — ${pitchTrackInfo.artist}](${nomination.pitch_track_url})`;
    } else {
      trackValue = `[Listen](${nomination.pitch_track_url})`;
    }
    fields.push({
      name: '\u{1F3B5} Pitch Track',
      value: trackValue,
      inline: true,
    });
  }

  // Vote stats (for poll results view)
  if (showVoteStats && 'vote_summary' in nomination && nomination.vote_summary) {
    const { points, first_place, second_place } = nomination.vote_summary;
    fields.push({
      name: '\u{1F4CA} Votes',
      value: `**${points}** pts \u2022 ${first_place} first \u2022 ${second_place} second`,
      inline: true,
    });
  }

  if (fields.length > 0) {
    embed.addFields(fields);
  }

  // --- Footer: nomination index + week label ---
  const footerParts: string[] = [];
  if (nominationIndex != null) {
    footerParts.push(`#${nominationIndex}`);
  }
  if (weekLabel || weekNumber) {
    footerParts.push(formatWeekLabel(weekLabel ?? '', weekNumber ?? null));
  }
  footerParts.push('Sidetrack Club');

  embed.setFooter({ text: footerParts.join(' \u2022 ') });

  return embed;
}

/**
 * Build action row with nomination-related buttons.
 *
 * Buttons: Edit (pitch/track), Change Album, Withdraw.
 * All are keyed by nomination ID for handler routing.
 */
export function buildNominationButtons(
  nominationId: string,
  options?: { allowEdit?: boolean; allowChangeAlbum?: boolean; allowWithdraw?: boolean },
): ActionRowBuilder<ButtonBuilder> {
  const buttons: ButtonBuilder[] = [];

  if (options?.allowEdit !== false) {
    buttons.push(
      new ButtonBuilder()
        .setCustomId(`nomination:edit:${nominationId}`)
        .setLabel('Edit')
        .setEmoji('\u270F\uFE0F')
        .setStyle(ButtonStyle.Secondary),
    );
  }

  if (options?.allowChangeAlbum !== false) {
    buttons.push(
      new ButtonBuilder()
        .setCustomId(`nomination:change-album:${nominationId}`)
        .setLabel('Change Album')
        .setEmoji('\u{1F504}')
        .setStyle(ButtonStyle.Secondary),
    );
  }

  if (options?.allowWithdraw !== false) {
    buttons.push(
      new ButtonBuilder()
        .setCustomId(`nomination:withdraw:${nominationId}`)
        .setLabel('Withdraw')
        .setEmoji('\u{1F5D1}\uFE0F')
        .setStyle(ButtonStyle.Danger),
    );
  }

  return new ActionRowBuilder<ButtonBuilder>().addComponents(buttons);
}

/**
 * Build a sleek confirmation embed for nomination success.
 */
export function buildNominationConfirmEmbed(
  albumTitle: string,
  artistName: string,
  coverUrl?: string | null,
): EmbedBuilder {
  const embed = createBaseEmbed()
    .setColor(BRAND_COLORS.success)
    .setTitle('Nomination Submitted')
    .setDescription(
      `Your nomination for **${albumTitle}** by **${artistName}** has been recorded.\n\nWait for the voting phase to begin. Good luck!`,
    );

  if (coverUrl) {
    embed.setThumbnail(coverUrl);
  }

  return embed;
}

/**
 * Build a greyed-out embed for a withdrawn nomination.
 */
export function buildWithdrawnNominationEmbed(
  albumTitle: string,
  artistName: string,
  nominatorName: string,
): EmbedBuilder {
  return new EmbedBuilder()
    .setColor(0x2f3136) // Discord dark background — looks "greyed out"
    .setTitle(`~~${albumTitle}~~`)
    .setDescription(`~~${artistName}~~\n\n*Nomination withdrawn by ${nominatorName}*`)
    .setTimestamp();
}
