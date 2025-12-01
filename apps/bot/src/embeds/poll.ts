import {
  EmbedBuilder,
  ActionRowBuilder,
  ButtonBuilder,
  ButtonStyle,
  StringSelectMenuBuilder,
  StringSelectMenuOptionBuilder,
} from 'discord.js';
import { NominationWithStats, AlbumRead, WeekDetail } from '@sidetrack/shared';
import { createBaseEmbed, BRAND_COLORS, formatWeekLabel, truncate } from './common';

export interface PollOverviewOptions {
  week: WeekDetail;
  nominations: NominationWithStats[];
  albums?: Map<string, AlbumRead>;
  nominatorNames?: Map<string, string>;
}

/**
 * Build a Poll Overview embed listing all nominees for voting.
 */
export function buildPollOverviewEmbed(options: PollOverviewOptions): EmbedBuilder {
  const { week, nominations, albums, nominatorNames } = options;
  const weekLabel = formatWeekLabel(week.label, week.week_number);

  const embed = createBaseEmbed()
    .setColor(BRAND_COLORS.poll)
    .setTitle(`🗳️ ${weekLabel} — Voting`)
    .setDescription(
      "Pick your **1st & 2nd choice**!\n" +
        "• 1st choice = 2 points\n" +
        "• 2nd choice = 1 point\n\n" +
        "Click **Open Ballot** to vote.",
    );

  // List nominations
  const nomineeList = nominations
    .map((nom, idx) => {
      const album = albums?.get(nom.album_id);
      const nominator = nominatorNames?.get(nom.user_id) ?? 'Unknown';
      const title = album?.title ?? 'Unknown Album';
      const artist = album?.artist_name ?? 'Unknown Artist';
      return `${idx + 1}. **${title}** — ${artist} *(${nominator})*`;
    })
    .join('\n');

  if (nomineeList) {
    embed.addFields({ name: '🎵 Nominees', value: truncate(nomineeList, 1024), inline: false });
  }

  if (week.poll_close_at) {
    const timestamp = Math.floor(new Date(week.poll_close_at).getTime() / 1000);
    embed.addFields({ name: '⏰ Voting Ends', value: `<t:${timestamp}:R>`, inline: true });
  }

  embed.setFooter({ text: `${nominations.length} nominees` });

  return embed;
}

/**
 * Build Open Ballot button for poll.
 */
export function buildPollOpenBallotButton(weekId: string): ActionRowBuilder<ButtonBuilder> {
  return new ActionRowBuilder<ButtonBuilder>().addComponents(
    new ButtonBuilder()
      .setCustomId(`poll:open:${weekId}`)
      .setLabel('🗳️ Open Ballot')
      .setStyle(ButtonStyle.Primary),
  );
}

/**
 * Build ephemeral ballot with select menus for 1st and 2nd choice.
 */
export function buildBallotSelectMenus(
  weekId: string,
  nominations: NominationWithStats[],
  albums?: Map<string, AlbumRead>,
): ActionRowBuilder<StringSelectMenuBuilder>[] {
  const options: StringSelectMenuOptionBuilder[] = nominations.map((nom) => {
    const album = albums?.get(nom.album_id);
    const title = album?.title ?? 'Unknown Album';
    const artist = album?.artist_name ?? 'Unknown Artist';

    const builder = new StringSelectMenuOptionBuilder()
      .setLabel(truncate(`${title} — ${artist}`, 100))
      .setValue(nom.id);

    if (nom.pitch) {
      builder.setDescription(truncate(nom.pitch, 50));
    }

    return builder;
  });

  const firstChoice = new StringSelectMenuBuilder()
    .setCustomId(`poll:first:${weekId}`)
    .setPlaceholder('Select your 1st choice (2 pts)')
    .addOptions(options);

  const secondChoice = new StringSelectMenuBuilder()
    .setCustomId(`poll:second:${weekId}`)
    .setPlaceholder('Select your 2nd choice (1 pt) - optional')
    .addOptions(options);

  return [
    new ActionRowBuilder<StringSelectMenuBuilder>().addComponents(firstChoice),
    new ActionRowBuilder<StringSelectMenuBuilder>().addComponents(secondChoice),
  ];
}

/**
 * Build Submit Ballot button.
 */
export function buildBallotSubmitButton(weekId: string): ActionRowBuilder<ButtonBuilder> {
  return new ActionRowBuilder<ButtonBuilder>().addComponents(
    new ButtonBuilder()
      .setCustomId(`poll:submit:${weekId}`)
      .setLabel('✅ Submit Ballot')
      .setStyle(ButtonStyle.Success),
  );
}

export interface PollResultsOptions {
  week: WeekDetail;
  rankedNominations: NominationWithStats[];
  albums?: Map<string, AlbumRead>;
  nominatorNames?: Map<string, string>;
}

/**
 * Build Poll Results embed with scoreboard.
 */
export function buildPollResultsEmbed(options: PollResultsOptions): EmbedBuilder {
  const { week, rankedNominations, albums, nominatorNames } = options;
  const weekLabel = formatWeekLabel(week.label, week.week_number);

  const embed = createBaseEmbed()
    .setColor(BRAND_COLORS.poll)
    .setTitle(`📊 ${weekLabel} — Poll Results`)
    .setDescription('The votes are in! Here are the final standings:');

  const results = rankedNominations
    .slice(0, 10) // Top 10
    .map((nom, idx) => {
      const album = albums?.get(nom.album_id);
      const nominator = nominatorNames?.get(nom.user_id) ?? 'Unknown';
      const title = album?.title ?? 'Unknown Album';
      const artist = album?.artist_name ?? 'Unknown Artist';
      const { points, first_place, second_place } = nom.vote_summary;

      const medal = idx === 0 ? '🥇' : idx === 1 ? '🥈' : idx === 2 ? '🥉' : `${idx + 1}.`;
      return `${medal} **${title}** — ${artist}\n   ${points} pts (${first_place}×1st, ${second_place}×2nd) — *${nominator}*`;
    })
    .join('\n\n');

  if (results) {
    embed.addFields({ name: '🏆 Standings', value: truncate(results, 1024), inline: false });
  }

  embed.setFooter({ text: `Total nominees: ${rankedNominations.length}` });

  return embed;
}

export interface WinnerAnnouncementOptions {
  week: WeekDetail;
  winner: NominationWithStats;
  album?: AlbumRead | null;
  nominatorName?: string;
}

/**
 * Build a Winner Announcement embed.
 */
export function buildWinnerEmbed(options: WinnerAnnouncementOptions): EmbedBuilder {
  const { week, winner, album, nominatorName } = options;
  const weekLabel = formatWeekLabel(week.label, week.week_number);

  const title = album?.title ?? 'Unknown Album';
  const artist = album?.artist_name ?? 'Unknown Artist';
  const coverUrl = album?.cover_url;
  const releaseYear = album?.release_year;

  const titleLine = releaseYear ? `${title} (${releaseYear})` : title;

  const embed = createBaseEmbed()
    .setColor(BRAND_COLORS.winner)
    .setTitle(`🏆 ${weekLabel} — Winner!`)
    .setDescription(`The club has spoken! This week's album is:\n\n## ${titleLine}\nby **${artist}**`);

  if (coverUrl) {
    embed.setImage(coverUrl);
  }

  const fields: { name: string; value: string; inline: boolean }[] = [];

  if (nominatorName) {
    fields.push({ name: '👤 Nominated by', value: nominatorName, inline: true });
  }

  const { points, first_place, second_place } = winner.vote_summary;
  fields.push({
    name: '📊 Votes',
    value: `${points} points (${first_place}×1st, ${second_place}×2nd)`,
    inline: true,
  });

  if (winner.pitch) {
    fields.push({ name: '💬 Pitch', value: truncate(winner.pitch, 256), inline: false });
  }

  if (winner.pitch_track_url) {
    fields.push({ name: '🎧 Pitch Track', value: `[Listen](${winner.pitch_track_url})`, inline: true });
  }

  embed.addFields(fields);
  embed.setFooter({ text: 'Time to listen and rate!' });

  return embed;
}

/**
 * Build Open Ratings button after winner announcement.
 */
export function buildOpenRatingsButton(weekId: string): ActionRowBuilder<ButtonBuilder> {
  return new ActionRowBuilder<ButtonBuilder>().addComponents(
    new ButtonBuilder()
      .setCustomId(`ratings:open:${weekId}`)
      .setLabel('⭐ Open Ratings')
      .setStyle(ButtonStyle.Primary),
  );
}
