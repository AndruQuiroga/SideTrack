'use client';
import clsx from 'clsx';

type Option = { label: string; value: string };

type Props = {
  options: Option[];
  value: string;
  onChange?: (value: string) => void;
};

export default function FilterBar({ options, value, onChange }: Props) {
  return (
    <div className="flex flex-wrap items-center gap-2">
      {options.map((opt) => (
        <button
          key={opt.value}
          type="button"
          onClick={() => onChange?.(opt.value)}
          className={clsx(
            'rounded-full px-3 py-1 text-xs transition-colors',
            value === opt.value
              ? 'bg-emerald-500/15 text-emerald-300'
              : 'bg-white/5 text-muted-foreground hover:text-foreground',
          )}
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
}
