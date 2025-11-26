export interface SyncCounters {
  successes: number;
  failures: number;
  deduped: number;
  ingested: number;
  lastSyncAt?: string;
  lastError?: string;
}

export interface MetricsSnapshot {
  syncs: Record<string, SyncCounters>;
}

export class MetricsRegistry {
  private readonly counters: Record<string, SyncCounters> = {};

  recordSuccess(scope: string): void {
    const counter = this.ensure(scope);
    counter.successes += 1;
    counter.lastSyncAt = new Date().toISOString();
  }

  recordError(scope: string, error?: unknown): void {
    const counter = this.ensure(scope);
    counter.failures += 1;
    counter.lastError = error instanceof Error ? error.message : String(error ?? 'unknown');
  }

  recordListenIngest(count: number): void {
    const counter = this.ensure('ingest');
    counter.ingested += count;
    counter.lastSyncAt = new Date().toISOString();
  }

  recordDeduped(): void {
    const counter = this.ensure('ingest');
    counter.deduped += 1;
  }

  snapshot(): MetricsSnapshot {
    return { syncs: this.counters };
  }

  private ensure(scope: string): SyncCounters {
    if (!this.counters[scope]) {
      this.counters[scope] = { successes: 0, failures: 0, deduped: 0, ingested: 0 };
    }
    return this.counters[scope];
  }
}
