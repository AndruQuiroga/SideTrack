'use client';

import Link from 'next/link';
import React from 'react';
import { Sparkles, ChevronRight, Compass, Flame, Music, TrendingUp, Play, Zap } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import KpiCard from '../../components/dashboard/KpiCard';
import InsightCard from '../../components/dashboard/InsightCard';
import QuickActions from '../../components/dashboard/QuickActions';
import Skeleton from '../../components/Skeleton';
import { Card } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { useDashboard, useRecentListens, useTopTags, useTrajectory } from '../../lib/query';

function VibeSummary({ lastArtist }: { lastArtist: string }) {
  return (
    <Card variant="glass" className="relative min-h-[180px] overflow-hidden p-6 md:p-8">
      <div className="absolute -right-10 -top-10 h-40 w-40 rounded-full bg-gradient-to-br from-emerald-400/70 via-teal-400/60 to-cyan-400/60 blur-3xl" />
      <div className="flex items-center gap-2 text-emerald-300">
        <Sparkles size={18} />
        <span className="text-xs uppercase tracking-wider">Today’s Vibe</span>
      </div>
      <div className="mt-3 text-2xl font-semibold md:text-3xl">
        Ride the wave — your mood is trending up
      </div>
      <div className="mt-2 text-sm text-muted-foreground">
        Last played artist: <span className="font-medium text-foreground">{lastArtist || '—'}</span>
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

function FeatureMixtape() {
  return (
    <Card variant="glass" className="relative overflow-hidden p-4 md:p-6">
      <div className="absolute -right-10 -bottom-10 h-28 w-28 rounded-full bg-gradient-to-br from-fuchsia-400/70 via-pink-400/60 to-rose-400/60 blur-2xl" />
      <div className="flex items-center gap-2 text-pink-300">
        <Zap size={18} />
        <span className="text-xs uppercase tracking-wider">Instant Mixtape</span>
      </div>
      <div className="mt-2 text-lg font-semibold">60‑minute flow</div>
      <p className="mt-1 text-sm text-muted-foreground">Auto‑curated from your recent energy</p>
      <div className="mt-3">
        <Button asChild size="sm" className="gap-2">
          <Link href="/mixtape?duration=60">
            <Play size={14} /> Play mix
          </Link>
        </Button>
      </div>
    </Card>
  );
}

function MiniTrajectory() {
  const { data } = useTrajectory();
  const points = data?.points ?? [];
  const pathD =
    points.length > 1
      ? `M${points.map((p, i) => `${(i / (points.length - 1)) * 100},${40 - p.y * 40}`).join(' L')}`
      : '';
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
        {pathD && (
          <motion.path
            key={`traj-${points.length}`}
            d={pathD}
            fill="none"
            stroke="url(#traj-grad)"
            strokeWidth={2.5}
            strokeLinecap="round"
            initial={{ pathLength: 0, opacity: 0.6 }}
            animate={{ pathLength: 1, opacity: 1 }}
            transition={{ duration: 0.8, ease: 'easeInOut' }}
          />
        )}
      </svg>
      <div className="mt-2 text-xs text-muted-foreground">Valence vs Energy over recent weeks</div>
    </Card>
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
                className="chip-shimmer rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs text-foreground/90 backdrop-blur"
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
            <span className="max-w-[70%] truncate">
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

function ConnectTile() {
  return (
    <Card variant="glass" className="p-4 md:p-6">
      <div className="text-xs uppercase tracking-wider text-muted-foreground">Connect & sync</div>
      <div className="mt-2 text-sm">Hook up Spotify or Last.fm to unlock more insights</div>
      <div className="mt-3">
        <Button asChild variant="outline" size="sm" className="backdrop-blur bg-white/5">
          <Link href="/settings">Open settings</Link>
        </Button>
      </div>
    </Card>
  );
}

function CuratedMixes() {
  const mixes = [
    {
      title: 'Chill Bloom',
      grad: 'from-emerald-400/70 to-cyan-400/70',
      href: '/recommendations?mood=chill',
    },
    {
      title: 'Pulse Driver',
      grad: 'from-violet-400/70 to-pink-400/70',
      href: '/recommendations?mood=energetic',
    },
    {
      title: 'Late Night',
      grad: 'from-amber-400/70 to-rose-400/70',
      href: '/recommendations?mood=late',
    },
  ];
  return (
    <div>
      <div className="mb-2 text-xs uppercase tracking-wider text-muted-foreground">
        Curated mixes
      </div>
      <div className="grid gap-4 @[900px]:grid-cols-3">
        {mixes.map((m, idx) => (
          <motion.div
            key={m.title}
            initial={{ opacity: 0, y: 8 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, amount: 0.4 }}
            transition={{ duration: 0.35, ease: 'easeOut', delay: idx * 0.05 }}
          >
            <Card variant="glass" className="relative overflow-hidden p-5">
              <div
                className={`absolute -right-8 -top-10 h-24 w-24 rounded-full bg-gradient-to-br ${m.grad} blur-2xl`}
              />
              <div className="flex items-center justify-between">
                <div className="text-sm font-medium">{m.title}</div>
                <Button asChild size="sm" className="gap-2">
                  <Link href={m.href}>
                    <Play size={14} /> Play
                  </Link>
                </Button>
              </div>
            </Card>
          </motion.div>
        ))}
      </div>
    </div>
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
      {tiles.map((t, idx) => (
        <motion.div
          key={t.title}
          initial={{ opacity: 0, y: 8 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.5 }}
          transition={{ duration: 0.35, ease: 'easeOut', delay: idx * 0.05 }}
          whileHover={{ y: -2, scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          className="will-change-transform"
        >
          <Card variant="glass" className="relative overflow-hidden p-5">
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
        </motion.div>
      ))}
    </div>
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
    <section className="relative @container space-y-8">
      {/* Ambient background accents */}
      <div className="pointer-events-none absolute inset-0 -z-10 overflow-hidden">
        <div className="absolute -top-24 -left-16 h-64 w-64 rounded-full bg-gradient-to-br from-emerald-500/20 via-teal-400/10 to-cyan-400/10 blur-3xl" />
        <div className="absolute -bottom-24 -right-16 h-64 w-64 rounded-full bg-gradient-to-br from-fuchsia-400/10 via-pink-400/10 to-rose-400/10 blur-3xl" />
      </div>

      {/* Hero header */}
      <div className="flex flex-col gap-2">
        {(() => {
          const TITLES = [
            'Your Sound, Evolving',
            'Find Your Flow',
            'Taste in Motion',
            'Vibes in Color',
            'Music, Mapped',
          ];
          const title = React.useMemo(() => TITLES[Math.floor(Math.random() * TITLES.length)], []);
          return (
            <h1 className="inline-block bg-gradient-to-r from-emerald-400 via-cyan-400 to-fuchsia-400 bg-clip-text text-3xl font-extrabold tracking-tight text-transparent md:text-4xl animate-gradient">
              {title}
            </h1>
          );
        })()}
        <p className="text-sm text-muted-foreground">
          A playful snapshot of your listening energy, momentum, and flavor.
        </p>
      </div>

      {/* Feature row: banner + actions */}
      <div className="grid gap-4 @[1000px]:grid-cols-3">
        <div className="@[1000px]:col-span-2">
          {isLoading ? (
            <Skeleton className="h-48" />
          ) : (
            <VibeSummary lastArtist={data?.lastArtist ?? ''} />
          )}
        </div>
        <div className="flex flex-col gap-4">
          {isLoading ? <Skeleton className="h-24" /> : <FeatureMixtape />}
          {isLoading ? (
            <Skeleton className="h-24" />
          ) : (
            <QuickActions lastArtist={data?.lastArtist ?? ''} />
          )}
        </div>
      </div>

      {/* Trends & activity packed row */}
      <div className="grid gap-4 @[1200px]:grid-cols-3">
        <div className="@[1200px]:col-span-2 grid gap-4 @[900px]:grid-cols-2">
          {isLoading ? <Skeleton className="h-40" /> : <MiniTrajectory />}
          {isLoading ? <Skeleton className="h-40" /> : <TopTagsCloud />}
        </div>
        <div className="flex flex-col gap-4">
          {isLoading ? <Skeleton className="h-40" /> : <RecentActivity />}
          <ConnectTile />
        </div>
      </div>

      {/* Mixes */}
      <CuratedMixes />

      {/* Insights carousel */}
      <div>
        <div className="mb-2 text-xs uppercase tracking-wider text-muted-foreground">Insights</div>
        <div className="flex gap-4 overflow-x-auto pb-2">
          {isLoading ? (
            [1, 2, 3].map((i) => <Skeleton key={i} className="h-24 min-w-[220px]" />)
          ) : (
            <AnimatePresence mode="popLayout">
              {(data?.insights || []).map((ins) => (
                <motion.div
                  key={ins.id}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -8 }}
                  transition={{ duration: 0.35, ease: 'easeOut' }}
                  whileHover={{ scale: 1.02 }}
                >
                  <InsightCard insight={ins} />
                </motion.div>
              ))}
            </AnimatePresence>
          )}
        </div>
      </div>

      {/* Compact KPIs */}
      <div className="grid gap-4 @[750px]:grid-cols-3">
        {isLoading
          ? [1, 2, 3].map((i) => <Skeleton key={i} className="h-24" />)
          : (data?.kpis || []).map((kpi) => <KpiCard key={kpi.id} kpi={kpi} />)}
      </div>

      {/* Discover shortcuts */}
      <DiscoverRow />
    </section>
  );
}
