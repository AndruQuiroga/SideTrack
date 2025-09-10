'use client';

import { motion } from 'framer-motion';

export interface Shift {
  week: string;
  metric: string;
  delta: number;
  before: number;
  after: number;
}

interface Props {
  shifts: Shift[];
  onSelect?: (week: string) => void;
}

export default function ShiftMarkers({ shifts, onSelect }: Props) {
  if (!shifts.length) return null;
  return (
    <div className="flex gap-2 overflow-x-auto py-2">
      {shifts.map((s) => (
        <motion.button
          key={`${s.metric}-${s.week}`}
          whileHover={{ scale: 1.1 }}
          whileTap={{ scale: 0.95 }}
          className="px-3 py-1 text-xs rounded-full bg-secondary whitespace-nowrap"
          onClick={() => onSelect?.(s.week)}
        >
          {s.metric} {s.delta.toFixed(2)}
        </motion.button>
      ))}
    </div>
  );
}
