import { REST, Routes } from 'discord.js';
import { SidetrackApiClient } from '@sidetrack/shared';

import { ClubSyncService } from './clubService';
import { loadBotConfig } from './config';
import { createDiscordClient } from './runtime/client';
import { registerInteractionHandlers } from './runtime/handlers';
import { createLogger } from './logger';
import { pingCommand } from './runtime/commands';

export async function startBot(): Promise<void> {
  const config = loadBotConfig();
  const logger = createLogger('startup');
  const client = new SidetrackApiClient({
    baseUrl: config.api.baseUrl,
    authToken: config.api.token,
  });

  const service = new ClubSyncService(client, config, logger);
  const openWeeks = await service.bootstrap();

  const discordClient = createDiscordClient(config.discord.token, logger);
  registerInteractionHandlers(discordClient, logger);

  if (config.discord.clientId && config.discord.guildId) {
    const rest = new REST({ version: '10' }).setToken(config.discord.token);
    await rest.put(Routes.applicationGuildCommands(config.discord.clientId, config.discord.guildId), {
      body: [pingCommand.data.toJSON()],
    });
    logger.info('Registered guild slash commands.', { guildId: config.discord.guildId });
  } else {
    logger.warn('Skipping slash command registration; DISCORD_CLIENT_ID or DISCORD_GUILD_ID missing.');
  }

  await discordClient.login(config.discord.token);

  logger.info('Bot service initialized.', {
    discordTokenLoaded: Boolean(config.discord.token),
    openWeeks: openWeeks.length,
  });
}

startBot().catch((error) => {
  const logger = createLogger('startup');
  logger.error('Bot failed to start.', { error: error instanceof Error ? error.message : String(error) });
  process.exitCode = 1;
});
