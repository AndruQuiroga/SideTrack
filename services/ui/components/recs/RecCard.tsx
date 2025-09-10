'use client';

import { Button } from '../ui/button';

export type Rec = {
  id: string;
  title: string;
  artist: string;
  mbid?: string;
  isrc?: string;
  uri?: string;
  because?: string[];
};

interface Props {
  rec: Rec;
  onLike: () => void;
  onSkip: () => void;
  onHideArtist: () => void;
}

export default function RecCard({ rec, onLike, onSkip, onHideArtist }: Props) {
  return (
    <div className="space-y-4 rounded-lg border p-4">
      <div>
        <h4 className="text-lg font-semibold">{rec.title}</h4>
        <p className="text-sm text-muted-foreground">{rec.artist}</p>
      </div>
      {rec.because && (
        <div className="flex flex-wrap gap-2">
          {rec.because.map((reason) => (
            <span key={reason} className="rounded-full bg-secondary px-2 py-0.5 text-xs">
              Because {reason}
            </span>
          ))}
        </div>
      )}
      <div className="flex gap-2">
        <Button onClick={onLike}>Like</Button>
        <Button variant="outline" onClick={onSkip}>
          Skip
        </Button>
        <Button variant="ghost" onClick={onHideArtist}>
          Hide artist
        </Button>
      </div>
    </div>
  );
}
