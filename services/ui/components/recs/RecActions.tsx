'use client';

import { Button } from '../ui/button';
import { useToast } from '../ToastProvider';

interface Props {
  onLike: () => void | Promise<void>;
  onSkip: () => void | Promise<void>;
  onHideArtist: () => void | Promise<void>;
}

export default function RecActions({ onLike, onSkip, onHideArtist }: Props) {
  const { show } = useToast();

  return (
    <div className="flex gap-2">
      <Button
        onClick={async () => {
          await onLike();
          show({ title: 'Saved', kind: 'success' });
        }}
      >
        Like
      </Button>
      <Button
        variant="outline"
        onClick={async () => {
          await onSkip();
        }}
      >
        Skip
      </Button>
      <Button
        variant="ghost"
        onClick={async () => {
          await onHideArtist();
          show({ title: 'Artist hidden', kind: 'success' });
        }}
      >
        Hide artist
      </Button>
    </div>
  );
}

