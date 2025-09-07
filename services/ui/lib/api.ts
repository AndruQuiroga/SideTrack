export const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'https://sidetrack.network/api';

export function apiFetch(path: string, init?: RequestInit) {
  return fetch(`${API_BASE}${path}`, init);
}
