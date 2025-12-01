import { EmbedBuilder, ActionRowBuilder, ButtonBuilder, ButtonStyle } from 'discord.js';
import { NominationRead, NominationWithStats, AlbumRead } from '@sidetrack/shared';
import { createBaseEmbed, BRAND_COLORS, truncate } from './common';

export interface NominationEmbedOptions {
  nomination: NominationRead | NominationWithStats;
  album?: AlbumRead | null;
  nominatorName?: string;
  weekLabel?: string;
  showVoteStats?: boolean;
}

/**
 * Build a beautiful Nomination Card embed.
 */
export function buildNominationEmbed(options: NominationEmbedOptions): EmbedBuilder {
  const { nomination, album, nominatorName, weekLabel, showVoteStats } = options;

  const albumTitle = album?.title ?? 'Unknown Album';
  const artistName = album?.artist_name ?? 'Unknown Artist';
  const releaseYear = album?.release_year;
  const coverUrl = album?.cover_url;

  const titleLine = releaseYear
    ? `${albumTitle} — ${artistName} (${releaseYear})`
    : `${albumTitle} — ${artistName}`;

  const embed = createBaseEmbed()
    .setColor(BRAND_COLORS.nomination)
    .setTitle(`🎵 ${titleLine}`);

  if (coverUrl) {
    embed.setThumbnail(coverUrl);
  }

  // Pitch / Why?
  if (nomination.pitch) {
    embed.setDescription(truncate(nomination.pitch, 300));
  }

  const fields: { name: string; value: string; inline: boolean }[] = [];

  // Nominated by
  if (nominatorName) {
    fields.push({
      name: '👤 Nominated by',
      value: nominatorName,
      inline: true,
    });
  }

  // Tags
  const tags: string[] = [];
  if (nomination.genre) tags.push(nomination.genre);
  if (nomination.decade) tags.push(nomination.decade);
  if (nomination.country) tags.push(nomination.country);

  if (tags.length > 0) {
    fields.push({
      name: '🏷️ Tags',
      value: tags.join(' / '),
      inline: true,
    });
  }

  // Pitch track
  if (nomination.pitch_track_url) {
    fields.push({
      name: '🎧 Pitch Track',
      value: `[Listen](${nomination.pitch_track_url})`,
      inline: true,
    });
  }

  // Vote stats (for poll results)
  if (showVoteStats && 'vote_summary' in nomination && nomination.vote_summary) {
    const { points, first_place, second_place } = nomination.vote_summary;
    fields.push({
      name: '📊 Votes',
      value: `${points} pts (${first_place} 1st, ${second_place} 2nd)`,
      inline: true,
    });
  }

  embed.addFields(fields);

  if (weekLabel) {
    embed.setFooter({ text: weekLabel });
  }

  return embed;
}

/**
 * Build action row with nomination-related buttons.
 */
export function buildNominationButtons(
  nominationId: string,
  options?: { allowEdit?: boolean; allowWithdraw?: boolean },
): ActionRowBuilder<ButtonBuilder> {
  const buttons: ButtonBuilder[] = [];

  if (options?.allowEdit) {
    buttons.push(
      new ButtonBuilder()
        .setCustomId(`nomination:edit:${nominationId}`)
        .setLabel('✏️ Edit')
        .setStyle(ButtonStyle.Secondary),
    );
  }

  if (options?.allowWithdraw) {
    buttons.push(
      new ButtonBuilder()
        .setCustomId(`nomination:withdraw:${nominationId}`)
        .setLabel('🗑️ Withdraw')
        .setStyle(ButtonStyle.Danger),
    );
  }

  return new ActionRowBuilder<ButtonBuilder>().addComponents(buttons);
}

/**
 * Build a simple confirmation embed for nomination success.
 */
export function buildNominationConfirmEmbed(
  albumTitle: string,
  artistName: string,
): EmbedBuilder {
  return createBaseEmbed()
    .setColor(BRAND_COLORS.success)
    .setTitle('✅ Nomination Submitted!')
    .setDescription(`Your nomination for **${albumTitle}** by **${artistName}** has been recorded.`)
    .addFields({
      name: 'Next Steps',
      value: 'Wait for the voting phase to begin. Good luck!',
      inline: false,
    });
}
