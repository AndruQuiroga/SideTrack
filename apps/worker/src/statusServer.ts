import http from 'http';

import { SyncCoordinator, SyncStatus } from './sync';

export class StatusServer {
  private readonly server: http.Server;
  private readonly port: number;

  constructor(coordinator: SyncCoordinator, port = Number(process.env.WORKER_STATUS_PORT ?? '8700')) {
    this.port = port;
    this.server = http.createServer((_, res) => {
      const status: SyncStatus = coordinator.status();
      const body = JSON.stringify(status, null, 2);
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(body);
    });
  }

  start(): void {
    this.server.listen(this.port, () => {
      console.log(`[worker] status server running on :${this.port}`);
    });
  }
}
