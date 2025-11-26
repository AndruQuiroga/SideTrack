import { describeProject } from '@sidetrack/shared';

export function startWorker(): void {
  console.log('Launching background worker with shared context:', describeProject());
}

startWorker();
