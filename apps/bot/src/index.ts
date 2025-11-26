import { describeProject } from '@sidetrack/shared';

export function startBot(): void {
  console.log('Bootstrapping Discord bot with shared context:', describeProject());
}

startBot();
