'use client';

import { useMemo, useState } from 'react';
import { Dialog, DialogContent, DialogTitle } from '../ui/dialog';
import { Button } from '../ui/button';
import type { Rec } from '../recs/RecCard';
import { createPlaylist } from '../../lib/spotifyClient';

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  tracks: Rec[];
}

export default function MixtapeModal({ open, onOpenChange, tracks }: Props) {
  const [length, setLength] = useState(Math.min(10, tracks.length));
  const selected = useMemo(() => tracks.slice(0, length), [tracks, length]);
  const uris = useMemo(
    () => selected.map((t) => t.spotify_id || '').filter(Boolean),
    [selected],
  );

  const exportM3U = () => {
    const lines = ['#EXTM3U', ...selected.map((t) => t.title)];
    const blob = new Blob([lines.join('\n')], { type: 'audio/x-mpegurl' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'mixtape.m3u';
    a.click();
    URL.revokeObjectURL(url);
  };

  const createSpotify = async () => {
    if (!uris.length) return;
    await createPlaylist('Mixtape', uris);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-sm">
        <DialogTitle>Build Mixtape</DialogTitle>
        <div className="space-y-4">
          <label className="flex items-center gap-2 text-sm">
            Length
            <input
              type="range"
              min={1}
              max={tracks.length}
              value={length}
              onChange={(e) => setLength(parseInt(e.target.value, 10))}
            />
            <span>{length}</span>
          </label>
          <div className="flex flex-col gap-2 sm:flex-row">
            <Button onClick={exportM3U} className="flex-1">
              Export M3U
            </Button>
            <Button
              variant="outline"
              onClick={createSpotify}
              className="flex-1"
            >
              Create Spotify playlist
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
