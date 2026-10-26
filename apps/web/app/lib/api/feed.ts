/** Server-only club activity feed for the session user. */
import { apiRequest } from '../server-api';

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

export async function fetchFeed(sessionUserId: string, limit: number = 20): Promise<FeedItem[]> {
  return apiRequest<FeedItem[]>(sessionUserId, `/feed?limit=${limit}`);
}
