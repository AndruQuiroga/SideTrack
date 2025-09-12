'use client';

import Link from 'next/link';
import { Sparkles, ChevronRight, Compass, Flame, Music, TrendingUp } from 'lucide-react';
import KpiCard from '../../components/dashboard/KpiCard';
import InsightCard from '../../components/dashboard/InsightCard';
import QuickActions from '../../components/dashboard/QuickActions';
import Skeleton from '../../components/Skeleton';
import { Card } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { useDashboard, useRecentListens, useTopTags, useTrajectory } from '../../lib/query';

function VibeSummary({ lastArtist }: { lastArtist: string }) {
  return (
    <Card
      variant="glass"
      className="relative overflow-hidden p-6 md:p-8 flex flex-col justify-between min-h-[180px]"
    >
      <div className="absolute -right-10 -top-10 h-40 w-40 rounded-full bg-gradient-to-br from-emerald-400/70 via-teal-400/60 to-cyan-400/60 blur-3xl" />
      <div className="flex items-center gap-2 text-emerald-300">
        <Sparkles size={18} />
        <span className="text-xs uppercase tracking-wider">Today’s Vibe</span>
      </div>
      <div className="mt-3 text-2xl md:text-3xl font-semibold">
        Ride the wave — your mood is trending up
      </div>
      <div className="mt-2 text-sm text-muted-foreground">
        Last played artist: <span className="text-foreground font-medium">{lastArtist || '—'}</span>
      </div>
      <div className="mt-4">
        <Link
          href="/trajectory"
          className="inline-flex items-center text-sm text-emerald-300 hover:text-emerald-200"
        >
          View trajectory <ChevronRight size={16} className="ml-1" />
        </Link>
      </div>
    </Card>
  );
}

function MiniTrajectory() {
  const { data } = useTrajectory();
  const points = data?.points ?? [];
  return (
    <Card variant="glass" className="p-4 md:p-6">
      <div className="flex items-center gap-2 text-violet-300">
        <TrendingUp size={18} />
        <span className="text-xs uppercase tracking-wider">Trajectory</span>
      </div>
      <svg viewBox="0 0 100 40" className="mt-3 h-24 w-full">
        <defs>
          <linearGradient id="traj-grad" x1="0" x2="1">
            <stop offset="0%" stopColor="rgba(167,139,250,0.8)" />
            <stop offset="100%" stopColor="rgba(244,114,182,0.6)" />
          </linearGradient>
        </defs>
        {points.length > 1 && (
          <path
            d={`M${points
              .map((p, i) => `${(i / (points.length - 1)) * 100},${40 - p.y * 40}`)
              .join(' L')}`}
            fill="none"
            stroke="url(#traj-grad)"
            strokeWidth={2.5}
            strokeLinecap="round"
          />
        )}
      </svg>
      <div className="mt-2 text-xs text-muted-foreground">Valence vs Energy over recent weeks</div>
    </Card>
  );
}

function RecentActivity() {
  const { data } = useRecentListens(6);
  const listens = data?.listens ?? [];
  return (
    <Card variant="glass" className="p-4 md:p-6">
      <div className="flex items-center gap-2 text-amber-300">
        <Music size={18} />
        <span className="text-xs uppercase tracking-wider">Recent activity</span>
      </div>
      <ul className="mt-3 space-y-2">
        {listens.map((l) => (
          <li
            key={`${l.track_id}-${l.played_at}`}
            className="flex items-center justify-between text-sm"
          >
            <span className="truncate max-w-[70%]">
              {l.title}{' '}
              <span className="text-muted-foreground">{l.artist ? `– ${l.artist}` : ''}</span>
            </span>
            <span className="text-xs text-muted-foreground">
              {new Date(l.played_at).toLocaleDateString()}
            </span>
          </li>
        ))}
        {listens.length === 0 && (
          <li className="text-sm text-muted-foreground">No listens yet — play something!</li>
        )}
      </ul>
    </Card>
  );
}

function DiscoverRow() {
  const tiles = [
    {
      href: '/recommendations',
      title: 'Fresh picks',
      icon: <Flame size={16} />,
      grad: 'from-rose-400/70 to-orange-400/70',
    },
    {
      href: '/explore',
      title: 'Explore moods',
      icon: <Compass size={16} />,
      grad: 'from-sky-400/70 to-emerald-400/70',
    },
  ];
  return (
    <div className="grid gap-4 @[700px]:grid-cols-2">
      {tiles.map((t) => (
        <Card key={t.title} variant="glass" className="relative overflow-hidden p-5">
          <div
            className={`absolute -right-8 -top-10 h-24 w-24 rounded-full bg-gradient-to-br ${t.grad} blur-2xl`}
          />
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-sm">
              {t.icon}
              <span>{t.title}</span>
            </div>
            <Button asChild variant="outline" size="sm" className="backdrop-blur bg-white/5">
              <Link href={t.href}>Open</Link>
            </Button>
          </div>
        </Card>
      ))}
    </div>
  );
}

function TopTagsCloud() {
  const { data, isLoading } = useTopTags(12, 90);
  const tags = data?.tags ?? [];
  return (
    <Card variant="glass" className="p-4 md:p-6">
      <div className="flex items-center gap-2 text-cyan-300">
        <Compass size={18} />
        <span className="text-xs uppercase tracking-wider">Top tags</span>
      </div>
      <div className="mt-3 flex flex-wrap gap-2">
        {isLoading
          ? Array.from({ length: 8 }, (_, i) => (
              <span key={i} className="h-6 w-16 animate-pulse rounded-full bg-white/5" />
            ))
          : tags.map((t, idx) => (
              <span
                key={t.name}
                className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs text-foreground/90 backdrop-blur"
                title={`${t.count} mentions`}
                style={{ opacity: 1 - Math.min(idx, 10) * 0.05 }}
              >
                {t.name}
              </span>
            ))}
        {!isLoading && tags.length === 0 && (
          <span className="text-sm text-muted-foreground">
            No tags yet — sync Last.fm to see yours
          </span>
        )}
      </div>
    </Card>
  );
}

export default function DashboardPage() {
  const { data, isLoading, error } = useDashboard();

  if (error) {
    return (
      <section className="@container space-y-6">
        <p className="text-sm text-rose-400">
          Failed to load dashboard: {(error as Error).message}
        </p>
      </section>
    );
  }

  return (
    <section className="@container space-y-6">
      {/* Hero row: Vibe summary + Quick actions */}
      <div className="grid gap-4 @[900px]:grid-cols-3">
        <div className="@[900px]:col-span-2">
          {isLoading ? (
            <Skeleton className="h-44" />
          ) : (
            <VibeSummary lastArtist={data?.lastArtist ?? ''} />
          )}
        </div>
        <div>
          {isLoading ? (
            <Skeleton className="h-44" />
          ) : (
            <QuickActions lastArtist={data?.lastArtist ?? ''} />
          )}
        </div>
      </div>

      {/* Trends & activity */}
      <div className="grid gap-4 @[1200px]:grid-cols-3">
        <div className="@[1200px]:col-span-2 grid gap-4 @[900px]:grid-cols-2">
          {isLoading ? <Skeleton className="h-40" /> : <MiniTrajectory />}
          {isLoading ? <Skeleton className="h-40" /> : <TopTagsCloud />}
        </div>
        <div>{isLoading ? <Skeleton className="h-40" /> : <RecentActivity />}</div>
      </div>

      {/* Insights carousel */}
      <div className="flex gap-4 overflow-x-auto pb-2">
        {isLoading
          ? [1, 2, 3].map((i) => <Skeleton key={i} className="h-24 min-w-[220px]" />)
          : (data?.insights || []).map((ins) => <InsightCard key={ins.id} insight={ins} />)}
      </div>

      {/* Subtle KPIs */}
      <div className="grid gap-4 @[700px]:grid-cols-3">
        {isLoading
          ? [1, 2, 3].map((i) => <Skeleton key={i} className="h-24" />)
          : (data?.kpis || []).map((kpi) => <KpiCard key={kpi.id} kpi={kpi} />)}
      </div>

      {/* Discover shortcuts */}
      <DiscoverRow />
    </section>
  );
}
