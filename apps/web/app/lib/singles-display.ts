import type { SinglesSessionRead } from '@sidetrack/api-client';

export function singlesDate(value: string | null): string {
  if (!value) return 'Date unavailable';
  return new Intl.DateTimeFormat('en-US', {
    timeZone: 'UTC',
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  }).format(new Date(`${value}T12:00:00Z`));
}

export function sessionTitle(session: SinglesSessionRead) {
  return session.week_number == null ? 'Singles Night' : `Singles Night ${session.week_number}`;
}
