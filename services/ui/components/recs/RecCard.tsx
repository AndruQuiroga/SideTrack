'use client';

import Image from 'next/image';
import { motion, useMotionValue, useTransform, type PanInfo } from 'framer-motion';
import { useEffect, useMemo, useState } from 'react';
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

const LIKE_THRESHOLD = 120;
const SKIP_THRESHOLD = 100;
const HIDE_THRESHOLD = 220;

const clamp = (value: number, min = 0, max = 1) => Math.min(Math.max(value, min), max);

export default function RecCard({ rec, onLike, onSkip, onHideArtist }: Props) {
  const [img, setImg] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const x = useMotionValue(0);

  const likeProgress = useTransform(x, (value) => (value <= 0 ? 0 : clamp(value / LIKE_THRESHOLD)));
  const skipProgress = useTransform(x, (value) => {
    if (value >= 0) return 0;
    const magnitude = Math.abs(value);
    if (magnitude <= SKIP_THRESHOLD) {
      return clamp(magnitude / SKIP_THRESHOLD);
    }
    if (magnitude >= HIDE_THRESHOLD) {
      return 0;
    }
    const between = (magnitude - SKIP_THRESHOLD) / (HIDE_THRESHOLD - SKIP_THRESHOLD);
    return clamp(1 - between);
  });
  const hideProgress = useTransform(x, (value) => {
    if (value >= 0) return 0;
    const magnitude = Math.abs(value);
    if (magnitude <= SKIP_THRESHOLD) {
      return 0;
    }
    if (magnitude >= HIDE_THRESHOLD) {
      return 1;
    }
    const between = (magnitude - SKIP_THRESHOLD) / (HIDE_THRESHOLD - SKIP_THRESHOLD);
    return clamp(between);
  });

  const dragConstraints = useMemo(() => ({ left: -HIDE_THRESHOLD - 80, right: LIKE_THRESHOLD + 80 }), []);

  const handleDragEnd = (_: MouseEvent | TouchEvent | PointerEvent, info: PanInfo) => {
    const offsetX = info.offset.x;
    if (offsetX > LIKE_THRESHOLD) {
      onLike();
      x.set(0);
      return;
    }
    if (offsetX < -HIDE_THRESHOLD) {
      onHideArtist();
      x.set(0);
      return;
    }
    if (offsetX < -SKIP_THRESHOLD) {
      onSkip();
    }
    x.set(0);
  };

  useEffect(() => {
    setLoading(true);
    getArtworkUrl(rec.spotify_id, rec.recording_mbid)
      .then((url) => setImg(url))
      .finally(() => setLoading(false));
  }, [rec.spotify_id, rec.recording_mbid]);

  return (
    <motion.div
      data-testid="rec-card"
      className="space-y-4 rounded-lg border p-4 touch-pan-y"
      drag="x"
      dragConstraints={dragConstraints}
      dragElastic={0.2}
      dragMomentum={false}
      dragSnapToOrigin
      onDragEnd={handleDragEnd}
      style={{ x }}
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
      <RecActions
        onLike={onLike}
        onSkip={onSkip}
        onHideArtist={onHideArtist}
        likeProgress={likeProgress}
        skipProgress={skipProgress}
        hideProgress={hideProgress}
      />
    </motion.div>
  );
}

