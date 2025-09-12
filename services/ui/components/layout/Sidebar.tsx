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
        'relative shrink-0 flex flex-col border-r border-white/10 bg-white/5 backdrop-blur-md supports-[backdrop-filter]:bg-white/5',
        collapsed ? 'w-16' : 'w-16 md:w-60',
        'transition-[width,background-color] duration-300',
      )}
    >
      <div className="flex items-center justify-between px-3 py-3">
        {!collapsed && (
          <span className="text-sm font-semibold tracking-wide text-foreground/90">SideTrack</span>
        )}
        <button
          onClick={() => setCollapsed(!collapsed)}
          aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          className="hidden h-8 w-8 items-center justify-center rounded-md text-muted-foreground hover:bg-white/10 hover:text-foreground focus:outline-none focus:ring-2 focus:ring-emerald-500 md:inline-flex"
        >
          <Menu size={16} />
        </button>
      </div>
      <nav className="flex-1 space-y-1 px-2">
        {navItems.map((item) => {
          const active = pathname === item.href || pathname.startsWith(item.href + '/');
          return (
            <div key={item.href} className="relative group">
              <Link
                href={item.href}
                className={clsx(
                  'relative flex items-center gap-3 rounded-md px-3 py-2 text-sm text-muted-foreground transition-colors hover:bg-white/10 hover:text-foreground focus:outline-none focus:ring-2 focus:ring-emerald-500',
                  active && 'bg-white/10 text-foreground',
                )}
                aria-label={item.label}
              >
                {active && (
                  <span
                    className="absolute left-0 top-1/2 h-5 w-1 -translate-y-1/2 rounded-sm bg-emerald-400"
                    aria-hidden
                  />
                )}
                <item.icon size={18} />
                {!collapsed && <span className="hidden md:inline">{item.label}</span>}
              </Link>
              {collapsed && (
                <span
                  className="pointer-events-none absolute left-full top-1/2 ml-2 -translate-y-1/2 whitespace-nowrap rounded-md border border-white/10 bg-white/10 px-2 py-1 text-xs text-foreground/90 opacity-0 backdrop-blur transition-opacity duration-150 group-hover:opacity-100"
                  role="tooltip"
                >
                  {item.label}
                </span>
              )}
            </div>
          );
        })}
      </nav>
      <div className="mt-auto p-2">
        <ThemeToggle />
      </div>
    </aside>
  );
}
