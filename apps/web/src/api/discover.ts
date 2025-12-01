import { getApiBaseUrl } from '../config';

export type SearchResult = {
  users: Array<{ id: string; display_name: string; handle?: string }>;
  albums: Array<{ id: string; title: string; artist_name: string; release_year?: number }>;
  tracks: Array<{ id: string; title: string; artist_name: string; album_title?: string }>;
};

export async function webSearch(query: string): Promise<SearchResult> {
  const res = await fetch(`${getApiBaseUrl()}/search?q=${encodeURIComponent(query)}`, {
    cache: 'no-store',
  });
  if (!res.ok) throw new Error(`Search failed with status ${res.status}`);
  return (await res.json()) as SearchResult;
}

export type RecommendationItem =
  | { type: 'album'; id: string; title: string; artist_name: string; reason?: string }
  | { type: 'track'; id: string; title: string; artist_name: string; album_title?: string; reason?: string };

export async function fetchRecommendations(userId: string): Promise<RecommendationItem[]> {
  const res = await fetch(`${getApiBaseUrl()}/recommendations?user_id=${encodeURIComponent(userId)}`, {
    cache: 'no-store',
  });
  if (!res.ok) throw new Error(`Recommendations failed with status ${res.status}`);
  return (await res.json()) as RecommendationItem[];
}

export async function requestIntegrationConnect(provider: 'spotify' | 'lastfm' | 'discord') {
  const res = await fetch(`${getApiBaseUrl()}/integrations/${provider}/connect`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ redirect_url: typeof window !== 'undefined' ? window.location.href : undefined }),
  });
  if (!res.ok) throw new Error(`Connect ${provider} failed with status ${res.status}`);
  return (await res.json()) as { status: string; url?: string };
}

export type TrendingItem = {
  type: 'album' | 'track';
  id: string;
  title: string;
  artist_name: string;
  average?: number;
  count?: number;
};

export async function fetchTrending(): Promise<TrendingItem[]> {
  const res = await fetch(`${getApiBaseUrl()}/trending`, { cache: 'no-store' });
  if (!res.ok) throw new Error(`Trending failed with status ${res.status}`);
  return (await res.json()) as TrendingItem[];
}
