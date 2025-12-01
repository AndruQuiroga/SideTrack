import { Metadata } from 'next';
import Link from 'next/link';

import { PageShell } from '../components/page-shell';
import { Card, SectionHeading } from '../components/ui';
import { RatingBadge } from '../components/rating-badge';
import { fetchRecommendations, fetchTrending, type RecommendationItem, type TrendingItem } from '../../src/api/discover';

export const metadata: Metadata = {
  title: 'Sidetrack — Discover',
  description: 'Fresh recommendations tailored to your taste, plus trending picks from the club.',
};

async function getData(): Promise<{ recs: RecommendationItem[]; trending: TrendingItem[]; source: 'api' | 'fallback' }> {
  try {
    const [recs, trending] = await Promise.all([
      fetchRecommendations('demo'),
      fetchTrending().catch(() => []),
    ]);
    return { recs, trending, source: 'api' };
  } catch {
    // Fallback demo content
    return {
      recs: [
        { type: 'album', id: 'a2', title: 'In Rainbows', artist_name: 'Radiohead', reason: 'valence match' },
        { type: 'album', id: 'a1', title: 'Random Access Memories', artist_name: 'Daft Punk', reason: 'danceability' },
        { type: 'track', id: 't1', title: 'Get Lucky', artist_name: 'Daft Punk', album_title: 'Random Access Memories' },
        { type: 'album', id: 'a3', title: 'Vespertine', artist_name: 'Björk', reason: 'mood similarity' },
        { type: 'album', id: 'a4', title: 'Endtroducing...', artist_name: 'DJ Shadow', reason: 'tempo match' },
      ],
      trending: [
        { type: 'album', id: 'album-1', title: 'Spirit of Eden', artist_name: 'Talk Talk', average: 4.37, count: 24 },
        { type: 'album', id: 'album-2', title: 'Visions', artist_name: 'Grimes', average: 3.9, count: 18 },
        { type: 'album', id: 'album-3', title: 'Heat Rush', artist_name: 'Cloudy Friends', average: 3.6, count: 11 },
      ],
      source: 'fallback',
    };
  }
}

function RecommendationCard({ item, index }: { item: RecommendationItem; index: number }) {
  const isAlbum = item.type === 'album';
  
  return (
    <div className="group relative overflow-hidden rounded-2xl border border-slate-800/60 bg-gradient-to-br from-slate-900/80 to-slate-900/40 p-4 backdrop-blur-sm transition-all hover:border-slate-700/80 hover:from-slate-900/90 hover:to-slate-800/50">
      <div className="absolute -right-8 -top-8 h-24 w-24 rounded-full bg-gradient-to-br from-purple-500/10 via-sky-500/5 to-transparent blur-2xl transition-all group-hover:from-purple-500/15" />
      <div className="relative">
        <div className="flex items-center gap-2">
          <span className="flex h-6 w-6 items-center justify-center rounded-full bg-slate-800/80 text-[0.65rem] font-semibold text-slate-400">
            {index + 1}
          </span>
          <span className="rounded-full bg-slate-800/60 px-2 py-0.5 text-[0.6rem] font-semibold uppercase tracking-wider text-slate-400">
            {isAlbum ? 'Album' : 'Track'}
          </span>
        </div>
        <h3 className="mt-2 text-sm font-semibold text-white">{item.title}</h3>
        <p className="text-xs text-slate-400">
          {item.artist_name}
          {'album_title' in item && item.album_title && (
            <span className="text-slate-500"> · {item.album_title}</span>
          )}
        </p>
        {'reason' in item && item.reason && (
          <p className="mt-2 text-[0.7rem] text-emerald-300/80">
            <span className="mr-1">✨</span>
            {item.reason}
          </p>
        )}
      </div>
    </div>
  );
}

function TrendingCard({ item, rank }: { item: TrendingItem; rank: number }) {
  return (
    <div className="group flex items-center gap-3 rounded-xl border border-slate-800/40 bg-slate-900/50 p-3 transition-all hover:border-slate-700/60 hover:bg-slate-900/70">
      <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-purple-500/20 to-sky-500/20 text-sm font-bold text-white">
        {rank}
      </span>
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-semibold text-white">{item.title}</p>
        <p className="text-xs text-slate-400">{item.artist_name}</p>
      </div>
      <div className="text-right">
        {item.average != null && <RatingBadge value={item.average} />}
        {item.count != null && <p className="mt-1 text-[0.65rem] text-slate-500">{item.count} ratings</p>}
      </div>
    </div>
  );
}

export default async function DiscoverPage() {
  const { recs, trending, source } = await getData();
  
  return (
    <PageShell
      title="Discover"
      description="Personalized recommendations based on your listening and the club's top picks."
      accent="For You"
    >
      <div className="grid gap-5 lg:grid-cols-[1.5fr,1fr]">
        <Card className="space-y-4">
          <SectionHeading eyebrow="Personalized" title="Recommended for you" />
          {recs.length > 0 ? (
            <div className="grid gap-3 sm:grid-cols-2">
              {recs.map((item, index) => (
                <RecommendationCard key={`${item.type}-${item.id}`} item={item} index={index} />
              ))}
            </div>
          ) : (
            <div className="rounded-2xl border border-slate-800/60 bg-slate-900/40 p-6 text-center">
              <p className="text-sm text-slate-400">Link your Spotify or Last.fm to get personalized recommendations.</p>
              <Link href="/settings" className="mt-2 inline-block text-sm text-emerald-300 hover:text-white">
                Go to settings →
              </Link>
            </div>
          )}
          {source === 'fallback' && (
            <p className="text-xs text-slate-500">
              Showing sample recommendations. Connect Spotify or Last.fm for personalized picks.
            </p>
          )}
        </Card>

        <Card className="space-y-4">
          <SectionHeading eyebrow="Club picks" title="Trending this week" />
          {trending.length > 0 ? (
            <div className="space-y-2">
              {trending.map((item, index) => (
                <TrendingCard key={item.id} item={item} rank={index + 1} />
              ))}
            </div>
          ) : (
            <p className="text-sm text-slate-400">No trending albums this week yet.</p>
          )}
          <Link href="/club" className="inline-block text-sm text-emerald-300 hover:text-white">
            Browse full archive →
          </Link>
        </Card>
      </div>

      <Card className="mt-1 space-y-3">
        <SectionHeading eyebrow="How it works" title="Transparent recommendations" />
        <div className="grid gap-4 md:grid-cols-3">
          <div className="rounded-xl bg-slate-900/50 p-4">
            <p className="text-sm font-semibold text-white">🎵 Your taste</p>
            <p className="mt-1 text-xs text-slate-400">
              We analyze your listening history for mood, energy, and genre patterns.
            </p>
          </div>
          <div className="rounded-xl bg-slate-900/50 p-4">
            <p className="text-sm font-semibold text-white">📊 Club data</p>
            <p className="mt-1 text-xs text-slate-400">
              Highly-rated albums and nominations influence what we suggest.
            </p>
          </div>
          <div className="rounded-xl bg-slate-900/50 p-4">
            <p className="text-sm font-semibold text-white">🔍 No black boxes</p>
            <p className="mt-1 text-xs text-slate-400">
              Each recommendation shows why it was picked, so you know what's driving it.
            </p>
          </div>
        </div>
      </Card>
    </PageShell>
  );
}
