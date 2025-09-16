"use client";

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { apiFetch } from '../../lib/api';
import { addToMixtape } from '../../lib/mixtape';
import RadarChart from '../charts/RadarChart';
import { useInspector } from '../../hooks/useInspector';

type SimilarArtist = { artist_id: number; name: string };
type AlsoListened = { track_id: number; title: string };

type TrackData = {
  title?: string;
  features?: { valence: number; energy: number; tempo: number; danceability: number };
  tags?: string[];
  similar?: SimilarArtist[];
  mb?: { label?: string; area?: string; era?: string };
  alsoListened?: AlsoListened[];
};

export default function TrackPanel({ trackId }: { trackId: number }) {
  const [data, setData] = useState<TrackData>();
  const router = useRouter();
  const { inspect } = useInspector();

  useEffect(() => {
    (async () => {
      try {
        const res = await apiFetch(`/inspect/track/${trackId}`);
        setData((await res.json()) as TrackData);
      } catch {
        setData({});
      }
    })();
  }, [trackId]);

  const handleAddFive = async () => {
    try {
      const res = await apiFetch(`/similar/track/${trackId}?limit=5`);
      const items = (await res.json()) as AlsoListened[];
      items.slice(0, 5).forEach((t) => addToMixtape({ track_id: t.track_id, title: t.title }));
    } catch {
      /* noop */
    }
  };

  const baseline = { valence: 0.5, energy: 0.5, tempo: 0.5, danceability: 0.5 };
  const axes = data?.features
    ? {
        valence: data.features.valence,
        energy: data.features.energy,
        tempo: data.features.tempo / 200,
        danceability: data.features.danceability,
      }
    : baseline;

  return (
    <div className="space-y-6 p-4">
      {data?.features && (
        <section>
          <h3 className="mb-2 text-sm font-semibold">Audio Features</h3>
          <RadarChart axes={axes} baseline={baseline} />
        </section>
      )}
      {data?.tags && data.tags.length > 0 && (
        <section>
          <h3 className="mb-2 text-sm font-semibold">Top Tags</h3>
          <ul className="flex flex-wrap gap-2 text-xs text-muted-foreground">
            {data.tags.map((t) => (
              <li key={t}>#{t}</li>
            ))}
          </ul>
        </section>
      )}
      {data?.similar && data.similar.length > 0 && (
        <section>
          <h3 className="mb-2 text-sm font-semibold">Similar Artists</h3>
          <div className="grid grid-cols-3 gap-2 text-sm">
            {data.similar.map((a) => (
              <button
                key={a.artist_id}
                onClick={() => inspect({ type: 'artist', id: a.artist_id })}
                className="truncate text-left hover:underline"
              >
                {a.name}
              </button>
            ))}
          </div>
        </section>
      )}
      {data?.mb && (
        <section className="text-sm">
          <h3 className="mb-2 font-semibold">MusicBrainz</h3>
          <p>Label: {data.mb.label ?? '—'}</p>
          <p>Area: {data.mb.area ?? '—'}</p>
          <p>Era: {data.mb.era ?? '—'}</p>
        </section>
      )}
      {data?.alsoListened && data.alsoListened.length > 0 && (
        <section>
          <h3 className="mb-2 text-sm font-semibold">Also Listened</h3>
          <ul className="space-y-1 text-sm">
            {data.alsoListened.map((t) => (
              <button
                key={t.track_id}
                onClick={() => inspect({ type: 'track', id: t.track_id })}
                className="block w-full truncate text-left hover:underline"
              >
                {t.title}
              </button>
            ))}
          </ul>
        </section>
      )}
      <div className="flex gap-2 pt-2">
        <button
          className="rounded bg-primary px-3 py-1 text-xs text-primary-foreground"
          onClick={() => router.push(`/similar?track=${trackId}`)}
        >
          Find similar
        </button>
        <button
          className="rounded bg-primary px-3 py-1 text-xs text-primary-foreground"
          onClick={() => router.push(`/radio?track=${trackId}`)}
        >
          Start radio
        </button>
        <button
          className="rounded bg-primary px-3 py-1 text-xs text-primary-foreground"
          onClick={handleAddFive}
        >
          Add 5 to mixtape
        </button>
      </div>
    </div>
  );
}
