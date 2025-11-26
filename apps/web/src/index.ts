import { describeProject } from '@sidetrack/shared';

export function startWebApp(): void {
  console.log('Starting web app with shared context:', describeProject());
}

startWebApp();
