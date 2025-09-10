'use client';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import clsx from 'clsx';

const tabs = [
  { href: '/explore/trajectory', label: 'Trajectory' },
  { href: '/explore/moods', label: 'Moods' },
  { href: '/explore/radar', label: 'Radar' },
  { href: '/explore/outliers', label: 'Outliers' },
];

export default function ExploreTabs() {
  const pathname = usePathname();
  return (
    <nav className="flex gap-4 border-b border-white/10">
      {tabs.map((t) => {
        const active = pathname === t.href;
        return (
          <Link
            key={t.href}
            href={t.href}
            className={clsx(
              'pb-2 text-sm',
              active
                ? 'border-b-2 border-emerald-400 text-emerald-300'
                : 'text-muted-foreground hover:text-foreground'
            )}
          >
            {t.label}
          </Link>
        );
      })}
    </nav>
  );
}
