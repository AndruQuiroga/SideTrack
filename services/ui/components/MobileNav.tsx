'use client';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import clsx from 'clsx';
import { useNavItems } from '../lib/nav';

export default function MobileNav() {
  const pathname = usePathname();
  const visibleItems = useNavItems();
  return (
    <nav
      className="fixed bottom-0 left-0 right-0 z-40 flex border-t border-white/10 bg-black/70 p-2 backdrop-blur md:hidden"
      aria-label="Primary"
    >
      {visibleItems.map((item, idx) => {
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
            <item.icon size={18} />
            <span className="text-xs">{item.label}</span>
          </Link>
        );
      })}
    </nav>
  );
}
