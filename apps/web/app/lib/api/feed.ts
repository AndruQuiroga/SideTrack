import { getApiBaseUrl } from '../config';

export type FeedEventType = 'rating' | 'listen' | 'club' | 'follow';

export interface FeedItem {
  id: string;
  type: FeedEventType;
  actor: string;
  actor_id?: string | null;
  action: string;
  target?: string | null;
  target_link?: string | null;
  rating?: number | null;
  timestamp: string;
  metadata?: Record<string, unknown> | null;
}

export async function fetchFeed(userId?: string, limit: number = 20): Promise<FeedItem[]> {
  const params = new URLSearchParams();
  if (userId) params.set('user_id', userId);
  params.set('limit', String(limit));

  const res = await fetch(`${getApiBaseUrl()}/feed?${params.toString()}`, {
    cache: 'no-store',
  });
  if (!res.ok) throw new Error(`Feed failed with status ${res.status}`);
  return (await res.json()) as FeedItem[];
}
