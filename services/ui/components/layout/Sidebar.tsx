'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Menu } from 'lucide-react';
import clsx from 'clsx';
import ThemeToggle from '../common/ThemeToggle';
import { useNavItems } from '../../lib/nav';

export default function Sidebar({
  collapsed,
  setCollapsed,
}: {
  collapsed: boolean;
  setCollapsed: (v: boolean) => void;
}) {
  const pathname = usePathname();
  const navItems = useNavItems();

  return (
    <aside
      className={clsx(
        'relative shrink-0 flex flex-col border-r border-white/10 bg-white/5 backdrop-blur-md supports-[backdrop-filter]:bg-white/5',
        collapsed ? 'w-16' : 'w-64 md:w-60',
        'transition-[width,background-color] duration-300 ease-in-out',
      )}
    >
      <div className="flex items-center justify-between px-3 py-3">
        <span
          className={clsx(
            'overflow-hidden text-sm font-semibold tracking-wide text-foreground/90 transition-[max-width,opacity] duration-300 ease-in-out',
            collapsed ? 'max-w-0 opacity-0' : 'max-w-[160px] opacity-100',
          )}
          aria-hidden={collapsed ? 'true' : 'false'}
        >
          SideTrack
        </span>
        <button
          type="button"
          onClick={() => setCollapsed(!collapsed)}
          aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          aria-expanded={!collapsed}
          className="flex h-9 w-9 items-center justify-center rounded-md text-muted-foreground transition-colors duration-200 hover:bg-white/10 hover:text-foreground focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500"
        >
          <Menu size={16} />
        </button>
      </div>
      <nav className="flex-1 space-y-1 px-2" aria-label="Primary">
        {navItems.map((item) => {
          const active = pathname === item.path || pathname.startsWith(item.path + '/');
          return (
            <div key={item.path} className="relative group">
              <Link
                href={item.path}
                className={clsx(
                  'relative flex items-center rounded-md px-3 py-2 text-sm text-muted-foreground transition-colors hover:bg-white/10 hover:text-foreground focus:outline-none focus:ring-2 focus:ring-emerald-500',
                  collapsed ? 'justify-center gap-0' : 'gap-3',
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
                <item.icon
                  size={18}
                  className={clsx(
                    'shrink-0 transition-opacity duration-300 ease-in-out',
                    collapsed ? 'opacity-90' : 'opacity-100',
                  )}
                />
                <span
                  className={clsx(
                    'whitespace-nowrap overflow-hidden transition-[max-width,opacity] duration-300 ease-in-out',
                    collapsed ? 'max-w-0 opacity-0' : 'max-w-[160px] opacity-100',
                  )}
                  aria-hidden={collapsed ? 'true' : 'false'}
                >
                  {item.label}
                </span>
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
