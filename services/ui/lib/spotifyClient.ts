import { apiFetch } from './api';

export async function saveTrack(trackId: string) {
  await apiFetch('/api/spotify/save', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ trackId }),
  });
}

export async function createPlaylist(name: string, uris: string[]) {
  const r = await apiFetch('/api/spotify/playlist', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, uris }),
  });
  return r.json().catch(() => ({}));
}
