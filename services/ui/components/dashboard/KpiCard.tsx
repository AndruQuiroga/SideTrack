'use client';
import { motion } from 'framer-motion';
import { Card } from '../ui/card';
import { useMemo } from 'react';
import { Music, Users, Activity } from 'lucide-react';
import type { DashboardKpi } from '../../lib/query';

type Props = {
  kpi: DashboardKpi;
};

export default function KpiCard({ kpi }: Props) {
  const { title, value, delta, series, error } = kpi;
  const deltaText =
    delta && typeof delta.value === 'number'
      ? `${delta.value > 0 ? '+' : ''}${delta.value}${delta.suffix ?? ''}`
      : undefined;
  const deltaClass = delta && delta.value >= 0 ? 'text-emerald-400' : 'text-rose-400';

  const path = useMemo(() => {
    if (!series || series.length === 0) return '';
    const w = 100;
    const h = 24;
    const max = Math.max(...series);
    const min = Math.min(...series);
    const range = max - min || 1;
    const scaleX = w / (series.length - 1);
    const points = series.map((v, i) => {
      const x = i * scaleX;
      const y = h - ((v - min) / range) * h;
      return `${x},${y}`;
    });
    return `M${points.join(' L')}`;
  }, [series]);

  // Accent styling inspired by Spotify-like playful gradients
  const accent = useMemo(() => {
    const id = (kpi.id || '').toLowerCase();
    if (id.includes('listen'))
      return {
        grad: 'from-emerald-400/80 via-teal-400/70 to-cyan-400/80',
        ring: 'shadow-[0_0_40px_-10px_rgba(16,185,129,0.6)]',
        icon: <Music size={16} className="text-emerald-300" aria-hidden />,
      } as const;
    if (id.includes('artist'))
      return {
        grad: 'from-violet-400/80 via-fuchsia-400/70 to-pink-400/80',
        ring: 'shadow-[0_0_40px_-10px_rgba(192,132,252,0.6)]',
        icon: <Users size={16} className="text-violet-300" aria-hidden />,
      } as const;
    return {
      grad: 'from-amber-400/80 via-orange-400/70 to-rose-400/80',
      ring: 'shadow-[0_0_40px_-10px_rgba(251,191,36,0.6)]',
      icon: <Activity size={16} className="text-amber-300" aria-hidden />,
    } as const;
  }, [kpi.id]);

  return (
    <Card
      asChild
      variant="glass"
      className={`relative overflow-hidden p-4 ${accent.ring} transition-colors`}
    >
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35, ease: 'easeOut' }}
        whileHover={{ scale: 1.02 }}
        whileTap={{ scale: 0.98 }}
      >
        {/* Glow blob */}
        <div
          className={`pointer-events-none absolute -right-6 -top-8 h-24 w-24 rounded-full bg-gradient-to-br ${accent.grad} blur-2xl opacity-30`}
        />

        <div className="flex items-center justify-between">
          <div className="text-xs uppercase tracking-wide text-muted-foreground">{title}</div>
          <div className="rounded-md bg-white/5 p-1.5 backdrop-blur-sm">{accent.icon}</div>
        </div>
        {error ? (
          <div className="mt-2 text-sm text-rose-400">{error}</div>
        ) : (
          <>
            <div className="mt-2 flex items-baseline gap-2">
              <div
                className={`bg-gradient-to-r ${accent.grad} bg-clip-text text-3xl font-semibold text-transparent`}
              >
                {value ?? '--'}
              </div>
              {deltaText && (
                <div
                  className={`rounded-full border border-white/10 px-2 py-0.5 text-[11px] ${deltaClass} bg-white/5`}
                >
                  {deltaText}
                </div>
              )}
            </div>
            {path && (
              <svg viewBox="0 0 100 24" className="mt-3 h-7 w-full">
                <defs>
                  <linearGradient id={`kpi-grad-${kpi.id || 'x'}`} x1="0" x2="1">
                    <stop offset="0%" stopColor="rgba(255,255,255,0.6)" />
                    <stop offset="100%" stopColor="rgba(255,255,255,0.2)" />
                  </linearGradient>
                </defs>
                <path
                  d={path}
                  fill="none"
                  stroke={`url(#kpi-grad-${kpi.id || 'x'})`}
                  strokeWidth={2.5}
                  strokeLinecap="round"
                />
              </svg>
            )}
          </>
        )}
      </motion.div>
    </Card>
  );
}
