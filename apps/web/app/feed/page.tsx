import Link from 'next/link';
import type { Route } from 'next';

import { fetchFeedWithFallback, type FeedItem } from '../../src/api/feed';
import { PageShell } from '../components/page-shell';
import { Card, SectionHeading } from '../components/ui';
import { RatingBadge } from '../components/rating-badge';

export const metadata = {
  title: 'Sidetrack — Feed',
  description: 'Recent club and friend activity.',
};

function formatTimeAgo(timestamp: string): string {
  const date = new Date(timestamp);
  if (Number.isNaN(date.getTime())) return 'Recently';
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  const diffHours = Math.floor(diffMins / 60);
  if (diffHours < 24) return `${diffHours}h ago`;
  const diffDays = Math.floor(diffHours / 24);
  return `${diffDays}d ago`;
}

function getEventColor(type: FeedItem['type']): { bg: string; text: string } {
  switch (type) {
    case 'rating':
      return { bg: 'rgba(251, 191, 36, 0.15)', text: '#fbbf24' };
    case 'listen':
      return { bg: 'rgba(52, 211, 153, 0.15)', text: '#34d399' };
    case 'follow':
      return { bg: 'rgba(244, 114, 182, 0.15)', text: '#f472b6' };
    case 'club':
    default:
      return { bg: 'rgba(59, 130, 246, 0.15)', text: '#60a5fa' };
  }
}

function FeedItemCard({ item }: { item: FeedItem }) {
  const color = getEventColor(item.type);

  return (
    <div className="group flex flex-col gap-3 rounded-2xl border border-slate-800/60 bg-slate-900/40 p-4 backdrop-blur-sm transition-all hover:border-slate-700/80 hover:bg-slate-900/60 sm:flex-row sm:items-center sm:justify-between">
      <div className="flex items-start gap-3">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-slate-800/80 text-sm font-semibold text-slate-200">
          {item.actor.charAt(0).toUpperCase()}
        </div>
        <div className="space-y-1">
          <p className="text-sm text-slate-200">
            <span className="font-semibold text-white">{item.actor}</span>{' '}
            <span className="text-slate-400">{item.action}</span>{' '}
            {item.target_link ? (
              <Link href={item.target_link as Route} className="font-medium text-emerald-300 transition-colors hover:text-white">
                {item.target}
              </Link>
            ) : item.target ? (
              <span className="font-medium text-white">{item.target}</span>
            ) : null}
          </p>
          <p className="text-xs text-slate-500">{formatTimeAgo(item.timestamp)}</p>
        </div>
      </div>
      <div className="flex items-center gap-3 pl-13 sm:pl-0">
        {item.rating != null && <RatingBadge value={item.rating} />}
        <span
          className="rounded-full px-3 py-1 text-[0.65rem] font-semibold uppercase tracking-wider"
          style={{ background: color.bg, color: color.text }}
        >
          {item.type}
        </span>
      </div>
    </div>
  );
}

export default async function FeedPage() {
  const feed = await fetchFeedWithFallback();

  return (
    <PageShell
      title="Activity feed"
      description="See what friends are rating, listening to, and celebrating. Live updates once you link Discord and Spotify."
      accent="Live"
    >
      <Card className="space-y-5">
        <SectionHeading eyebrow="Recent activity" title="Club + friends" />
        <div className="space-y-3">
          {feed.length > 0 ? (
            feed.map((item) => <FeedItemCard key={item.id} item={item} />)
          ) : (
            <div className="rounded-2xl border border-slate-800/60 bg-slate-900/40 p-6 text-center">
              <p className="text-sm text-slate-400">No activity yet. Rate an album or follow a friend to see updates here.</p>
            </div>
          )}
        </div>
        <p className="text-xs text-slate-500">
          Hook up Spotify or Last.fm for listening events. Presence indicators and now-playing badges appear once accounts are linked.
        </p>
      </Card>
    </PageShell>
  );
}
