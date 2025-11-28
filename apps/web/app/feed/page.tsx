import Link from 'next/link';

import { PageShell } from '../components/page-shell';
import { Card, SectionHeading } from '../components/ui';
import { RatingBadge } from '../components/rating-badge';

interface FeedItem {
  id: string;
  actor: string;
  action: string;
  target?: string;
  targetLink?: string;
  rating?: number;
  timestamp: string;
  type: 'rating' | 'listen' | 'club';
}

const demoFeed: FeedItem[] = [
  {
    id: '1',
    actor: 'lydia',
    action: 'rated',
    target: 'Spirit of Eden',
    rating: 4.5,
    timestamp: '5m ago',
    type: 'rating',
  },
  {
    id: '2',
    actor: 'arden',
    action: 'is now playing',
    target: 'Open My Eyes · Yeule',
    timestamp: '12m ago',
    type: 'listen',
  },
  {
    id: '3',
    actor: 'bot',
    action: 'announced winner for WEEK 003',
    target: 'Join the ratings thread',
    targetLink: '/club/weeks/week-demo-3',
    timestamp: '1h ago',
    type: 'club',
  },
  {
    id: '4',
    actor: 'demo',
    action: 'followed you back',
    timestamp: '2h ago',
    type: 'club',
  },
];

export const metadata = {
  title: 'Sidetrack — Feed',
  description: 'Recent club and friend activity.',
};

export default function FeedPage() {
  return (
    <PageShell
      title="Activity feed"
      description="See what friends are rating, listening to, and celebrating. The feed turns live once you link Discord and Spotify."
      accent="Social preview"
    >
      <Card className="space-y-4">
        <SectionHeading eyebrow="Live surface" title="Club + friends" />
        <div className="space-y-3">
          {demoFeed.map((item) => (
            <div
              key={item.id}
              className="flex flex-col gap-2 rounded-2xl border border-slate-800/70 bg-slate-900/60 p-4 sm:flex-row sm:items-center sm:justify-between"
            >
              <div className="space-y-1">
                <p className="text-sm text-slate-200">
                  <span className="font-semibold text-white">{item.actor}</span> {item.action}{' '}
                  {item.targetLink ? (
                    <Link href={item.targetLink} className="text-emerald-200 hover:text-white">
                      {item.target}
                    </Link>
                  ) : (
                    <span className="font-medium text-white">{item.target}</span>
                  )}
                </p>
                <p className="text-xs text-slate-400">{item.timestamp}</p>
              </div>
              <div className="flex items-center gap-3">
                {item.rating && <RatingBadge value={item.rating} />}
                <span
                  className="rounded-full px-3 py-1 text-[0.7rem] font-semibold uppercase tracking-wide"
                  style={{
                    background:
                      item.type === 'rating'
                        ? 'rgba(251, 191, 36, 0.15)'
                        : item.type === 'listen'
                          ? 'rgba(52, 211, 153, 0.15)'
                          : 'rgba(59, 130, 246, 0.15)',
                    color: item.type === 'rating' ? '#fbbf24' : item.type === 'listen' ? '#34d399' : '#60a5fa',
                  }}
                >
                  {item.type}
                </span>
              </div>
            </div>
          ))}
        </div>
        <p className="text-xs text-slate-400">
          Hook up Spotify/Last.fm for listening events and keep Discord open for live club reactions. We surface presence indicators and now playing
          once accounts are linked.
        </p>
      </Card>
    </PageShell>
  );
}
