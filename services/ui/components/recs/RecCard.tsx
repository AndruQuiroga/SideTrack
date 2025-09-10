'use client';

import Image from 'next/image';
import { useEffect, useState } from 'react';
import BecauseChips from './BecauseChips';
import RecActions from './RecActions';
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

  useEffect(() => {
    if (rec.spotify_id) {
      fetch(`https://open.spotify.com/oembed?url=spotify:track:${rec.spotify_id}`)
        .then((r) => r.json())
        .then((j) => setImg(j?.thumbnail_url))
        .catch(() => {});
    }
  }, [rec.spotify_id]);

  return (
    <div className="space-y-4 rounded-lg border p-4">
      {img && (
        <Image
          src={img}
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

