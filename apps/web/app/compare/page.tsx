import { Suspense } from 'react';

import { fetchCompatibility } from '../../src/api/client';
import { PageShell } from '../components/page-shell';
import { Card } from '../components/ui';

interface ComparePageProps {
  searchParams: { userA?: string; userB?: string };
}

interface OverlapData {
  shared_artists?: string[];
  shared_genres?: string[];
}

async function CompatibilityResult({ userA, userB }: { userA: string; userB: string }) {
  const result = await fetchCompatibility(userA, userB).catch(() => null);

  if (!result) {
    return (
      <Card>
        <p className="text-sm text-slate-300">Compatibility lookup failed.</p>
      </Card>
    );
  }

  const overlap = result.overlap as OverlapData | undefined;

  return (
    <Card className="space-y-3">
      <p className="text-sm uppercase tracking-wide text-slate-400">Taste match</p>
      <p className="text-4xl font-semibold text-sidetrack-accent">{Math.round(result.score)}%</p>
      <p className="text-sm text-slate-300">{result.explanation ?? 'Similarity based on shared tastes.'}</p>
      <div className="grid gap-3 md:grid-cols-2">
        <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-3">
          <p className="text-xs uppercase tracking-wide text-slate-400">Shared artists</p>
          <div className="mt-2 flex flex-wrap gap-2 text-xs font-semibold text-slate-200">
            {Array.isArray(overlap?.shared_artists)
              ? overlap.shared_artists.map((artist) => (
                  <span key={artist} className="rounded-full bg-slate-800 px-3 py-1">
                    {artist}
                  </span>
                ))
              : ['Bjork', 'Little Simz', 'Radiohead'].map((artist) => (
                  <span key={artist} className="rounded-full bg-slate-800 px-3 py-1">
                    {artist}
                  </span>
                ))}
          </div>
        </div>
        <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-3">
          <p className="text-xs uppercase tracking-wide text-slate-400">Shared genres</p>
          <div className="mt-2 flex flex-wrap gap-2 text-xs font-semibold text-slate-200">
            {Array.isArray(overlap?.shared_genres)
              ? overlap.shared_genres.map((g) => (
                  <span key={g} className="rounded-full bg-slate-800 px-3 py-1">
                    {g}
                  </span>
                ))
              : ['Art Pop', 'Indie Rock', 'Alt Hip-Hop'].map((g) => (
                  <span key={g} className="rounded-full bg-slate-800 px-3 py-1">
                    {g}
                  </span>
                ))}
          </div>
        </div>
      </div>
    </Card>
  );
}

export default function ComparePage({ searchParams }: ComparePageProps) {
  const { userA, userB } = searchParams;

  if (!userA || !userB) {
    return (
      <PageShell
        title="Compare tastes"
        description="Provide two users to see how their listening overlaps. Perfect for friend matchups or club debates."
        accent="Taste match"
      >
        <Card className="space-y-2">
          <p className="text-sm text-slate-300">Provide userA and userB query params to see compatibility.</p>
          <p className="text-sm text-slate-400">Example: /compare?userA=demo&userB=demo2</p>
        </Card>
      </PageShell>
    );
  }

  return (
    <PageShell
      title="Compatibility"
      description="See how two listeners align based on ratings and listening data. Percentage is an early preview of the social experience."
      accent="Prototype view"
    >
      <Suspense fallback={<p className="text-sm text-slate-300">Loading compatibility…</p>}>
        <CompatibilityResult userA={userA} userB={userB} />
      </Suspense>
    </PageShell>
  );
}
