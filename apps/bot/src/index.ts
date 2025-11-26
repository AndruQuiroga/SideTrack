import { SidetrackApiClient } from '@sidetrack/shared';

import { ClubSyncService } from './clubService';
import { loadBotConfig } from './config';
import { createLogger } from './logger';

export async function startBot(): Promise<void> {
  const config = loadBotConfig();
  const logger = createLogger('startup');
  const client = new SidetrackApiClient({
    baseUrl: config.api.baseUrl,
    authToken: config.api.token,
  });

  const service = new ClubSyncService(client, config, logger);
  const openWeeks = await service.bootstrap();

  logger.info('Bot service initialized.', {
    discordTokenLoaded: Boolean(config.discordToken),
    openWeeks: openWeeks.length,
  });
}

startBot().catch((error) => {
  const logger = createLogger('startup');
  logger.error('Bot failed to start.', { error: error instanceof Error ? error.message : String(error) });
  process.exitCode = 1;
});
