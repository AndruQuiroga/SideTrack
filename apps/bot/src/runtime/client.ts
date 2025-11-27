import { Client, GatewayIntentBits, Partials } from 'discord.js';

import { Logger } from '../logger';

export function createDiscordClient(token: string, logger: Logger): Client {
  const client = new Client({
    intents: [GatewayIntentBits.Guilds, GatewayIntentBits.GuildMessages, GatewayIntentBits.MessageContent],
    partials: [Partials.Channel],
  });

  client.once('ready', () => {
    logger.info('Discord client is ready.', {
      user: client.user?.tag,
    });
  });

  client.on('error', (error) => {
    logger.error('Discord client error.', { error: error.message });
  });

  return client;
}
