import Link from 'next/link';

import { PageShell } from './components/page-shell';
import { Card, SectionHeading } from './components/ui';

export const metadata = {
  title: 'Sidetrack — Music tracker & social',
  description:
    'Track what you listen to, compare tastes with friends, and browse the Sidetrack Club archive — all in one sleek place.',
};

export default function Home() {
  return (
    <PageShell
      accent="Tracker + social"
      title="Track your music. Find your people."
      description="Sidetrack is a modern music tracker with a social feed and taste tools — plus a public archive of our Discord album club. Link Spotify/Last.fm to light it up."
      actions={
        <div className="flex gap-2">
          <Link
            href="/feed"
            className="rounded-full bg-slate-100 px-4 py-2 text-sm font-semibold text-sidetrack-bg shadow-soft transition hover:brightness-95"
          >
            Open feed
          </Link>
          <Link
            href="/login"
            className="rounded-full border border-slate-700/70 bg-slate-900/80 px-4 py-2 text-sm font-semibold text-slate-100 transition hover:bg-slate-800/80"
          >
            Sign in
          </Link>
        </div>
      }
    >
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
        <Card className="h-full">
          <SectionHeading eyebrow="Profiles" title="Your listening, visualized" />
          <ul className="mt-3 space-y-2 text-sm text-slate-300">
            <li>• Top artists, albums, and genres over time.</li>
            <li>• Ratings and short reviews with sleek badges.</li>
            <li>• Mood vectors from Spotify audio features.</li>
          </ul>
          <div className="mt-4">
            <Link href={{ pathname: '/u/[id]', query: { id: 'demo' } }} className="text-emerald-200 hover:text-white">
              View demo profile →
            </Link>
          </div>
        </Card>

        <Card className="h-full">
          <SectionHeading eyebrow="Social" title="Feed and compatibility" />
          <ul className="mt-3 space-y-2 text-sm text-slate-300">
            <li>• Live feed of friends’ listens and ratings.</li>
            <li>• “Taste match” comparisons and overlaps.</li>
            <li>• Friend‑blend ideas and playlist seeds.</li>
          </ul>
          <div className="mt-4 flex items-center gap-4">
            <Link href="/feed" className="text-emerald-200 hover:text-white">
              Open feed →
            </Link>
            <Link href={{ pathname: '/compare', query: { userA: 'demo', userB: 'demo2' } }} className="text-emerald-200 hover:text-white">
              Try compatibility →
            </Link>
          </div>
        </Card>

        <Card className="h-full">
          <SectionHeading eyebrow="Club" title="Sidetrack Club archive" />
          <p className="mt-3 text-sm text-slate-300">
            Explore every week of the Discord album club: winners, tags, ratings, filters, and participation stats.
          </p>
          <div className="mt-4">
            <Link href="/club" className="text-emerald-200 hover:text-white">
              Browse the archive →
            </Link>
          </div>
        </Card>
      </div>

      <Card className="mt-2">
        <SectionHeading eyebrow="Get set up" title="Link Spotify or Last.fm in Settings" />
        <p className="mt-2 text-sm text-slate-300">
          Once you sign in, head to Settings to connect accounts. We’ll pull in recent listens and compute your taste
          profile automatically.
        </p>
        <div className="mt-4">
          <Link href="/settings" className="text-emerald-200 hover:text-white">
            Go to Settings →
          </Link>
        </div>
      </Card>
    </PageShell>
  );
}
