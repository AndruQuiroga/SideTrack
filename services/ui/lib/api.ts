import { getUserId } from './auth';

export const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'https://sidetrack.network/api';

export async function apiFetch(path: string, init: RequestInit = {}) {
  const headers = new Headers(init.headers);
  const uid = getUserId();
  if (uid) headers.set('X-User-Id', uid);
  const finalInit = { ...init, headers };
  const url = path.startsWith('/api/') ? path : `${API_BASE}${path}`;

  try {
    const res = await fetch(url, finalInit);
    if (!res.ok) {
      let message = res.statusText;
      try {
        const data = await res.json();
        message = (data && (data.detail || data.message)) || message;
      } catch {
        // ignore json parse errors
      }
      throw new Error(`${res.status} ${message}`);
    }
    return res;
  } catch (err: any) {
    throw new Error(err?.message || 'Network error');
  }
}
