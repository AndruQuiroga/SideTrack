const cache = new Map<string, string | null>();

export async function getArtworkUrl(
  spotifyId?: string,
  recordingMbid?: string,
): Promise<string | null> {
  const key = spotifyId
    ? `spotify:${spotifyId}`
    : recordingMbid
      ? `mbid:${recordingMbid}`
      : null;
  if (!key) return null;
  if (cache.has(key)) return cache.get(key)!;

  try {
    const params = new URLSearchParams();
    if (spotifyId) params.set('spotify_id', spotifyId);
    if (recordingMbid) params.set('recording_mbid', recordingMbid);
    const r = await fetch(`/api/artwork?${params.toString()}`);
    if (!r.ok) {
      cache.set(key, null);
      return null;
    }
    const j = await r.json();
    const url = j?.url ?? null;
    cache.set(key, url);
    return url;
  } catch {
    cache.set(key, null);
    return null;
  }
}

