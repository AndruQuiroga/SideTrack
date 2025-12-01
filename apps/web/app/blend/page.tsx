'use client';

import { useState, useEffect } from 'react';
import { useSearchParams } from 'next/navigation';
import Link from 'next/link';

import { PageShell } from '../components/page-shell';
import { Card, SectionHeading } from '../components/ui';
import { createFriendBlend, type BlendPreview } from '../../src/api/social';
import { showToast } from '../components/toast';

// Demo tracks for fallback
const demoTracks = [
  { id: '1', title: 'Hyperballad', artist_name: 'Björk', reason: 'Shared favorite' },
  { id: '2', title: 'Vroom Vroom', artist_name: 'Charli XCX', reason: 'High energy match' },
  { id: '3', title: 'Intro', artist_name: 'The xx', reason: 'Mood similarity' },
  { id: '4', title: 'How to Disappear Completely', artist_name: 'Radiohead', reason: 'Top artist overlap' },
  { id: '5', title: 'Oblivion', artist_name: 'Grimes', reason: 'Genre blend' },
];

export default function BlendPage() {
  const searchParams = useSearchParams();
  const [userA, setUserA] = useState('');
  const [userB, setUserB] = useState('');
  const [loading, setLoading] = useState(false);
  const [preview, setPreview] = useState<BlendPreview | null>(null);

  useEffect(() => {
    const a = searchParams.get('userA');
    const b = searchParams.get('userB');
    if (a) setUserA(a);
    if (b) setUserB(b);
  }, [searchParams]);

  async function onBlend() {
    if (!userA || !userB) {
      showToast('Enter two users to create a blend', 'error');
      return;
    }
    setLoading(true);
    setPreview(null);
    try {
      const result = await createFriendBlend(userA, userB);
      setPreview(result);
      showToast('Blend generated!', 'success');
    } catch {
      // Use demo fallback
      setPreview({
        name: `${userA} × ${userB} Blend`,
        description: 'A curated mix based on your shared tastes and listening patterns.',
        tracks: demoTracks,
      });
      showToast('Showing demo blend (API unavailable)', 'success');
    } finally {
      setLoading(false);
    }
  }

  return (
    <PageShell
      title="Friend blend"
      description="Create a blended playlist from two users' listening tastes and preferences."
      accent="Playlist generator"
    >
      <Card className="space-y-4">
        <SectionHeading eyebrow="Select users" title="Who's blending?" />
        <div className="grid gap-4 md:grid-cols-[1fr,auto,1fr]">
          <div className="space-y-2">
            <label className="text-xs font-semibold uppercase tracking-wider text-slate-400">User A</label>
            <input
              value={userA}
              onChange={(e) => setUserA(e.target.value)}
              placeholder="Username or ID"
              className="w-full rounded-xl border border-slate-800/80 bg-slate-900/80 px-4 py-2.5 text-sm text-slate-100 outline-none ring-emerald-500/40 transition placeholder:text-slate-500 focus:border-slate-700 focus:ring-2"
            />
          </div>
          <div className="flex items-end justify-center pb-2">
            <span className="text-2xl text-slate-600">×</span>
          </div>
          <div className="space-y-2">
            <label className="text-xs font-semibold uppercase tracking-wider text-slate-400">User B</label>
            <input
              value={userB}
              onChange={(e) => setUserB(e.target.value)}
              placeholder="Username or ID"
              className="w-full rounded-xl border border-slate-800/80 bg-slate-900/80 px-4 py-2.5 text-sm text-slate-100 outline-none ring-emerald-500/40 transition placeholder:text-slate-500 focus:border-slate-700 focus:ring-2"
            />
          </div>
        </div>
        <div className="flex justify-center pt-2">
          <button
            onClick={onBlend}
            disabled={loading || !userA || !userB}
            className="rounded-full bg-gradient-to-r from-purple-500 to-emerald-400 px-8 py-2.5 text-sm font-semibold text-white shadow-lg transition hover:opacity-90 disabled:opacity-50"
          >
            {loading ? (
              <span className="flex items-center gap-2">
                <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                Blending...
              </span>
            ) : (
              'Generate blend'
            )}
          </button>
        </div>
      </Card>

      <Card className="space-y-4">
        <SectionHeading
          eyebrow="Result"
          title={preview?.name ?? 'Your blend will appear here'}
          aside={
            preview && (
              <span className="rounded-full bg-emerald-500/20 px-3 py-1 text-xs font-semibold text-emerald-300">
                {preview.tracks.length} tracks
              </span>
            )
          }
        />
        {preview ? (
          <div className="space-y-4">
            {preview.description && (
              <p className="text-sm text-slate-400">{preview.description}</p>
            )}
            <div className="space-y-2">
              {preview.tracks.map((track, index) => (
                <div
                  key={track.id}
                  className="group flex items-center gap-3 rounded-xl border border-slate-800/60 bg-slate-900/50 p-3 transition-all hover:border-slate-700/80 hover:bg-slate-900/70"
                >
                  <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-slate-800/80 text-xs font-semibold text-slate-400">
                    {index + 1}
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-semibold text-white">{track.title}</p>
                    <p className="text-xs text-slate-400">{track.artist_name}</p>
                  </div>
                  {track.reason && (
                    <span className="hidden rounded-full bg-slate-800/60 px-3 py-1 text-xs text-slate-400 sm:block">
                      {track.reason}
                    </span>
                  )}
                </div>
              ))}
            </div>
            <div className="flex flex-wrap gap-3 pt-2">
              <button className="rounded-full border border-slate-700/70 bg-slate-800/80 px-5 py-2 text-sm font-medium text-white transition hover:bg-slate-700/80">
                Save to Spotify
              </button>
              <Link
                href={`/compare?userA=${userA}&userB=${userB}`}
                className="rounded-full border border-slate-800/60 bg-slate-900/60 px-5 py-2 text-sm text-slate-300 transition hover:border-slate-700 hover:text-white"
              >
                View compatibility
              </Link>
            </div>
          </div>
        ) : (
          <div className="rounded-2xl border border-dashed border-slate-800/60 bg-slate-900/30 p-8 text-center">
            <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-slate-800/60 text-xl">
              🎶
            </div>
            <p className="text-sm text-slate-400">
              Enter two users above and click Generate to create a blended playlist
            </p>
          </div>
        )}
      </Card>

      <Card className="space-y-3">
        <SectionHeading eyebrow="How it works" title="Smart blending algorithm" />
        <div className="grid gap-4 md:grid-cols-3">
          <div className="rounded-xl bg-slate-900/50 p-4">
            <p className="text-sm font-semibold text-white">🔍 Find overlaps</p>
            <p className="mt-1 text-xs text-slate-400">
              We identify shared artists, genres, and mood preferences between both users.
            </p>
          </div>
          <div className="rounded-xl bg-slate-900/50 p-4">
            <p className="text-sm font-semibold text-white">⚖️ Balance tastes</p>
            <p className="mt-1 text-xs text-slate-400">
              Tracks are weighted to represent both listeners fairly.
            </p>
          </div>
          <div className="rounded-xl bg-slate-900/50 p-4">
            <p className="text-sm font-semibold text-white">🎯 Curate flow</p>
            <p className="mt-1 text-xs text-slate-400">
              The final playlist is ordered for smooth transitions and energy arcs.
            </p>
          </div>
        </div>
      </Card>
    </PageShell>
  );
}
