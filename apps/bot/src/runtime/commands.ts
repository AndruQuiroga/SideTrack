import { SlashCommandBuilder } from 'discord.js';

export const pingCommand = {
  data: new SlashCommandBuilder().setName('ping').setDescription('Check if Sidetrack bot is online'),
};

export const weekStartCommand = {
  data: new SlashCommandBuilder()
    .setName('week-start')
    .setDescription('Create a Sidetrack Club week and open the nominations thread')
    .addStringOption((option) =>
      option
        .setName('label')
        .setDescription('Week label, e.g., WEEK 003 [2025-11-24]')
        .setRequired(true),
    )
    .addIntegerOption((option) =>
      option.setName('week_number').setDescription('Numeric week number (optional)').setRequired(false),
    )
    .addStringOption((option) =>
      option
        .setName('nominations_close_at')
        .setDescription('Nominations close time (ISO timestamp, e.g., 2025-11-23T18:00Z)')
        .setRequired(false),
    )
    .addStringOption((option) =>
      option
        .setName('poll_close_at')
        .setDescription('Poll close time (ISO timestamp, e.g., 2025-11-24T18:00Z)')
        .setRequired(false),
    )
    .addStringOption((option) =>
      option
        .setName('discussion_at')
        .setDescription('Discussion time (ISO timestamp, e.g., 2025-11-25T18:00Z)')
        .setRequired(false),
    ),
};

export type RegisteredCommand = typeof pingCommand | typeof weekStartCommand;
