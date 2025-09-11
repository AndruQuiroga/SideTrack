'use client';

import Image from 'next/image';
import { useEffect, useRef, useState } from 'react';
import BecauseChips from './BecauseChips';
import RecActions from './RecActions';
import Skeleton from '../Skeleton';
import { getArtworkUrl } from '../../lib/artwork';
import type { Reason } from '../../lib/sources';

export type Rec = {
  title: string;
  artist: string;
  spotify_id?: string;
  recording_mbid?: string;
  reasons?: Reason[];
};

interface Props {
  rec: Rec;
  onLike: () => void;
  onSkip: () => void;
  onHideArtist: () => void;
}

export default function RecCard({ rec, onLike, onSkip, onHideArtist }: Props) {
  const [img, setImg] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const startX = useRef<number | null>(null);

  useEffect(() => {
    setLoading(true);
    getArtworkUrl(rec.spotify_id, rec.recording_mbid)
      .then((url) => setImg(url))
      .finally(() => setLoading(false));
  }, [rec.spotify_id, rec.recording_mbid]);

  return (
    <div
      className="space-y-4 rounded-lg border p-4 touch-pan-y"
      onPointerDown={(e) => {
        startX.current = e.clientX;
      }}
      onPointerUp={(e) => {
        if (startX.current === null) return;
        const diff = e.clientX - startX.current;
        if (diff > 40) onLike();
        if (diff < -40) onSkip();
        startX.current = null;
      }}
    >
      {loading ? (
        <Skeleton className="h-[300px]" />
      ) : (
        <Image
          src={img ?? '/default-cover.svg'}
          alt={`${rec.title} cover`}
          width={300}
          height={300}
          className="w-full rounded"
        />
      )}
      <div>
        <h4 className="text-lg font-semibold">{rec.title}</h4>
        <p className="text-sm text-muted-foreground">{rec.artist}</p>
      </div>
      {rec.reasons && rec.reasons.length > 0 && <BecauseChips reasons={rec.reasons} />}
      <RecActions onLike={onLike} onSkip={onSkip} onHideArtist={onHideArtist} />
    </div>
  );
}

