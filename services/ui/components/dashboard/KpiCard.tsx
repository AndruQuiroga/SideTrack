'use client';
import { motion } from 'framer-motion';
import { Card } from '../ui/card';
import { useMemo } from 'react';
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

  return (
    <Card asChild variant="glass" className="p-4 shadow-soft">
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35, ease: 'easeOut' }}
        whileHover={{ scale: 1.02 }}
        whileTap={{ scale: 0.98 }}
      >
        <div className="text-xs uppercase tracking-wide text-muted-foreground">{title}</div>
        {error ? (
          <div className="mt-2 text-sm text-rose-400">{error}</div>
        ) : (
          <>
            <div className="mt-2 flex items-baseline gap-2">
              <div className="text-2xl font-semibold">{value ?? '--'}</div>
              {deltaText && <div className={`text-xs ${deltaClass}`}>{deltaText}</div>}
            </div>
            {path && (
              <svg viewBox="0 0 100 24" className="mt-2 h-6 w-full text-emerald-400">
                <path d={path} fill="none" stroke="currentColor" strokeWidth={2} />
              </svg>
            )}
          </>
        )}
      </motion.div>
    </Card>
  );
}
