import { SlashCommandBuilder } from 'discord.js';

export const pingCommand = {
  data: new SlashCommandBuilder().setName('ping').setDescription('Check if Sidetrack bot is online'),
};

export type RegisteredCommand = typeof pingCommand;
