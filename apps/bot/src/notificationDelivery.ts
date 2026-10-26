import type { DeliveryEvent } from '@sidetrack/api-client';
import type { Logger } from './logger';

interface DeliveryApi {
  claimNotifications(): Promise<DeliveryEvent[]>;
  acknowledgeNotification(id: string, token: string, messageId: string): Promise<void>;
  failNotification(
    id: string,
    token: string,
    permanent: boolean,
    retryAfter?: number,
  ): Promise<void>;
}

export class PermanentDeliveryError extends Error {}

/** Polling wakes delivery; Postgres owns every deadline, lease and retry. */
export class NotificationDelivery {
  private api: DeliveryApi;
  private send: (event: DeliveryEvent) => Promise<string>;
  private logger: Logger;
  private timer?: ReturnType<typeof setTimeout>;
  private stopped = true;
  private active?: Promise<void>;

  constructor(api: DeliveryApi, send: (event: DeliveryEvent) => Promise<string>, logger: Logger) {
    this.api = api;
    this.send = send;
    this.logger = logger;
  }

  start(): void {
    if (!this.stopped) return;
    this.stopped = false;
    const tick = async () => {
      this.active = this.deliverOnce();
      await this.active;
      if (!this.stopped) this.timer = setTimeout(() => void tick(), 5000);
    };
    void tick();
  }

  async stop(): Promise<void> {
    this.stopped = true;
    if (this.timer) clearTimeout(this.timer);
    await this.active;
  }

  async deliverOnce(): Promise<void> {
    try {
      const events = await this.api.claimNotifications();
      for (const event of events) {
        if (this.stopped) return;
        let messageId: string;
        try {
          messageId = await this.send(event);
        } catch (error) {
          const info = error as { status?: number; retry_after?: number };
          const permanent =
            error instanceof PermanentDeliveryError ||
            (typeof info?.status === 'number' &&
              info.status >= 400 &&
              info.status < 500 &&
              ![408, 429].includes(info.status));
          const retryAfter = Math.min(300, Math.max(0, Math.ceil(info?.retry_after ?? 0)));
          await this.api.failNotification(event.id, event.lease_token, permanent, retryAfter);
          continue;
        }
        try {
          await this.api.acknowledgeNotification(event.id, event.lease_token, messageId);
        } catch {
          // Sending succeeded. Leave the lease for recovery; never report a send failure.
          this.logger.warn('Notification acknowledgment failed; lease will recover.', {
            id: event.id,
          });
        }
      }
    } catch {
      this.logger.warn('Notification delivery unavailable; polling will retry.');
    }
  }
}
