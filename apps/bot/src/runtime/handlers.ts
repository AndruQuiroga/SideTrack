import { ChatInputCommandInteraction, Client, Interaction } from 'discord.js';

import { Logger } from '../logger';
import { pingCommand } from './commands';

export function registerInteractionHandlers(client: Client, logger: Logger): void {
  client.on('interactionCreate', async (interaction: Interaction) => {
    if (!interaction.isChatInputCommand()) return;

    switch (interaction.commandName) {
      case pingCommand.data.name:
        await handlePing(interaction, logger);
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
