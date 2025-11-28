import { Client, ChannelType, TextChannel, ThreadChannel } from 'discord.js';
import { WeekDetail } from '@sidetrack/shared';

import { ClubSyncService } from './clubService';
import { Logger } from './logger';

const ONE_HOUR_MS = 60 * 60 * 1000;

interface ScheduledJob {
  timeoutId: NodeJS.Timeout;
  weekId: string;
  description: string;
}

export class ReminderScheduler {
  private jobs: ScheduledJob[] = [];

  constructor(
    private readonly client: Client,
    private readonly service: ClubSyncService,
    private readonly logger: Logger,
  ) {}

  scheduleWeeks(weeks: WeekDetail[]): void {
    weeks.forEach((week) => this.scheduleForWeek(week));
  }

  scheduleForWeek(week: WeekDetail): void {
    if (!week.nominations_thread_id || !week.nominations_close_at) return;

    const closeAt = new Date(week.nominations_close_at).getTime();
    const reminderAt = closeAt - ONE_HOUR_MS;

    if (reminderAt > Date.now()) {
      this.enqueue(reminderAt - Date.now(), week, 'nominations-1h-reminder', () =>
        this.sendReminder(
          String(week.nominations_thread_id),
          `⏰ Nominations close in 1 hour for **${week.label}**. Submit your pick!`,
        ),
      );
    }

    if (closeAt > Date.now()) {
      this.enqueue(closeAt - Date.now(), week, 'nominations-close', () =>
        this.sendReminder(
          String(week.nominations_thread_id),
          `🔒 Nominations are now closed for **${week.label}**.`,
        ),
      );
    }
  }

  private enqueue(delayMs: number, week: WeekDetail, description: string, fn: () => Promise<void>): void {
    const timeoutId = setTimeout(async () => {
      try {
        await fn();
      } catch (error) {
        this.logger.warn('Scheduled reminder failed.', {
          week_id: week.id,
          description,
          error: error instanceof Error ? error.message : String(error),
        });
      }
    }, delayMs);

    this.jobs.push({ timeoutId, weekId: week.id, description });
    this.logger.info('Scheduled reminder.', { week_id: week.id, description, delay_ms: delayMs });
  }

  private async sendReminder(threadId: string, message: string): Promise<void> {
    const channel = await this.client.channels.fetch(threadId);
    if (!channel) {
      this.logger.warn('Reminder target thread not found.', { threadId });
      return;
    }

    if (channel.type === ChannelType.PublicThread || channel.type === ChannelType.PrivateThread) {
      await (channel as ThreadChannel).send(message);
      return;
    }

    if (channel.isTextBased()) {
      await (channel as TextChannel).send(message);
      return;
    }

    this.logger.warn('Reminder target not text-based.', { threadId });
  }
}
