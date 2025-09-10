'use client';

import { useState } from 'react';
import { Button } from '../ui/button';
import MixtapeModal from './MixtapeModal';
import type { Rec } from '../recs/RecCard';

interface Props {
  tracks: Rec[];
}

export default function MixtapeButton({ tracks }: Props) {
  const [open, setOpen] = useState(false);
  if (!tracks.length) return null;
  return (
    <>
      <Button variant="ghost" size="sm" onClick={() => setOpen(true)}>
        Build Mixtape
      </Button>
      {open && (
        <MixtapeModal open={open} onOpenChange={setOpen} tracks={tracks} />
      )}
    </>
  );
}
