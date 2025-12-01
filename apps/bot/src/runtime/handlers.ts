import {
  APIInteractionGuildMember,
  ButtonInteraction,
  ChannelType,
  ChatInputCommandInteraction,
  Client,
  GuildMember,
  GuildMemberRoleManager,
  Interaction,
  ModalSubmitInteraction,
  PermissionFlagsBits,
  StringSelectMenuInteraction,
} from 'discord.js';

import { Logger } from '../logger';
import { ClubSyncService } from '../clubService';
import { BotConfig } from '../config';
import { WeekCreate, WeekUpdate, NominationCreate, VoteCreate, RatingCreate, AlbumRead, WeekDetail } from '@sidetrack/shared';
import {
  pingCommand,
  stWeekCommand,
  stNominateCommand,
  stPollCommand,
  stRatingsCommand,
  stHelpCommand,
  weekStartCommand,
} from './commands';
import { ReminderScheduler } from '../scheduler';
import {
  buildWeekOverviewEmbed,
  buildWeekOverviewButtons,
  buildNominationEmbed,
  buildNominationConfirmEmbed,
  buildPollOverviewEmbed,
  buildPollOpenBallotButton,
  buildBallotSelectMenus,
  buildBallotSubmitButton,
  buildPollResultsEmbed,
  buildWinnerEmbed,
  buildOpenRatingsButton,
  buildRatingsCallEmbed,
  buildRateAlbumButton,
  buildRatingsSummaryEmbed,
  buildRatingConfirmEmbed,
  createBaseEmbed,
  BRAND_COLORS,
} from '../embeds';
import { buildNominationModal, buildRatingModal } from '../interactions/modals';

/** Session state for ballot voting */
interface BallotSession {
  firstChoice?: string;
  secondChoice?: string;
}

const ballotSessions = new Map<string, BallotSession>();

export function registerInteractionHandlers(
  client: Client,
  service: ClubSyncService,
  scheduler: ReminderScheduler,
  config: BotConfig,
  logger: Logger,
): void {
  client.on('interactionCreate', async (interaction: Interaction) => {
    try {
      // Slash commands
      if (interaction.isChatInputCommand()) {
        await handleSlashCommand(interaction, service, scheduler, config, logger);
        return;
      }

      // Button interactions
      if (interaction.isButton()) {
        await handleButtonInteraction(interaction, service, config, logger);
        return;
      }

      // Select menu interactions
      if (interaction.isStringSelectMenu()) {
        await handleSelectMenuInteraction(interaction, logger);
        return;
      }

      // Modal submissions
      if (interaction.isModalSubmit()) {
        await handleModalSubmit(interaction, service, config, logger);
        return;
      }
    } catch (error) {
      logger.error('Unhandled interaction error.', {
        error: error instanceof Error ? error.message : String(error),
        interactionType: interaction.type,
      });

      // Try to respond with error if possible
      if ('reply' in interaction && typeof interaction.reply === 'function') {
        try {
          const replyFn = interaction.deferred || interaction.replied
            ? interaction.editReply.bind(interaction)
            : interaction.reply.bind(interaction);
          await replyFn({
            content: '❌ An error occurred while processing your request. Please try again.',
            ephemeral: true,
          });
        } catch {
          // Ignore reply errors
        }
      }
    }
  });
}

async function handleSlashCommand(
  interaction: ChatInputCommandInteraction,
  service: ClubSyncService,
  scheduler: ReminderScheduler,
  config: BotConfig,
  logger: Logger,
): Promise<void> {
  switch (interaction.commandName) {
    case pingCommand.data.name:
      await handlePing(interaction, logger);
      break;
    case stWeekCommand.data.name:
      await handleStWeek(interaction, service, scheduler, config, logger);
      break;
    case stNominateCommand.data.name:
      await handleStNominate(interaction, service, logger);
      break;
    case stPollCommand.data.name:
      await handleStPoll(interaction, service, config, logger);
      break;
    case stRatingsCommand.data.name:
      await handleStRatings(interaction, service, config, logger);
      break;
    case stHelpCommand.data.name:
      await handleStHelp(interaction, logger);
      break;
    case weekStartCommand.data.name:
      await handleWeekStart(interaction, service, scheduler, config, logger);
      break;
  }
}

// ============ PING ============

async function handlePing(interaction: ChatInputCommandInteraction, logger: Logger): Promise<void> {
  try {
    await interaction.reply({ content: 'Pong! 🎵 Sidetrack is online.', ephemeral: true });
  } catch (error) {
    logger.error('Failed to respond to /ping.', {
      error: error instanceof Error ? error.message : String(error),
    });
  }
}

// ============ ST-HELP ============

async function handleStHelp(interaction: ChatInputCommandInteraction, logger: Logger): Promise<void> {
  try {
    const embed = createBaseEmbed()
      .setColor(BRAND_COLORS.info)
      .setTitle('🎵 Sidetrack Club — Help')
      .setDescription(
        "Welcome to Sidetrack Club! Here's how our weekly album club works:",
      )
      .addFields(
        {
          name: '📅 Weekly Flow',
          value: [
            '1️⃣ **Nominations** — Members nominate albums',
            '2️⃣ **Voting** — Vote for your 1st & 2nd choice',
            '3️⃣ **Winner** — Album with most points wins',
            '4️⃣ **Listen & Rate** — Everyone listens and rates',
          ].join('\n'),
          inline: false,
        },
        {
          name: '🎹 Commands',
          value: [
            '`/st-nominate` — Nominate an album',
            '`/st-week overview` — See current week status',
            '`/st-ratings summary` — View rating stats',
            '`/st-help` — This help message',
          ].join('\n'),
          inline: true,
        },
        {
          name: '🔐 Admin Commands',
          value: [
            '`/st-week start` — Start a new week',
            '`/st-poll open` — Open voting',
            '`/st-poll close` — Close voting',
            '`/st-ratings open` — Open ratings',
          ].join('\n'),
          inline: true,
        },
        {
          name: '🗳️ Voting System',
          value: '• 1st choice = 2 points\n• 2nd choice = 1 point\n• Highest score wins!',
          inline: false,
        },
      )
      .setFooter({ text: 'Happy listening! 🎧' });

    await interaction.reply({ embeds: [embed], ephemeral: true });
  } catch (error) {
    logger.error('Failed to respond to /st-help.', {
      error: error instanceof Error ? error.message : String(error),
    });
  }
}

// ============ ST-WEEK ============

async function handleStWeek(
  interaction: ChatInputCommandInteraction,
  service: ClubSyncService,
  scheduler: ReminderScheduler,
  config: BotConfig,
  logger: Logger,
): Promise<void> {
  const subcommand = interaction.options.getSubcommand();

  switch (subcommand) {
    case 'start':
      await handleWeekStart(interaction, service, scheduler, config, logger);
      break;
    case 'overview':
      await handleWeekOverview(interaction, service, logger);
      break;
  }
}

async function handleWeekOverview(
  interaction: ChatInputCommandInteraction,
  service: ClubSyncService,
  logger: Logger,
): Promise<void> {
  await interaction.deferReply({ ephemeral: false });

  try {
    const weekId = interaction.options.getString('week_id', false);
    let week: WeekDetail;

    if (weekId) {
      week = await service.getClient().getWeek(weekId);
    } else {
      const weeks = await service.getClient().listWeeks({ has_winner: false });
      if (weeks.length === 0) {
        await interaction.editReply('No active weeks found. Ask an admin to start a new week with `/st-week start`.');
        return;
      }
      week = weeks[0];
    }

    const embed = buildWeekOverviewEmbed({ week });
    const buttons = buildWeekOverviewButtons(week.id);

    await interaction.editReply({ embeds: [embed], components: [buttons] });
  } catch (error) {
    logger.error('Failed to show week overview.', {
      error: error instanceof Error ? error.message : String(error),
    });
    await interaction.editReply('❌ Failed to fetch week information. Please try again.');
  }
}

// ============ ST-NOMINATE ============

async function handleStNominate(
  interaction: ChatInputCommandInteraction,
  service: ClubSyncService,
  logger: Logger,
): Promise<void> {
  try {
    const weekId = interaction.options.getString('week_id', false);
    let targetWeekId: string;

    if (weekId) {
      targetWeekId = weekId;
    } else {
      const weeks = await service.getClient().listWeeks({ has_winner: false });
      if (weeks.length === 0) {
        await interaction.reply({
          content: 'No active weeks found. Wait for an admin to start a new week.',
          ephemeral: true,
        });
        return;
      }
      targetWeekId = weeks[0].id;
    }

    const modal = buildNominationModal(targetWeekId);
    await interaction.showModal(modal);
  } catch (error) {
    logger.error('Failed to show nomination modal.', {
      error: error instanceof Error ? error.message : String(error),
    });
    await interaction.reply({
      content: '❌ Failed to open nomination form. Please try again.',
      ephemeral: true,
    });
  }
}

// ============ ST-POLL ============

async function handleStPoll(
  interaction: ChatInputCommandInteraction,
  service: ClubSyncService,
  config: BotConfig,
  logger: Logger,
): Promise<void> {
  const subcommand = interaction.options.getSubcommand();

  switch (subcommand) {
    case 'open':
      await handlePollOpen(interaction, service, config, logger);
      break;
    case 'close':
      await handlePollClose(interaction, service, config, logger);
      break;
  }
}

async function handlePollOpen(
  interaction: ChatInputCommandInteraction,
  service: ClubSyncService,
  config: BotConfig,
  logger: Logger,
): Promise<void> {
  await interaction.deferReply({ ephemeral: false });

  if (!isAdmin(interaction, config)) {
    await interaction.editReply('❌ You need admin permissions to open a poll.');
    return;
  }

  try {
    const weekId = interaction.options.getString('week_id', false);
    let week: WeekDetail;

    if (weekId) {
      week = await service.getClient().getWeek(weekId);
    } else {
      const weeks = await service.getClient().listWeeks({ has_winner: false });
      if (weeks.length === 0) {
        await interaction.editReply('No active weeks found.');
        return;
      }
      week = weeks[0];
    }

    if (week.nominations.length === 0) {
      await interaction.editReply('❌ Cannot open poll: no nominations yet.');
      return;
    }

    // Build album map for display
    const albums = new Map<string, AlbumRead>();
    const nominatorNames = new Map<string, string>();

    // Populate nominator names from Discord
    for (const nom of week.nominations) {
      try {
        const member = await interaction.guild?.members.fetch(nom.user_id).catch(() => null);
        if (member) {
          nominatorNames.set(nom.user_id, member.displayName);
        }
      } catch {
        // Skip if we can't fetch
      }
    }

    const embed = buildPollOverviewEmbed({
      week,
      nominations: week.nominations,
      albums,
      nominatorNames,
    });
    const button = buildPollOpenBallotButton(week.id);

    await interaction.editReply({ embeds: [embed], components: [button] });
    logger.info('Poll opened.', { week_id: week.id });
  } catch (error) {
    logger.error('Failed to open poll.', {
      error: error instanceof Error ? error.message : String(error),
    });
    await interaction.editReply('❌ Failed to open poll. Please try again.');
  }
}

async function handlePollClose(
  interaction: ChatInputCommandInteraction,
  service: ClubSyncService,
  config: BotConfig,
  logger: Logger,
): Promise<void> {
  await interaction.deferReply({ ephemeral: false });

  if (!isAdmin(interaction, config)) {
    await interaction.editReply('❌ You need admin permissions to close a poll.');
    return;
  }

  try {
    const weekId = interaction.options.getString('week_id', false);
    let week: WeekDetail;

    if (weekId) {
      week = await service.getClient().getWeek(weekId);
    } else {
      const weeks = await service.getClient().listWeeks({ has_winner: false });
      if (weeks.length === 0) {
        await interaction.editReply('No active weeks found.');
        return;
      }
      week = weeks[0];
    }

    // Sort nominations by vote points
    const rankedNominations = [...week.nominations].sort((a, b) => {
      const aPoints = a.vote_summary?.points ?? 0;
      const bPoints = b.vote_summary?.points ?? 0;
      if (bPoints !== aPoints) return bPoints - aPoints;
      // Tiebreaker: most 1st place votes
      const aFirst = a.vote_summary?.first_place ?? 0;
      const bFirst = b.vote_summary?.first_place ?? 0;
      return bFirst - aFirst;
    });

    if (rankedNominations.length === 0) {
      await interaction.editReply('❌ No nominations to determine a winner.');
      return;
    }

    const winner = rankedNominations[0];
    const albums = new Map<string, AlbumRead>();
    const nominatorNames = new Map<string, string>();

    // Update week with winner
    await service.getClient().updateWeek(week.id, { winner_album_id: winner.album_id });

    // Fetch updated week
    week = await service.getClient().getWeek(week.id);

    // Build results embed
    const resultsEmbed = buildPollResultsEmbed({
      week,
      rankedNominations,
      albums,
      nominatorNames,
    });

    // Build winner embed
    const winnerEmbed = buildWinnerEmbed({
      week,
      winner,
      album: null,
      nominatorName: nominatorNames.get(winner.user_id),
    });

    const ratingsButton = buildOpenRatingsButton(week.id);

    await interaction.editReply({
      embeds: [winnerEmbed, resultsEmbed],
      components: [ratingsButton],
    });

    logger.info('Poll closed and winner announced.', { week_id: week.id, winner_id: winner.id });
  } catch (error) {
    logger.error('Failed to close poll.', {
      error: error instanceof Error ? error.message : String(error),
    });
    await interaction.editReply('❌ Failed to close poll. Please try again.');
  }
}

// ============ ST-RATINGS ============

async function handleStRatings(
  interaction: ChatInputCommandInteraction,
  service: ClubSyncService,
  config: BotConfig,
  logger: Logger,
): Promise<void> {
  const subcommand = interaction.options.getSubcommand();

  switch (subcommand) {
    case 'open':
      await handleRatingsOpen(interaction, service, config, logger);
      break;
    case 'summary':
      await handleRatingsSummary(interaction, service, logger);
      break;
  }
}

async function handleRatingsOpen(
  interaction: ChatInputCommandInteraction,
  service: ClubSyncService,
  config: BotConfig,
  logger: Logger,
): Promise<void> {
  await interaction.deferReply({ ephemeral: false });

  if (!isAdmin(interaction, config)) {
    await interaction.editReply('❌ You need admin permissions to open ratings.');
    return;
  }

  try {
    const weekId = interaction.options.getString('week_id', false);
    let week: WeekDetail;

    if (weekId) {
      week = await service.getClient().getWeek(weekId);
    } else {
      const weeks = await service.getClient().listWeeks();
      const withWinner = weeks.filter((w) => w.winner_album_id);
      if (withWinner.length === 0) {
        await interaction.editReply('No weeks with a winner found. Close a poll first.');
        return;
      }
      week = withWinner[0];
    }

    const embed = buildRatingsCallEmbed({ week, album: null });
    const button = buildRateAlbumButton(week.id);

    await interaction.editReply({ embeds: [embed], components: [button] });
    logger.info('Ratings opened.', { week_id: week.id });
  } catch (error) {
    logger.error('Failed to open ratings.', {
      error: error instanceof Error ? error.message : String(error),
    });
    await interaction.editReply('❌ Failed to open ratings. Please try again.');
  }
}

async function handleRatingsSummary(
  interaction: ChatInputCommandInteraction,
  service: ClubSyncService,
  logger: Logger,
): Promise<void> {
  await interaction.deferReply({ ephemeral: false });

  try {
    const weekId = interaction.options.getString('week_id', false);
    let week: WeekDetail;

    if (weekId) {
      week = await service.getClient().getWeek(weekId);
    } else {
      const weeks = await service.getClient().listWeeks();
      const withWinner = weeks.filter((w) => w.winner_album_id);
      if (withWinner.length === 0) {
        await interaction.editReply('No weeks with a winner found.');
        return;
      }
      week = withWinner[0];
    }

    const summary = await service.getClient().getWeekRatingSummary(week.id, { include_histogram: true });

    const embed = buildRatingsSummaryEmbed({
      week,
      summary,
      album: null,
    });

    await interaction.editReply({ embeds: [embed] });
  } catch (error) {
    logger.error('Failed to show ratings summary.', {
      error: error instanceof Error ? error.message : String(error),
    });
    await interaction.editReply('❌ Failed to fetch ratings summary. Please try again.');
  }
}

// ============ BUTTON HANDLERS ============

async function handleButtonInteraction(
  interaction: ButtonInteraction,
  service: ClubSyncService,
  config: BotConfig,
  logger: Logger,
): Promise<void> {
  const [namespace, action, id] = interaction.customId.split(':');

  switch (namespace) {
    case 'week':
      if (action === 'nominate') {
        const modal = buildNominationModal(id);
        await interaction.showModal(modal);
      } else if (action === 'refresh') {
        await handleWeekRefresh(interaction, service, id, logger);
      }
      break;

    case 'poll':
      if (action === 'open') {
        await handleBallotOpen(interaction, service, id, logger);
      } else if (action === 'submit') {
        await handleBallotSubmit(interaction, service, id, logger);
      }
      break;

    case 'ratings':
      if (action === 'open') {
        await handleRatingsOpenButton(interaction, service, config, id, logger);
      } else if (action === 'rate') {
        const modal = buildRatingModal(id);
        await interaction.showModal(modal);
      }
      break;
  }
}

async function handleWeekRefresh(
  interaction: ButtonInteraction,
  service: ClubSyncService,
  weekId: string,
  logger: Logger,
): Promise<void> {
  await interaction.deferUpdate();

  try {
    const week = await service.getClient().getWeek(weekId);
    const embed = buildWeekOverviewEmbed({ week });
    const buttons = buildWeekOverviewButtons(week.id);

    await interaction.editReply({ embeds: [embed], components: [buttons] });
  } catch (error) {
    logger.error('Failed to refresh week.', {
      error: error instanceof Error ? error.message : String(error),
    });
  }
}

async function handleBallotOpen(
  interaction: ButtonInteraction,
  service: ClubSyncService,
  weekId: string,
  logger: Logger,
): Promise<void> {
  try {
    const week = await service.getClient().getWeek(weekId);

    if (week.nominations.length === 0) {
      await interaction.reply({
        content: '❌ No nominations available for voting.',
        ephemeral: true,
      });
      return;
    }

    // Initialize session
    const sessionKey = `${interaction.user.id}:${weekId}`;
    ballotSessions.set(sessionKey, {});

    const selectMenus = buildBallotSelectMenus(weekId, week.nominations);
    const submitButton = buildBallotSubmitButton(weekId);

    await interaction.reply({
      content: '🗳️ **Your Ballot**\nSelect your 1st and 2nd choice below, then click Submit.',
      components: [...selectMenus, submitButton],
      ephemeral: true,
    });
  } catch (error) {
    logger.error('Failed to open ballot.', {
      error: error instanceof Error ? error.message : String(error),
    });
    await interaction.reply({
      content: '❌ Failed to open ballot. Please try again.',
      ephemeral: true,
    });
  }
}

async function handleBallotSubmit(
  interaction: ButtonInteraction,
  service: ClubSyncService,
  weekId: string,
  logger: Logger,
): Promise<void> {
  await interaction.deferUpdate();

  const sessionKey = `${interaction.user.id}:${weekId}`;
  const session = ballotSessions.get(sessionKey);

  if (!session?.firstChoice) {
    await interaction.followUp({
      content: '❌ Please select at least your 1st choice before submitting.',
      ephemeral: true,
    });
    return;
  }

  if (session.firstChoice === session.secondChoice) {
    await interaction.followUp({
      content: '❌ Your 1st and 2nd choice cannot be the same.',
      ephemeral: true,
    });
    return;
  }

  try {
    // Ensure user exists
    const user = await service.ensureDiscordUser(
      interaction.user.id,
      interaction.user.displayName || interaction.user.username,
    );

    // Submit 1st choice vote (rank 1 = 2 points)
    const firstVote: VoteCreate = {
      week_id: weekId,
      nomination_id: session.firstChoice,
      user_id: user.id,
      rank: 1,
    };
    await service.recordVote(weekId, firstVote);

    // Submit 2nd choice vote if provided (rank 2 = 1 point)
    if (session.secondChoice) {
      const secondVote: VoteCreate = {
        week_id: weekId,
        nomination_id: session.secondChoice,
        user_id: user.id,
        rank: 2,
      };
      await service.recordVote(weekId, secondVote);
    }

    // Clear session
    ballotSessions.delete(sessionKey);

    await interaction.editReply({
      content: '✅ **Ballot submitted!**\nYour votes have been recorded. Thanks for voting!',
      components: [],
    });

    logger.info('Ballot submitted.', {
      user_id: user.id,
      week_id: weekId,
      first: session.firstChoice,
      second: session.secondChoice,
    });
  } catch (error) {
    logger.error('Failed to submit ballot.', {
      error: error instanceof Error ? error.message : String(error),
    });
    await interaction.followUp({
      content: '❌ Failed to submit your ballot. Please try again.',
      ephemeral: true,
    });
  }
}

async function handleRatingsOpenButton(
  interaction: ButtonInteraction,
  service: ClubSyncService,
  config: BotConfig,
  weekId: string,
  logger: Logger,
): Promise<void> {
  try {
    const week = await service.getClient().getWeek(weekId);
    const embed = buildRatingsCallEmbed({ week, album: null });
    const button = buildRateAlbumButton(week.id);

    await interaction.reply({ embeds: [embed], components: [button] });
  } catch (error) {
    logger.error('Failed to open ratings via button.', {
      error: error instanceof Error ? error.message : String(error),
    });
    await interaction.reply({
      content: '❌ Failed to open ratings. Please try again.',
      ephemeral: true,
    });
  }
}

// ============ SELECT MENU HANDLERS ============

async function handleSelectMenuInteraction(
  interaction: StringSelectMenuInteraction,
  logger: Logger,
): Promise<void> {
  const [namespace, choice, weekId] = interaction.customId.split(':');

  if (namespace !== 'poll') return;

  const sessionKey = `${interaction.user.id}:${weekId}`;
  let session = ballotSessions.get(sessionKey);

  if (!session) {
    session = {};
    ballotSessions.set(sessionKey, session);
  }

  const selectedValue = interaction.values[0];

  if (choice === 'first') {
    session.firstChoice = selectedValue;
  } else if (choice === 'second') {
    session.secondChoice = selectedValue;
  }

  await interaction.deferUpdate();
  logger.debug('Ballot selection updated.', { choice, selectedValue });
}

// ============ MODAL HANDLERS ============

async function handleModalSubmit(
  interaction: ModalSubmitInteraction,
  service: ClubSyncService,
  config: BotConfig,
  logger: Logger,
): Promise<void> {
  const [namespace, action, id] = interaction.customId.split(':');

  switch (namespace) {
    case 'nomination':
      if (action === 'submit') {
        await handleNominationSubmit(interaction, service, id, logger);
      }
      break;

    case 'rating':
      if (action === 'submit') {
        await handleRatingSubmit(interaction, service, id, logger);
      }
      break;
  }
}

async function handleNominationSubmit(
  interaction: ModalSubmitInteraction,
  service: ClubSyncService,
  weekId: string,
  logger: Logger,
): Promise<void> {
  await interaction.deferReply({ ephemeral: true });

  try {
    const albumTitle = interaction.fields.getTextInputValue('album');
    const artistName = interaction.fields.getTextInputValue('artist');
    const pitch = interaction.fields.getTextInputValue('pitch');
    const link = interaction.fields.getTextInputValue('link') || undefined;
    const tagsRaw = interaction.fields.getTextInputValue('tags') || '';

    // Parse tags
    const tagParts = tagsRaw.split('/').map((t) => t.trim());
    const genre = tagParts[0] || undefined;
    const decade = tagParts[1] || undefined;
    const country = tagParts[2] || undefined;

    // Ensure user exists
    const user = await service.ensureDiscordUser(
      interaction.user.id,
      interaction.user.displayName || interaction.user.username,
    );

    // Create or find album
    const album = await service.ensureAlbumFromForm({
      title: albumTitle,
      artist_name: artistName,
    });

    // Create nomination
    const nomination: NominationCreate = {
      week_id: weekId,
      user_id: user.id,
      album_id: album.id,
      pitch,
      pitch_track_url: link,
      genre,
      decade,
      country,
    };

    const created = await service.recordNomination(weekId, nomination);

    // Send confirmation
    const confirmEmbed = buildNominationConfirmEmbed(albumTitle, artistName);
    await interaction.editReply({ embeds: [confirmEmbed] });

    // Post nomination card in the thread if possible
    if (interaction.channel && interaction.channel.isThread()) {
      const nominationEmbed = buildNominationEmbed({
        nomination: created,
        album,
        nominatorName: interaction.user.displayName || interaction.user.username,
      });
      await interaction.channel.send({ embeds: [nominationEmbed] });
    }

    logger.info('Nomination submitted via modal.', {
      nomination_id: created.id,
      week_id: weekId,
      album: albumTitle,
    });
  } catch (error) {
    logger.error('Failed to submit nomination.', {
      error: error instanceof Error ? error.message : String(error),
    });
    await interaction.editReply('❌ Failed to submit your nomination. Please try again.');
  }
}

async function handleRatingSubmit(
  interaction: ModalSubmitInteraction,
  service: ClubSyncService,
  weekId: string,
  logger: Logger,
): Promise<void> {
  await interaction.deferReply({ ephemeral: true });

  try {
    const scoreRaw = interaction.fields.getTextInputValue('score');
    const favoriteTrack = interaction.fields.getTextInputValue('favorite_track') || undefined;
    const review = interaction.fields.getTextInputValue('review') || undefined;

    // Parse and validate score
    const score = parseFloat(scoreRaw);
    if (isNaN(score) || score < 1.0 || score > 5.0) {
      await interaction.editReply('❌ Invalid score. Please enter a value between 1.0 and 5.0.');
      return;
    }

    // Round to nearest 0.5
    const roundedScore = Math.round(score * 2) / 2;

    // Get week to find winner album
    const week = await service.getClient().getWeek(weekId);
    if (!week.winner_album_id) {
      await interaction.editReply('❌ This week does not have a winning album yet.');
      return;
    }

    // Find the winning nomination
    const winnerNomination = week.nominations.find((n) => n.album_id === week.winner_album_id);

    // Ensure user exists
    const user = await service.ensureDiscordUser(
      interaction.user.id,
      interaction.user.displayName || interaction.user.username,
    );

    // Create rating
    const rating: RatingCreate = {
      week_id: weekId,
      user_id: user.id,
      album_id: week.winner_album_id,
      nomination_id: winnerNomination?.id,
      value: roundedScore,
      favorite_track: favoriteTrack,
      review,
    };

    await service.recordRating(weekId, rating);

    // Send confirmation
    const confirmEmbed = buildRatingConfirmEmbed(roundedScore, 'the winning album');
    await interaction.editReply({ embeds: [confirmEmbed] });

    logger.info('Rating submitted via modal.', {
      week_id: weekId,
      user_id: user.id,
      score: roundedScore,
    });
  } catch (error) {
    logger.error('Failed to submit rating.', {
      error: error instanceof Error ? error.message : String(error),
    });
    await interaction.editReply('❌ Failed to submit your rating. Please try again.');
  }
}

// ============ LEGACY WEEK-START HANDLER ============

async function handleWeekStart(
  interaction: ChatInputCommandInteraction,
  service: ClubSyncService,
  scheduler: ReminderScheduler,
  config: BotConfig,
  logger: Logger,
): Promise<void> {
  await interaction.deferReply({ ephemeral: true });

  if (!interaction.guildId || !interaction.guild) {
    await interaction.editReply('This command can only be used inside a guild.');
    return;
  }

  if (!isAdmin(interaction, config)) {
    await interaction.editReply('❌ You need Manage Server or an admin role to start a week.');
    return;
  }

  const nominationsForumId = config.club.nominationsForumId;
  if (!nominationsForumId) {
    await interaction.editReply('❌ Missing nominations forum ID. Set SIDETRACK_NOMINATIONS_FORUM_ID in env.');
    return;
  }

  const label = interaction.options.getString('label', true);
  const weekNumber = interaction.options.getInteger('week_number', false) ?? undefined;
  const nominationsCloseAt = parseDateOption(interaction, 'nominations_close_at');
  const pollCloseAt = parseDateOption(interaction, 'poll_close_at');
  const discussionAt = parseDateOption(interaction, 'discussion_at');
  if (nominationsCloseAt instanceof Error) {
    await interaction.editReply(nominationsCloseAt.message);
    return;
  }
  if (pollCloseAt instanceof Error) {
    await interaction.editReply(pollCloseAt.message);
    return;
  }
  if (discussionAt instanceof Error) {
    await interaction.editReply(discussionAt.message);
    return;
  }

  try {
    const weekPayload: WeekCreate = {
      label,
      week_number: weekNumber,
      nominations_close_at: nominationsCloseAt?.toISOString(),
      poll_close_at: pollCloseAt?.toISOString(),
      discussion_at: discussionAt?.toISOString(),
    };
    const updatePayload: WeekUpdate = {};
    if (nominationsCloseAt) updatePayload.nominations_close_at = nominationsCloseAt.toISOString();
    if (pollCloseAt) updatePayload.poll_close_at = pollCloseAt.toISOString();
    if (discussionAt) updatePayload.discussion_at = discussionAt.toISOString();

    const week = await service.ensureWeek({
      week: weekPayload,
      update: Object.keys(updatePayload).length > 0 ? updatePayload : undefined,
    });

    const existingThreadId = week.nominations_thread_id ? String(week.nominations_thread_id) : undefined;
    if (existingThreadId) {
      const existingThread = await interaction.guild.channels.fetch(existingThreadId).catch(() => null);
      if (existingThread && existingThread.isThread()) {
        await interaction.editReply(
          [
            `Week already has a nominations thread: <#${existingThread.id}>`,
            `Label: **${week.label}**${week.week_number ? ` (#${week.week_number})` : ''}`,
          ].join('\n'),
        );
        return;
      }
    }

    const forum = await interaction.guild.channels.fetch(nominationsForumId);
    if (!forum || forum.type !== ChannelType.GuildForum) {
      await interaction.editReply('❌ Configured nominations forum ID is not a forum channel.');
      return;
    }

    // Create thread with overview embed
    const overviewEmbed = buildWeekOverviewEmbed({ week });
    const overviewButtons = buildWeekOverviewButtons(week.id);

    const thread = await forum.threads.create({
      name: buildNominationsThreadName(week.label, week.week_number),
      message: {
        content: buildNominationsPrompt(week.label),
        embeds: [overviewEmbed],
        components: [overviewButtons],
      },
    });

    const starterMessage = await thread.fetchStarterMessage().catch(() => null);
    if (starterMessage && !starterMessage.pinned) {
      await starterMessage.pin().catch((error) => logger.warn('Failed to pin nominations prompt.', { error }));
    }

    await service.attachNominationsThread(week.id, thread.id);

    await interaction.editReply(
      [
        `✅ Week created: **${week.label}**${week.week_number ? ` (#${week.week_number})` : ''}`,
        `📋 Nominations thread: <#${thread.id}>`,
      ].join('\n'),
    );

    scheduler.scheduleForWeek(week);
    logger.info('Week started.', { week_id: week.id, thread_id: thread.id });
  } catch (error) {
    logger.error('Failed to start week.', {
      error: error instanceof Error ? error.message : String(error),
    });
    await interaction.editReply('❌ Failed to create week. Please try again.');
  }
}

// ============ UTILITY FUNCTIONS ============

function parseDateOption(
  interaction: ChatInputCommandInteraction,
  optionName: string,
): Date | Error | undefined {
  const raw = interaction.options.getString(optionName, false);
  if (!raw) return undefined;
  const parsed = new Date(raw);
  if (Number.isNaN(parsed.getTime())) {
    const label = optionName.replace(/_/g, ' ');
    return new Error(`Could not parse ${label}. Use an ISO timestamp like 2025-11-24T18:00Z.`);
  }
  return parsed;
}

function isAdmin(interaction: ChatInputCommandInteraction | ButtonInteraction, config: BotConfig): boolean {
  if ('memberPermissions' in interaction && interaction.memberPermissions?.has(PermissionFlagsBits.ManageGuild)) {
    return true;
  }

  const roleIds = config.club.adminRoleIds;
  if (!roleIds || roleIds.length === 0) return false;

  const member = interaction.member;
  if (!member) return false;

  const roles = (member as GuildMember).roles ?? (member as APIInteractionGuildMember).roles;
  if (!roles) return false;

  if (roles instanceof GuildMemberRoleManager) {
    return roleIds.some((roleId) => roles.cache.has(roleId));
  }
  if (Array.isArray(roles)) {
    const roleList = roles as string[];
    return roleIds.some((roleId) => roleList.includes(roleId));
  }

  return false;
}

function buildNominationsThreadName(label: string, weekNumber?: number | null): string {
  if (weekNumber) {
    return `WEEK ${String(weekNumber).padStart(3, '0')} — NOMINATIONS`;
  }
  return `${label} — NOMINATIONS`;
}

function buildNominationsPrompt(label: string): string {
  return [
    `**${label} — Nominations**`,
    '',
    '🎵 Click the **Nominate an Album** button below to submit your pick!',
    '',
    'Or paste this mini-form as a message:',
    '```',
    'Album — Artist (Year)',
    'Why?: <your pitch>',
    'Pitch track: <Spotify/YouTube link>',
    'Tags: <genre / decade / country>',
    '```',
  ].join('\n');
}
