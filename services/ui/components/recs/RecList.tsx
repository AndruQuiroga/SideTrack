'use client';

import { useMemo, useState } from 'react';
import RecCard, { type Rec } from './RecCard';
import { saveTrack, createPlaylist } from '../../lib/spotifyClient';

interface Props {
  recs: Rec[];
}

function dedupe(recs: Rec[]) {
  const seen = new Set<string>();
  return recs.filter((r) => {
    const key = r.mbid || r.isrc || r.id;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

export default function RecList({ recs }: Props) {
  const [index, setIndex] = useState(0);
  const [liked, setLiked] = useState<Rec[]>([]);
  const [hidden, setHidden] = useState<Set<string>>(new Set());

  const filtered = useMemo(() => {
    const deduped = dedupe(recs);
    return deduped.filter((r) => !hidden.has(r.artist));
  }, [recs, hidden]);

  const current = filtered[index];

  const handleLike = async () => {
    if (!current) return;
    setLiked((prev) => [...prev, current]);
    saveTrack(current.id).catch(() => {});
    setIndex((i) => i + 1);
  };

  const handleSkip = () => setIndex((i) => i + 1);

  const handleHide = () => {
    if (current) setHidden(new Set(hidden).add(current.artist));
    setIndex((i) => i + 1);
  };

  const buildMixtape = async () => {
    if (!liked.length) return;
    try {
      await createPlaylist(
        'Mixtape',
        liked.map((t) => t.uri || t.id),
      );
    } catch {
      const lines = ['#EXTM3U', ...liked.map((t) => t.uri || t.id)];
      const blob = new Blob([lines.join('\n')], { type: 'audio/x-mpegurl' });
      const link = document.createElement('a');
      link.href = URL.createObjectURL(blob);
      link.download = 'mixtape.m3u';
      link.click();
    }
  };

  if (!current) {
    return (
      <div className="space-y-4">
        <p>No more recommendations.</p>
        {liked.length > 0 && (
          <button onClick={buildMixtape} className="text-sm underline">
            Build Mixtape
          </button>
        )}
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <RecCard rec={current} onLike={handleLike} onSkip={handleSkip} onHideArtist={handleHide} />
      {liked.length > 0 && (
        <div className="text-right">
          <button onClick={buildMixtape} className="text-sm underline">
            Build Mixtape
          </button>
        </div>
      )}
    </div>
  );
}

export type { Rec };
