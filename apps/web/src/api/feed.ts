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

// Fallback demo feed for development/offline
export function getDemoFeed(): FeedItem[] {
  const now = new Date();
  return [
    {
      id: 'demo-1',
      type: 'rating',
      actor: 'lydia',
      action: 'rated',
      target: 'Spirit of Eden — Talk Talk',
      target_link: '/club/weeks/week-demo-3',
      rating: 4.5,
      timestamp: new Date(now.getTime() - 5 * 60 * 1000).toISOString(),
    },
    {
      id: 'demo-2',
      type: 'listen',
      actor: 'arden',
      action: 'is now playing',
      target: 'Open My Eyes · Yeule',
      timestamp: new Date(now.getTime() - 12 * 60 * 1000).toISOString(),
    },
    {
      id: 'demo-3',
      type: 'club',
      actor: 'bot',
      action: 'announced winner for WEEK 003',
      target: 'Join the ratings thread',
      target_link: '/club/weeks/week-demo-3',
      timestamp: new Date(now.getTime() - 60 * 60 * 1000).toISOString(),
    },
    {
      id: 'demo-4',
      type: 'follow',
      actor: 'demo',
      action: 'followed you back',
      timestamp: new Date(now.getTime() - 2 * 60 * 60 * 1000).toISOString(),
    },
  ];
}

export async function fetchFeedWithFallback(userId?: string, limit: number = 20): Promise<FeedItem[]> {
  try {
    return await fetchFeed(userId, limit);
  } catch (error) {
    console.warn('Falling back to demo feed due to API error', error);
    return getDemoFeed();
  }
}
