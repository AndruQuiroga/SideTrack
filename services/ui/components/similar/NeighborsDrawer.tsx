"use client";

import { useEffect, useState } from 'react';
import { apiFetch } from '../../lib/api';
import { addToMixtape } from '../../lib/mixtape';

type Props = {
  trackId: number;
  open: boolean;
  onClose: () => void;
};

type Neighbor = { track_id: number; score: number; title?: string };

export default function NeighborsDrawer({ trackId, open, onClose }: Props) {
  const [neighbors, setNeighbors] = useState<Neighbor[]>([]);

  useEffect(() => {
    if (!open) return;
    (async () => {
      try {
        const res = await apiFetch(`/similar/track/${trackId}`);
        if (res.ok) {
          setNeighbors((await res.json()) as Neighbor[]);
        } else {
          setNeighbors([]);
        }
      } catch {
        setNeighbors([]);
      }
    })();
  }, [trackId, open]);

  const handleDragStart = (e: React.DragEvent, n: Neighbor) => {
    e.dataTransfer.setData('application/json', JSON.stringify(n));
  };

  return (
    <aside
      className={`fixed right-0 top-0 z-40 h-full w-80 bg-background shadow-lg transition-transform ${
        open ? 'translate-x-0' : 'translate-x-full'
      }`}
    >
      <div className="flex items-center justify-between p-4">
        <h2 className="text-lg font-semibold">Sonic Neighbors</h2>
        <button onClick={onClose} className="text-sm text-muted-foreground">
          Close
        </button>
      </div>
      <ul className="divide-y divide-border overflow-y-auto">
        {neighbors.map((n) => (
          <li
            key={n.track_id}
            draggable
            onDragStart={(e) => handleDragStart(e, n)}
            onDoubleClick={() => addToMixtape(n)}
            className="cursor-move p-4 text-sm hover:bg-muted/20"
          >
            {n.title ?? `Track ${n.track_id}`}
          </li>
        ))}
      </ul>
    </aside>
  );
}

