import { getUserId } from './auth';

export const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'https://sidetrack.network/api';

export function apiFetch(path: string, init: RequestInit = {}) {
  const headers = new Headers(init.headers);
  const uid = getUserId();
  if (uid) headers.set('X-User-Id', uid);
  const finalInit = { ...init, headers };
  if (path.startsWith('/api/')) {
    return fetch(path, finalInit);
  }
  return fetch(`${API_BASE}${path}`, finalInit);
}
