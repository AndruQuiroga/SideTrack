import Link from 'next/link';

import { fetchWeekListWithFallback } from '../src/api/weeks';
import { PageShell } from './components/page-shell';
import { Card, SectionHeading } from './components/ui';
import { RatingBadge } from './components/rating-badge';

export const metadata = {
  title: 'Sidetrack — Music tracker & social',
  description:
    'Track what you listen to, compare tastes with friends, and browse the Sidetrack Club archive — all in one sleek place.',
};

export default async function Home() {
  let latestWeek = null;
  try {
    const weeks = await fetchWeekListWithFallback();
    if (weeks && weeks.length > 0) {
      latestWeek = weeks[0];
    }
  } catch {
    // Fallback gracefully
  }

  return (
    <PageShell
      accent="Welcome to Sidetrack"
      title="Track your music. Find your people."
      description="A modern music tracker with social features and our Discord album club archive. Link Spotify or Last.fm to unlock everything."
      actions={
        <div className="flex flex-wrap gap-2">
          <Link
            href="/discover"
            className="rounded-full bg-gradient-to-r from-purple-500 to-emerald-400 px-5 py-2.5 text-sm font-semibold text-white shadow-lg transition hover:opacity-90"
          >
            Start discovering
          </Link>
          <Link
            href="/login"
            className="rounded-full border border-slate-700/70 bg-slate-900/80 px-5 py-2.5 text-sm font-semibold text-slate-100 transition hover:bg-slate-800/80"
          >
            Sign in
          </Link>
        </div>
      }
    >
      {/* Hero features grid */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <Card className="group relative overflow-hidden">
          <div className="absolute -right-12 -top-12 h-32 w-32 rounded-full bg-gradient-to-br from-purple-500/20 to-transparent blur-2xl transition-all group-hover:from-purple-500/30" />
          <div className="relative">
            <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-xl bg-purple-500/20 text-lg">
              🎧
            </div>
            <SectionHeading eyebrow="Track" title="Your listening stats" />
            <p className="mt-3 text-sm text-slate-400">
              Top artists, albums, genres over time. Mood and energy patterns from audio features. Beautiful graphs and timelines.
            </p>
            <Link href="/u/demo" className="mt-4 inline-flex items-center gap-1 text-sm text-emerald-300 transition-colors hover:text-white">
              View demo profile <span aria-hidden>→</span>
            </Link>
          </div>
        </Card>

        <Card className="group relative overflow-hidden">
          <div className="absolute -right-12 -top-12 h-32 w-32 rounded-full bg-gradient-to-br from-sky-500/20 to-transparent blur-2xl transition-all group-hover:from-sky-500/30" />
          <div className="relative">
            <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-xl bg-sky-500/20 text-lg">
              🤝
            </div>
            <SectionHeading eyebrow="Connect" title="Social feed & matches" />
            <p className="mt-3 text-sm text-slate-400">
              See what friends are listening to. Get taste compatibility scores. Create blend playlists together.
            </p>
            <div className="mt-4 flex flex-wrap gap-3">
              <Link href="/feed" className="text-sm text-emerald-300 transition-colors hover:text-white">
                Open feed →
              </Link>
              <Link href="/compare?userA=demo&userB=demo2" className="text-sm text-emerald-300 transition-colors hover:text-white">
                Try matching →
              </Link>
            </div>
          </div>
        </Card>

        <Card className="group relative overflow-hidden">
          <div className="absolute -right-12 -top-12 h-32 w-32 rounded-full bg-gradient-to-br from-emerald-500/20 to-transparent blur-2xl transition-all group-hover:from-emerald-500/30" />
          <div className="relative">
            <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-500/20 text-lg">
              🏆
            </div>
            <SectionHeading eyebrow="Club" title="Weekly album picks" />
            <p className="mt-3 text-sm text-slate-400">
              Browse our Discord album club archive. See winners, ratings, poll results, and join the listening sessions.
            </p>
            <Link href="/club" className="mt-4 inline-flex items-center gap-1 text-sm text-emerald-300 transition-colors hover:text-white">
              Browse archive <span aria-hidden>→</span>
            </Link>
          </div>
        </Card>
      </div>

      {/* Latest week highlight */}
      {latestWeek && latestWeek.nominations && latestWeek.nominations.length > 0 && (
        <Card className="relative overflow-hidden">
          <div className="absolute -left-20 -top-20 h-40 w-40 rounded-full bg-gradient-to-br from-purple-500/15 via-sky-500/10 to-transparent blur-3xl" />
          <div className="relative grid gap-5 md:grid-cols-[1fr,auto]">
            <div>
              <SectionHeading eyebrow="Latest from the club" title={latestWeek.label} />
              <div className="mt-3 space-y-2">
                <p className="text-lg font-semibold text-white">
                  {latestWeek.nominations[0]?.pitch ?? 'Winner pending'}
                </p>
                <div className="flex flex-wrap items-center gap-2 text-xs">
                  {[latestWeek.nominations[0]?.genre, latestWeek.nominations[0]?.decade, latestWeek.nominations[0]?.country]
                    .filter(Boolean)
                    .map((tag) => (
                      <span key={tag as string} className="rounded-full bg-slate-800/80 px-3 py-1 text-slate-300">
                        {tag as string}
                      </span>
                    ))}
                  <span className="rounded-full bg-slate-800/60 px-3 py-1 text-slate-400">
                    {latestWeek.aggregates?.vote_count ?? 0} votes · {latestWeek.aggregates?.rating_count ?? 0} ratings
                  </span>
                </div>
              </div>
              <Link
                href={`/club/weeks/${latestWeek.id}`}
                className="mt-4 inline-flex items-center gap-1 text-sm font-medium text-emerald-300 transition-colors hover:text-white"
              >
                View full week <span aria-hidden>→</span>
              </Link>
            </div>
            <div className="flex items-center">
              <RatingBadge
                value={latestWeek.rating_summary?.average ?? latestWeek.aggregates?.rating_average}
                count={latestWeek.rating_summary?.count ?? latestWeek.aggregates?.rating_count}
              />
            </div>
          </div>
        </Card>
      )}

      {/* Get started */}
      <Card className="border-slate-800/40 bg-gradient-to-br from-slate-900/50 to-slate-900/30">
        <div className="grid gap-4 md:grid-cols-[1fr,auto]">
          <div>
            <SectionHeading eyebrow="Get started" title="Link your music services" />
            <p className="mt-2 text-sm text-slate-400">
              Connect Spotify or Last.fm to unlock listening stats, taste profiles, and personalized recommendations.
              Discord linking enables club participation.
            </p>
          </div>
          <div className="flex items-center">
            <Link
              href="/settings"
              className="rounded-full border border-slate-700/70 bg-slate-800/80 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-slate-700/80"
            >
              Open settings
            </Link>
          </div>
        </div>
      </Card>
    </PageShell>
  );
}
