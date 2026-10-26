/** Server-only discovery data, fetched for the session user. */
import { apiRequest } from '../server-api';

export type SearchResult = {
  users: Array<{ id: string; display_name: string; handle?: string }>;
  albums: Array<{ id: string; title: string; artist_name: string; release_year?: number }>;
  tracks: Array<{ id: string; title: string; artist_name: string; album_title?: string }>;
};

export async function webSearch(sessionUserId: string, query: string): Promise<SearchResult> {
  return apiRequest<SearchResult>(sessionUserId, `/search?q=${encodeURIComponent(query)}`);
}

export type RecommendationItem =
  | { type: 'album'; id: string; title: string; artist_name: string; reason?: string }
  | {
      type: 'track';
      id: string;
      title: string;
      artist_name: string;
      album_title?: string;
      reason?: string;
    };

/** The session user's own recommendations; the API derives the user from the actor. */
export async function fetchRecommendations(sessionUserId: string): Promise<RecommendationItem[]> {
  return apiRequest<RecommendationItem[]>(sessionUserId, '/recommendations');
}

export type TrendingItem = {
  type: 'album' | 'track';
  id: string;
  title: string;
  artist_name: string;
  average?: number;
  count?: number;
};

export async function fetchTrending(sessionUserId: string): Promise<TrendingItem[]> {
  return apiRequest<TrendingItem[]>(sessionUserId, '/trending');
}
