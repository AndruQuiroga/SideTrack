import type { Client } from 'discord.js';
import type { ClubSyncService } from './clubService';
import type { Logger } from './logger';
import { NotificationDelivery, PermanentDeliveryError } from './notificationDelivery';

export class ReminderScheduler {
  private delivery: NotificationDelivery;

  constructor(client: Client, service: ClubSyncService, logger: Logger) {
    this.delivery = new NotificationDelivery(
      service.getClient(),
      async (event) => {
        const channel = await client.channels.fetch(event.thread_id);
        if (!channel || !channel.isSendable())
          throw new PermanentDeliveryError('target_unavailable');
        const message = await channel.send(event.message);
        return message.id;
      },
      logger,
    );
  }

  start(): void {
    this.delivery.start();
  }

  async cancelAll(): Promise<void> {
    await this.delivery.stop();
  }
}
