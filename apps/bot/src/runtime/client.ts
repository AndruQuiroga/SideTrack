import { Client, GatewayIntentBits, Partials } from 'discord.js';

import { Logger } from '../logger';

export function createDiscordClient(
  token: string,
  logger: Logger,
  options: { membersIntent?: boolean } = {},
): Client {
  const intents = [
    GatewayIntentBits.Guilds,
    GatewayIntentBits.GuildMessages,
    GatewayIntentBits.MessageContent,
  ];
  // Privileged: must also be enabled for the application in the Discord developer portal.
  if (options.membersIntent) intents.push(GatewayIntentBits.GuildMembers);
  const client = new Client({
    intents,
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
