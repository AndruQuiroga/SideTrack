'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import RecCard, { type Rec } from '../../components/recs/RecCard';
import FiltersBar from '../../components/recs/FiltersBar';
import MixtapeButton from '../../components/mixtape/MixtapeButton';
import { apiFetch } from '../../lib/api';
import { saveTrack } from '../../lib/spotifyClient';

export default function RecommendationsPage() {
  const [recs, setRecs] = useState<Rec[]>([]);
  const [index, setIndex] = useState(0);
  const [liked, setLiked] = useState<Rec[]>([]);
  const [hidden, setHidden] = useState<Set<string>>(new Set());
  const [filters, setFilters] = useState({
    newOnly: false,
    freshness: 0,
    diversity: 0,
    energy: 0,
  });

  useEffect(() => {
    const params = new URLSearchParams();
    if (filters.newOnly) params.set('new', '1');
    if (filters.freshness) params.set('min_freshness', String(filters.freshness));
    if (filters.diversity) params.set('diversity', String(filters.diversity));
    if (filters.energy) params.set('energy', String(filters.energy));
    apiFetch(`/api/recs/ranked?${params.toString()}`)
      .then((r) => r.json())
      .then((j) => {
        setRecs(j ?? []);
        setIndex(0);
      })
      .catch(() => setRecs([]));
  }, [filters]);

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
      if (e.key === 'ArrowDown') hideArtist();
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [like, skip, hideArtist]);

  return (
    <section className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold">Recommendations</h2>
        <MixtapeButton tracks={liked} />
      </div>
      <FiltersBar filters={filters} onChange={setFilters} />
      {current ? (
        <RecCard rec={current} onLike={like} onSkip={skip} onHideArtist={hideArtist} />
      ) : (
        <p>No more recommendations.</p>
      )}
    </section>
  );
}

