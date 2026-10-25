import { EmbedBuilder, ActionRowBuilder, ButtonBuilder, ButtonStyle } from 'discord.js';
import { WeekDetail, NominationRead, AlbumRead } from '@sidetrack/api-client';
import { createBaseEmbed, BRAND_COLORS, formatWeekLabel, formatDiscordTimestamp } from './common';

export interface WeekOverviewOptions {
  week: WeekDetail;
  showNominateButton?: boolean;
  botAvatarUrl?: string;
  /** Pre-fetched album data keyed by album_id for displaying nomination list */
  albumsById?: Map<string, AlbumRead>;
}

/**
 * Build a modern Week Overview embed showing week status, dates, and a live
 * nominations list.
 */
export function buildWeekOverviewEmbed(options: WeekOverviewOptions): EmbedBuilder {
  const { week, botAvatarUrl, albumsById } = options;

  const weekLabel = week.week_number
    ? `WEEK ${String(week.week_number).padStart(3, '0')}`
    : week.label;

  const embed = createBaseEmbed().setColor(BRAND_COLORS.nomination).setTitle(weekLabel);

  if (botAvatarUrl) {
    embed.setAuthor({ name: 'Sidetrack Club', iconURL: botAvatarUrl });
  }

  // Description: instructions + deadline
  const descParts: string[] = [
    'Nominate one album for the club to listen to this week.',
    'Use the **Nominate** button below or paste the mini-form as a message.',
  ];
  if (week.nominations_close_at) {
    descParts.push('');
    descParts.push(`Deadline: ${formatDiscordTimestamp(week.nominations_close_at, 'F')}`);
  }
  embed.setDescription(descParts.join('\n'));

  // --- Status fields ---
  const nominationCount = week.aggregates?.nomination_count ?? week.nominations?.length ?? 0;
  const fields: { name: string; value: string; inline: boolean }[] = [];

  fields.push({
    name: 'Nominations',
    value: `**${nominationCount}** so far`,
    inline: true,
  });

  if (week.nominations_close_at) {
    fields.push({
      name: 'Closes',
      value: formatDiscordTimestamp(week.nominations_close_at, 'R'),
      inline: true,
    });
  }

  if (week.poll_close_at) {
    fields.push({
      name: 'Poll Ends',
      value: formatDiscordTimestamp(week.poll_close_at, 'R'),
      inline: true,
    });
  }

  if (week.discussion_at) {
    fields.push({
      name: 'Discussion',
      value: formatDiscordTimestamp(week.discussion_at, 'F'),
      inline: false,
    });
  }

  // --- Live nominations list ---
  const nominations = week.nominations ?? [];
  if (nominations.length > 0) {
    const lines: string[] = [];
    for (let i = 0; i < nominations.length; i++) {
      const nom = nominations[i] as NominationRead;
      const album = albumsById?.get(nom.album_id);
      const title = album?.title ?? 'Unknown';
      const artist = album?.artist_name ?? 'Unknown';
      lines.push(`\`${i + 1}.\` **${title}** \u2014 ${artist}`);
    }
    // Discord field value limit is 1024 chars; truncate if needed
    let listText = lines.join('\n');
    if (listText.length > 1000) {
      const shown = lines.slice(0, 10).join('\n');
      listText = `${shown}\n*\u2026and ${nominations.length - 10} more*`;
    }
    fields.push({
      name: '\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500',
      value: listText,
      inline: false,
    });
  }

  embed.addFields(fields);

  embed.setFooter({
    text: `${formatWeekLabel(week.label, week.week_number)} \u2022 One album per person \u2022 Sidetrack Club`,
  });

  return embed;
}

/**
 * Build action row with Nominate + Refresh buttons for week overview.
 */
export function buildWeekOverviewButtons(weekId: string): ActionRowBuilder<ButtonBuilder> {
  return new ActionRowBuilder<ButtonBuilder>().addComponents(
    new ButtonBuilder()
      .setCustomId(`week:nominate:${weekId}`)
      .setLabel('Nominate an Album')
      .setEmoji('\u{1F3B5}')
      .setStyle(ButtonStyle.Primary),
    new ButtonBuilder()
      .setCustomId(`week:refresh:${weekId}`)
      .setLabel('Refresh')
      .setEmoji('\u{1F504}')
      .setStyle(ButtonStyle.Secondary),
  );
}

/**
 * Return the pinned mini-form message content (plain text).
 * Simplified — tags and year are now auto-filled by the bot.
 */
export function buildMiniFormText(): string {
  return [
    '**Mini-form** \u2014 copy, paste, fill in, and post:',
    '',
    '```',
    'Album \u2014 Artist',
    'Why?: <your pitch>',
    'Pitch track: <Spotify or YouTube link>',
    '```',
  ].join('\n');
}

/**
 * Build a compact week summary card for lists.
 */
export function buildWeekCompactEmbed(week: WeekDetail): EmbedBuilder {
  const weekLabel = formatWeekLabel(week.label, week.week_number);
  const nominationCount = week.aggregates?.nomination_count ?? week.nominations?.length ?? 0;

  return createBaseEmbed()
    .setColor(week.winner_album_id ? BRAND_COLORS.winner : BRAND_COLORS.primary)
    .setTitle(weekLabel)
    .setDescription(
      week.winner_album_id ? '\u{1F3C6} Winner announced' : `${nominationCount} nominations`,
    );
}
