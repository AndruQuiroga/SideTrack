import clsx from 'clsx';
import { ReactNode } from 'react';

export function Card({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <div
      className={clsx(
        'relative overflow-hidden rounded-3xl border border-slate-800/80 bg-sidetrack-soft/70 p-5 shadow-soft backdrop-blur-sm',
        className
      )}
    >
      <div className="pointer-events-none absolute inset-x-0 -top-24 h-32 bg-gradient-to-b from-purple-500/10 via-sky-400/5 to-transparent" />
      <div className="relative">{children}</div>
    </div>
  );
}

export function Pill({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <span
      className={clsx(
        'inline-flex items-center gap-2 rounded-full border border-slate-700/60 bg-slate-900/80 px-3 py-1 text-[0.7rem] font-semibold uppercase tracking-wide text-slate-200',
        className
      )}
    >
      {children}
    </span>
  );
}

export function SectionHeading({ eyebrow, title, aside }: { eyebrow?: string; title: string; aside?: ReactNode }) {
  return (
    <div className="flex items-start justify-between gap-3">
      <div>
        {eyebrow && (
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
            <span className="mr-2 inline-block h-1.5 w-1.5 rounded-full bg-emerald-400" />
            {eyebrow}
          </p>
        )}
        <h2 className="text-xl font-bold text-white sm:text-2xl">{title}</h2>
      </div>
      {aside}
    </div>
  );
}
