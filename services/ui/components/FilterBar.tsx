'use client';
import { motion } from 'framer-motion';
import clsx from 'clsx';

type Option = { label: string; value: string };

type Props = {
  options: Option[];
  value: string;
  onChange?: (value: string) => void;
};

export default function FilterBar({ options, value, onChange }: Props) {
  return (
    <div className="inline-flex items-center gap-1 rounded-full bg-white/5 p-1" role="group">
      {options.map((opt) => {
        const active = value === opt.value;
        return (
          <button
            key={opt.value}
            type="button"
            aria-pressed={active}
            onClick={() => onChange?.(opt.value)}
            className={clsx(
              'relative rounded-full px-3 py-1 text-xs',
              active ? 'text-emerald-300' : 'text-muted-foreground hover:text-foreground',
            )}
          >
            {active && (
              <motion.div
                layout
                layoutId="filter-bar-active"
                className="absolute inset-0 rounded-full bg-emerald-500/15"
              />
            )}
            <span className="relative z-10">{opt.label}</span>
          </button>
        );
      })}
    </div>
  );
}
