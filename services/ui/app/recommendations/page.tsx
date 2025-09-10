'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import RecCard, { type Rec } from '../../components/recs/RecCard';
import { apiFetch } from '../../lib/api';
import { saveTrack, createPlaylist } from '../../lib/spotifyClient';

export default function RecommendationsPage() {
  const [recs, setRecs] = useState<Rec[]>([]);
  const [index, setIndex] = useState(0);
  const [liked, setLiked] = useState<Rec[]>([]);
  const [hidden, setHidden] = useState<Set<string>>(new Set());
  const [newOnly, setNewOnly] = useState(false);
  const [freshness, setFreshness] = useState(0);

  useEffect(() => {
    apiFetch('/api/v1/recs/ranked')
      .then((r) => r.json())
      .then((j) => setRecs(j ?? []))
      .catch(() => setRecs([]));
  }, []);

  const filtered = useMemo(() => recs.filter((r) => !hidden.has(r.artist)), [recs, hidden]);
  const current = filtered[index];

  const like = useCallback(async () => {
    if (!current) return;
    if (current.spotify_id) {
      saveTrack(current.spotify_id).catch(() => {});
    }
    setLiked((prev) => [...prev, current]);
    setIndex((i) => i + 1);
  }, [current]);

  const skip = useCallback(() => setIndex((i) => i + 1), []);

  const hideArtist = useCallback(() => {
    if (current) setHidden((prev) => new Set(prev).add(current.artist));
    setIndex((i) => i + 1);
  }, [current]);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'ArrowRight') like();
      if (e.key === 'ArrowLeft') skip();
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [like, skip]);

  const buildMixtape = useCallback(async () => {
    const uris = liked.map((t) => t.spotify_id || '').filter(Boolean);
    if (!uris.length) return;
    await createPlaylist('Mixtape', uris);
  }, [liked]);

  return (
    <section className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold">Recommendations</h2>
        {liked.length > 0 && (
          <button onClick={buildMixtape} className="text-sm underline">
            Build Mixtape
          </button>
        )}
      </div>
      <div className="flex items-center gap-4">
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={newOnly}
            onChange={() => setNewOnly((v) => !v)}
          />
          New artists only
        </label>
        <label className="flex items-center gap-2 text-sm">
          Min freshness
          <input
            type="range"
            min={0}
            max={1}
            step={0.1}
            value={freshness}
            onChange={(e) => setFreshness(parseFloat(e.target.value))}
          />
        </label>
      </div>
      {current ? (
        <RecCard rec={current} onLike={like} onSkip={skip} onHideArtist={hideArtist} />
      ) : (
        <p>No more recommendations.</p>
      )}
    </section>
  );
}

