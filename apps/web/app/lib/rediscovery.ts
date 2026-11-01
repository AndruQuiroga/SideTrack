import type { ForgottenTrack } from '@sidetrack/api-client';

export const REDISCOVERY_PATH = '/listening/rediscover';

const UUID = /^[a-f\d]{8}-[a-f\d]{4}-[a-f\d]{4}-[a-f\d]{4}-[a-f\d]{12}$/i;

export const REASONS = ['not_a_favourite', 'not_now'] as const;
export type Reason = (typeof REASONS)[number];

export function parseAutoplay(value?: string): boolean {
  return value === '1';
}

/** The page address that keeps the autoplay choice. */
export function rediscoveryHref(autoplay: boolean): string {
  return autoplay ? `${REDISCOVERY_PATH}?autoplay=1` : REDISCOVERY_PATH;
}

const month = (iso: string) =>
  new Intl.DateTimeFormat('en-US', { timeZone: 'UTC', month: 'long', year: 'numeric' }).format(
    new Date(iso),
  );

/** "Played a lot in March 2021": the peak period, never a claim about feelings. */
export function describePeak(track: Pick<ForgottenTrack, 'peak_start' | 'peak_end'>): string {
  const start = month(track.peak_start);
  const end = month(track.peak_end);
  return start === end ? `Played a lot in ${start}` : `Played a lot from ${start} to ${end}`;
}

export type RediscoveryAction =
  | { action: 'dismiss'; trackId: string; reason: Reason; autoplay: boolean }
  | { action: 'restore'; trackId: string; autoplay: boolean }
  | { action: 'restore_all'; autoplay: boolean };

/** Validates a posted form; anything unexpected is null and never reaches the API. */
export function parseRediscoveryForm(form: FormData): RediscoveryAction | null {
  const autoplay = parseAutoplay(String(form.get('autoplay') ?? ''));
  const action = form.get('action');
  if (action === 'restore_all') return { action, autoplay };
  const trackId = form.get('track_id');
  if (typeof trackId !== 'string' || !UUID.test(trackId)) return null;
  if (action === 'restore') return { action, trackId, autoplay };
  const reason = form.get('reason');
  if (action === 'dismiss' && (REASONS as readonly unknown[]).includes(reason)) {
    return { action, trackId, reason: reason as Reason, autoplay };
  }
  return null;
}
