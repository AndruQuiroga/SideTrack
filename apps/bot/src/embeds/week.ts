import { EmbedBuilder, ActionRowBuilder, ButtonBuilder, ButtonStyle } from 'discord.js';
import { WeekDetail } from '@sidetrack/shared';
import { createBaseEmbed, BRAND_COLORS, formatWeekLabel, formatDiscordTimestamp } from './common';

export interface WeekOverviewOptions {
  week: WeekDetail;
  showNominateButton?: boolean;
}

/**
 * Build a Week Overview embed showing week status and key dates.
 */
export function buildWeekOverviewEmbed(options: WeekOverviewOptions): EmbedBuilder {
  const { week } = options;
  const weekLabel = formatWeekLabel(week.label, week.week_number);

  const embed = createBaseEmbed()
    .setColor(BRAND_COLORS.primary)
    .setTitle(`📅 ${weekLabel}`)
    .setDescription('Welcome to a new week of Sidetrack Club! Nominate your album picks below.');

  const fields: { name: string; value: string; inline: boolean }[] = [];

  // Status
  const nominationCount = week.aggregates?.nomination_count ?? week.nominations?.length ?? 0;
  fields.push({
    name: '📋 Status',
    value: `${nominationCount} nomination${nominationCount !== 1 ? 's' : ''} so far`,
    inline: true,
  });

  // Phase info
  if (week.winner_album_id) {
    fields.push({ name: '🏆 Phase', value: 'Winner Announced', inline: true });
  } else if (week.nominations_close_at && new Date(week.nominations_close_at) > new Date()) {
    fields.push({ name: '📝 Phase', value: 'Nominations Open', inline: true });
  } else if (week.poll_close_at && new Date(week.poll_close_at) > new Date()) {
    fields.push({ name: '🗳️ Phase', value: 'Voting Open', inline: true });
  } else {
    fields.push({ name: '📊 Phase', value: 'In Progress', inline: true });
  }

  // Key dates
  if (week.nominations_close_at) {
    fields.push({
      name: '⏰ Nominations Close',
      value: formatDiscordTimestamp(week.nominations_close_at, 'R'),
      inline: true,
    });
  }

  if (week.poll_close_at) {
    fields.push({
      name: '🗳️ Voting Ends',
      value: formatDiscordTimestamp(week.poll_close_at, 'R'),
      inline: true,
    });
  }

  if (week.discussion_at) {
    fields.push({
      name: '🎧 Discussion',
      value: formatDiscordTimestamp(week.discussion_at, 'f'),
      inline: true,
    });
  }

  embed.addFields(fields);
  embed.setFooter({ text: `Week ID: ${week.id.slice(0, 8)}` });

  return embed;
}

/**
 * Build action row with Nominate button for week overview.
 */
export function buildWeekOverviewButtons(weekId: string): ActionRowBuilder<ButtonBuilder> {
  return new ActionRowBuilder<ButtonBuilder>().addComponents(
    new ButtonBuilder()
      .setCustomId(`week:nominate:${weekId}`)
      .setLabel('🎵 Nominate an Album')
      .setStyle(ButtonStyle.Primary),
    new ButtonBuilder()
      .setCustomId(`week:refresh:${weekId}`)
      .setLabel('🔄 Refresh')
      .setStyle(ButtonStyle.Secondary),
  );
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
      week.winner_album_id
        ? '🏆 Winner announced'
        : `${nominationCount} nominations`,
    );
}
