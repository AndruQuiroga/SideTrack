'use client';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import clsx from 'clsx';
import { nav } from './NavRail';

export default function MobileNav() {
  const pathname = usePathname();
  return (
    <nav className="fixed bottom-0 left-0 right-0 z-40 flex border-t border-white/10 bg-black/70 p-1 backdrop-blur md:hidden">
      {nav.map((item) => {
        const Icon = item.icon;
        const active = pathname === item.href;
        return (
          <Link
            key={item.href}
            href={item.href}
            className={clsx(
              'flex flex-1 flex-col items-center justify-center gap-1 rounded-md p-2 text-xs',
              active ? 'text-emerald-300' : 'text-muted-foreground hover:text-foreground',
            )}
          >
            <Icon size={18} />
            <span className="text-[10px]">{item.label}</span>
          </Link>
        );
      })}
    </nav>
  );
}
