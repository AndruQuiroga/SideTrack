import {
  APIInteractionGuildMember,
  ChannelType,
  ChatInputCommandInteraction,
  Client,
  GuildMember,
  GuildMemberRoleManager,
  Interaction,
  PermissionFlagsBits,
} from 'discord.js';

import { Logger } from '../logger';
import { ClubSyncService } from '../clubService';
import { BotConfig } from '../config';
import { WeekCreate, WeekUpdate } from '@sidetrack/shared';
import { pingCommand, weekStartCommand } from './commands';
import { ReminderScheduler } from '../scheduler';

export function registerInteractionHandlers(
  client: Client,
  service: ClubSyncService,
  scheduler: ReminderScheduler,
  config: BotConfig,
  logger: Logger,
): void {
  client.on('interactionCreate', async (interaction: Interaction) => {
    if (!interaction.isChatInputCommand()) return;

    switch (interaction.commandName) {
      case pingCommand.data.name:
        await handlePing(interaction, logger);
        break;
      case weekStartCommand.data.name:
        await handleWeekStart(interaction, service, scheduler, config, logger);
        break;
      default:
        break;
    }
  });
}

async function handlePing(interaction: ChatInputCommandInteraction, logger: Logger): Promise<void> {
  try {
    await interaction.reply({ content: 'Pong! Sidetrack is online.', ephemeral: true });
  } catch (error) {
    logger.error('Failed to respond to /ping.', {
      error: error instanceof Error ? error.message : String(error),
    });
  }
}

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
    await interaction.editReply('You need Manage Server or an admin role to start a week.');
    return;
  }

  const nominationsForumId = config.club.nominationsForumId;
  if (!nominationsForumId) {
    await interaction.editReply('Missing nominations forum ID. Set SIDETRACK_NOMINATIONS_FORUM_ID in env.');
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
    await interaction.editReply('Configured nominations forum ID is not a forum channel.');
    return;
  }

  const thread = await forum.threads.create({
    name: buildNominationsThreadName(week.label, week.week_number),
    message: { content: buildNominationsPrompt(week.label) },
  });

  const starterMessage = await thread.fetchStarterMessage().catch(() => null);
  if (starterMessage && !starterMessage.pinned) {
    await starterMessage.pin().catch((error) => logger.warn('Failed to pin nominations prompt.', { error }));
  }

  await service.attachNominationsThread(week.id, thread.id);

  await interaction.editReply(
    [
      `Week created/updated: **${week.label}**${week.week_number ? ` (#${week.week_number})` : ''}.`,
      `Nominations thread: <#${thread.id}>`,
    ].join('\n'),
  );

  scheduler.scheduleForWeek(week);
}

function parseDateOption(
  interaction: ChatInputCommandInteraction,
  optionName: string,
): Date | Error | undefined {
  const raw = interaction.options.getString(optionName, false);
  if (!raw) return undefined;
  const parsed = new Date(raw);
  if (Number.isNaN(parsed.getTime())) {
    return new Error(`Could not parse ${optionName.replaceAll('_', ' ')}. Use an ISO timestamp like 2025-11-24T18:00Z.`);
  }
  return parsed;
}

function isAdmin(interaction: ChatInputCommandInteraction, config: BotConfig): boolean {
  if (interaction.memberPermissions?.has(PermissionFlagsBits.ManageGuild)) {
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
    return roleIds.some((roleId) => roles.includes(roleId));
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
    'Paste this mini-form as a single message:',
    '',
    'Album — Artist (Year)',
    'Why?: <one or two sentences>',
    'Pitch track (choose one): <Spotify/YouTube link>',
    'Tags (Genre / Decade / Country): <rock / 90s / US>',
  ].join('\n');
}
