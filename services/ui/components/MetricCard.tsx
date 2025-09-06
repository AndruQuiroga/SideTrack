'use client';
import { motion } from 'framer-motion';

type Props = {
  title: string;
  value: string | number;
  delta?: { value: number; suffix?: string };
};

export default function MetricCard({ title, value, delta }: Props) {
  const deltaText =
    delta && typeof delta.value === 'number'
      ? `${delta.value > 0 ? '+' : ''}${delta.value}${delta.suffix ?? ''}`
      : undefined;
  const deltaClass = delta && delta.value >= 0 ? 'text-emerald-400' : 'text-rose-400';
  return (
    <motion.div
      className="glass rounded-lg p-4 shadow-soft"
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, ease: 'easeOut' }}
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
    >
      <div className="text-xs uppercase tracking-wide text-muted-foreground">{title}</div>
      <div className="mt-2 flex items-baseline gap-2">
        <div className="text-2xl font-semibold">{value}</div>
        {deltaText && <div className={`text-xs ${deltaClass}`}>{deltaText}</div>}
      </div>
    </motion.div>
  );
}
