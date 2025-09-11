'use client';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import clsx from 'clsx';
import * as Icons from 'lucide-react';
import nav from '../nav.json';
import useFeatureFlag from '../hooks/useFeatureFlag';

type NavItem = {
  path: string;
  label: string;
  icon: keyof typeof Icons;
  featureFlag?: string | null;
};

const items = nav as NavItem[];

export default function MobileNav() {
  const pathname = usePathname();
  const visibleItems = items.filter((item) => useFeatureFlag(item.featureFlag));
  return (
    <nav
      className="fixed bottom-0 left-0 right-0 z-40 flex border-t border-white/10 bg-black/70 p-2 backdrop-blur md:hidden"
      aria-label="Primary"
    >
      {visibleItems.map((item, idx) => {
        const Icon = Icons[item.icon];
        const active = pathname === item.path || pathname.startsWith(`${item.path}/`);
        return (
          <Link
            key={item.path}
            href={item.path}
            aria-label={item.label}
            aria-current={active ? 'page' : undefined}
            accessKey={(idx + 1).toString()}
            className={clsx(
              'flex flex-1 min-h-[48px] flex-col items-center justify-center gap-1 rounded-md p-3 text-sm',
              active ? 'text-emerald-300' : 'text-muted-foreground hover:text-foreground',
            )}
          >
            <Icon size={18} />
            <span className="text-xs">{item.label}</span>
          </Link>
        );
      })}
    </nav>
  );
}
