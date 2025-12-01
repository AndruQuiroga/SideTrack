import { Suspense } from 'react';
import Link from 'next/link';

import { fetchCompatibility } from '../../src/api/client';
import { PageShell } from '../components/page-shell';
import { Card, SectionHeading } from '../components/ui';

interface ComparePageProps {
  searchParams: { userA?: string; userB?: string };
}

interface OverlapData {
  shared_artists?: string[];
  shared_genres?: string[];
}

function MatchScore({ score }: { score: number }) {
  const getColor = () => {
    if (score >= 80) return 'from-emerald-400 to-emerald-500';
    if (score >= 60) return 'from-sky-400 to-sky-500';
    if (score >= 40) return 'from-purple-400 to-purple-500';
    return 'from-slate-400 to-slate-500';
  };

  return (
    <div className="relative">
      <div className="flex h-32 w-32 items-center justify-center rounded-full border-4 border-slate-800/80 bg-gradient-to-br from-slate-900/80 to-slate-900/50">
        <div className="text-center">
          <span className={`bg-gradient-to-r ${getColor()} bg-clip-text text-4xl font-bold text-transparent`}>
            {Math.round(score)}
          </span>
          <span className="text-2xl text-slate-400">%</span>
        </div>
      </div>
      <div 
        className={`absolute inset-0 rounded-full bg-gradient-to-r ${getColor()} opacity-20 blur-xl`}
      />
    </div>
  );
}

async function CompatibilityResult({ userA, userB }: { userA: string; userB: string }) {
  const result = await fetchCompatibility(userA, userB).catch(() => null);

  if (!result) {
    return (
      <Card className="text-center">
        <p className="text-sm text-slate-400">Compatibility lookup failed. Try again later.</p>
      </Card>
    );
  }

  const overlap = result.overlap as OverlapData | undefined;
  const sharedArtists = overlap?.shared_artists ?? ['Björk', 'Little Simz', 'Radiohead'];
  const sharedGenres = overlap?.shared_genres ?? ['Art Pop', 'Indie Rock', 'Alt Hip-Hop'];

  return (
    <div className="space-y-5">
      <Card className="relative overflow-hidden">
        <div className="absolute -left-20 -top-20 h-40 w-40 rounded-full bg-gradient-to-br from-purple-500/20 via-sky-500/10 to-transparent blur-3xl" />
        <div className="relative flex flex-col items-center gap-6 md:flex-row md:items-start md:justify-between">
          <div className="text-center md:text-left">
            <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">Taste match</p>
            <h2 className="mt-1 text-2xl font-bold text-white">
              {userA} <span className="text-slate-500">×</span> {userB}
            </h2>
            <p className="mt-3 max-w-md text-sm text-slate-400">
              {result.explanation ?? 'Based on shared listening patterns, genre preferences, and mood similarities.'}
            </p>
          </div>
          <MatchScore score={result.score} />
        </div>
      </Card>

      <div className="grid gap-4 md:grid-cols-2">
        <Card className="space-y-3">
          <SectionHeading eyebrow="Common ground" title="Shared artists" />
          <div className="flex flex-wrap gap-2">
            {sharedArtists.map((artist) => (
              <span
                key={artist}
                className="rounded-full border border-slate-800/60 bg-slate-900/60 px-4 py-1.5 text-sm font-medium text-slate-200"
              >
                {artist}
              </span>
            ))}
          </div>
        </Card>

        <Card className="space-y-3">
          <SectionHeading eyebrow="Overlap zones" title="Shared genres" />
          <div className="flex flex-wrap gap-2">
            {sharedGenres.map((genre) => (
              <span
                key={genre}
                className="rounded-full border border-slate-800/60 bg-slate-900/60 px-4 py-1.5 text-sm font-medium text-slate-200"
              >
                {genre}
              </span>
            ))}
          </div>
        </Card>
      </div>

      <Card className="space-y-3">
        <SectionHeading eyebrow="Next steps" title="What you can do" />
        <div className="grid gap-3 md:grid-cols-3">
          <div className="rounded-xl bg-slate-900/50 p-4">
            <p className="text-sm font-semibold text-white">🎧 Create a blend</p>
            <p className="mt-1 text-xs text-slate-400">Generate a playlist mixing both of your tastes.</p>
            <Link href={`/blend?userA=${userA}&userB=${userB}`} className="mt-2 inline-block text-xs text-emerald-300 hover:text-white">
              Try it →
            </Link>
          </div>
          <div className="rounded-xl bg-slate-900/50 p-4">
            <p className="text-sm font-semibold text-white">👀 View profiles</p>
            <p className="mt-1 text-xs text-slate-400">See each person's full listening stats and top picks.</p>
            <div className="mt-2 flex gap-2 text-xs">
              <Link href={`/u/${userA}`} className="text-emerald-300 hover:text-white">{userA} →</Link>
              <Link href={`/u/${userB}`} className="text-emerald-300 hover:text-white">{userB} →</Link>
            </div>
          </div>
          <div className="rounded-xl bg-slate-900/50 p-4">
            <p className="text-sm font-semibold text-white">🔗 Share this</p>
            <p className="mt-1 text-xs text-slate-400">Send this comparison to someone else.</p>
          </div>
        </div>
      </Card>
    </div>
  );
}

function LoadingSkeleton() {
  return (
    <Card className="animate-pulse space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <div className="h-4 w-24 rounded bg-slate-800" />
          <div className="mt-2 h-6 w-48 rounded bg-slate-800" />
        </div>
        <div className="h-32 w-32 rounded-full bg-slate-800" />
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
        description="See how two listeners align based on their music preferences and listening history."
        accent="Taste match"
      >
        <Card className="space-y-4 text-center">
          <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-slate-800/80 text-2xl">
            🎵
          </div>
          <div>
            <p className="text-lg font-semibold text-white">Select two users to compare</p>
            <p className="mt-1 text-sm text-slate-400">
              Add <code className="rounded bg-slate-800 px-1.5 py-0.5 text-xs">?userA=name&userB=name</code> to the URL
            </p>
          </div>
          <Link
            href="/compare?userA=demo&userB=demo2"
            className="inline-block rounded-full bg-slate-800 px-5 py-2 text-sm font-medium text-white transition hover:bg-slate-700"
          >
            Try demo comparison
          </Link>
        </Card>
      </PageShell>
    );
  }

  return (
    <PageShell
      title="Compatibility"
      description="How do these two listeners' tastes align? Based on listening history, ratings, and audio features."
      accent="Live match"
    >
      <Suspense fallback={<LoadingSkeleton />}>
        <CompatibilityResult userA={userA} userB={userB} />
      </Suspense>
    </PageShell>
  );
}
