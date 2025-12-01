import { Metadata } from 'next';

import { PageShell } from '../components/page-shell';
import { Card, SectionHeading } from '../components/ui';
import { fetchRecommendations, fetchTrending, type RecommendationItem, type TrendingItem } from '../../src/api/discover';

export const metadata: Metadata = {
  title: 'Sidetrack — Discover',
  description: 'Fresh recommendations tailored to your taste, plus trending picks from the club.',
};

async function getData(): Promise<{ recs: RecommendationItem[]; trending: TrendingItem[] }> {
  try {
    const [recs, trending] = await Promise.all([
      fetchRecommendations('demo'),
      fetchTrending().catch(() => []),
    ]);
    return { recs, trending };
  } catch {
    // Fallback demo content
    return {
      recs: [
        { type: 'album', id: 'a2', title: 'In Rainbows', artist_name: 'Radiohead', reason: 'valence match' },
        { type: 'album', id: 'a1', title: 'Random Access Memories', artist_name: 'Daft Punk', reason: 'danceability' },
        { type: 'track', id: 't1', title: 'Get Lucky', artist_name: 'Daft Punk', album_title: 'Random Access Memories' },
      ],
      trending: [
        { type: 'album', id: 'album-1', title: 'Spirit of Eden', artist_name: 'Talk Talk', average: 4.37, count: 24 },
        { type: 'album', id: 'album-2', title: 'Visions', artist_name: 'Grimes', average: 3.9, count: 18 },
        { type: 'album', id: 'album-3', title: 'Heat Rush', artist_name: 'Cloudy Friends', average: 3.6, count: 11 },
      ],
    };
  }
}

export default async function DiscoverPage() {
  const { recs, trending } = await getData();
  return (
    <PageShell
      title="Discover"
      description="Simple, transparent recommendations seeded by your listening and the club’s picks."
      accent="For You"
    >
      <div className="grid gap-4 md:grid-cols-3">
        <Card className="md:col-span-2">
          <SectionHeading eyebrow="Personalized" title="Recommended for you" />
          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            {recs.map((item) => (
              <RecommendationCard key={`${item.type}-${item.id}`} item={item} />)
            )}
          </div>
        </Card>
        <Card>
          <SectionHeading eyebrow="Trending" title="This week in the club" />
          <ul className="mt-3 space-y-2 text-sm">
            {trending.map((t) => (
              <li key={t.id} className="rounded-xl bg-slate-900 p-3">
                <div className="font-semibold text-white">{t.title} — {t.artist_name}</div>
                <div className="text-xs text-slate-400">{t.average ? `Average ${t.average}` : ''}{t.count ? ` • ${t.count} ratings` : ''}</div>
              </li>
            ))}
          </ul>
        </Card>
      </div>
    </PageShell>
  );
}

function RecommendationCard({ item }: { item: RecommendationItem }) {
  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-4">
      <div className="text-xs uppercase tracking-wide text-slate-400">{item.type === 'album' ? 'Album' : 'Track'}</div>
      <div className="mt-1 text-sm font-semibold text-white">{item.title}</div>
      <div className="text-xs text-slate-400">{item.artist_name}{'album_title' in item && item.album_title ? ` — ${item.album_title}` : ''}</div>
      {'reason' in item && item.reason && (
        <div className="mt-2 text-[0.7rem] text-emerald-300/80">Because of {item.reason}</div>
      )}
    </div>
  );
}
