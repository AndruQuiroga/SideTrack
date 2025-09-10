'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Home, Sparkles, Compass, BarChart3, Settings, Menu } from 'lucide-react';
import clsx from 'clsx';
import ThemeToggle from '../common/ThemeToggle';

const navItems = [
  { href: '/', label: 'Home', icon: Home },
  { href: '/recommendations', label: 'Recommendations', icon: Sparkles },
  { href: '/explore', label: 'Explore', icon: Compass },
  { href: '/insights', label: 'Insights', icon: BarChart3 },
  { href: '/settings', label: 'Settings', icon: Settings },
];

export default function Sidebar({
  collapsed,
  setCollapsed,
}: {
  collapsed: boolean;
  setCollapsed: (v: boolean) => void;
}) {
  const pathname = usePathname();

  return (
    <aside
      className={clsx(
        'hidden border-r bg-background md:flex md:flex-col',
        collapsed ? 'w-16' : 'w-56',
        'motion-safe:transition-[width]'
      )}
    >
      <button
        onClick={() => setCollapsed(!collapsed)}
        aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        className="m-2 inline-flex h-8 w-8 items-center justify-center rounded-md hover:bg-white/5 focus:outline-none focus:ring-2 focus:ring-emerald-500"
      >
        <Menu size={16} />
      </button>
      <nav className="flex-1 space-y-1 px-2">
        {navItems.map((item) => {
          const active =
            pathname === item.href || pathname.startsWith(item.href + '/');
          return (
            <Link
              key={item.href}
              href={item.href}
              className={clsx(
                'flex items-center gap-3 rounded-md px-3 py-2 text-sm text-muted-foreground hover:bg-white/5 hover:text-foreground focus:outline-none focus:ring-2 focus:ring-emerald-500',
                active && 'bg-white/10 text-foreground'
              )}
            >
              <item.icon size={18} />
              {!collapsed && <span>{item.label}</span>}
            </Link>
          );
        })}
      </nav>
      <div className="mt-auto p-2">
        <ThemeToggle />
      </div>
    </aside>
  );
}

