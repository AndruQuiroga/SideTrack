'use client';
import clsx from 'clsx';
import { useSearchParams, useRouter, usePathname } from 'next/navigation';

const tabs = [
  { key: 'trajectory', label: 'Trajectory' },
  { key: 'moods', label: 'Moods' },
  { key: 'radar', label: 'Radar' },
  { key: 'outliers', label: 'Outliers' },
];

type Props = {
  onTabChange?: (next: string, prev: string) => void;
};

export default function Tabs({ onTabChange }: Props) {
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();
  const active = searchParams.get('tab') ?? 'trajectory';

  const handleClick = (tab: string) => {
    if (tab === active) return;
    onTabChange?.(tab, active);
    const sp = new URLSearchParams(searchParams);
    sp.set('tab', tab);
    router.push(`${pathname}?${sp.toString()}`, { scroll: false });
  };

  return (
    <nav className="flex gap-4 border-b border-white/10">
      {tabs.map((t) => {
        const isActive = active === t.key;
        return (
          <button
            key={t.key}
            onClick={() => handleClick(t.key)}
            className={clsx(
              'pb-2 text-sm',
              isActive
                ? 'border-b-2 border-emerald-400 text-emerald-300'
                : 'text-muted-foreground hover:text-foreground',
            )}
          >
            {t.label}
          </button>
        );
      })}
    </nav>
  );
}
