'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Menu } from 'lucide-react';
import clsx from 'clsx';
import { motion } from 'framer-motion';

import ThemeToggle from '../common/ThemeToggle';
import { useNavItems } from '../../lib/nav';

const motionSpring = { type: 'spring', stiffness: 280, damping: 22 } as const;

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
          className="hidden h-8 w-8 items-center justify-center rounded-md text-muted-foreground hover:bg-white/10 hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-300 focus-visible:ring-offset-2 focus-visible:ring-offset-background md:inline-flex"
        >
          <Menu size={16} />
        </button>
      </div>
      <nav className="flex-1 space-y-1 px-2">
        {navItems.map((item) => {
          const active = pathname === item.path || pathname.startsWith(item.path + '/');
          const Icon = item.icon;
          return (
            <div key={item.path} className="relative group">
              <Link
                href={item.path}
                className={clsx(
                  'relative flex items-center gap-3 rounded-md px-3 py-2 text-sm text-muted-foreground transition-colors',
                  'hover:bg-white/10 hover:text-foreground',
                  'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-300 focus-visible:ring-offset-2 focus-visible:ring-offset-background',
                  'aria-[current=page]:bg-white/10 aria-[current=page]:text-foreground',
                )}
                aria-label={item.label}
                aria-current={active ? 'page' : undefined}
              >
                {active && (
                  <motion.span
                    layoutId="sidebar-active"
                    className="absolute left-0 top-1/2 h-5 w-1 -translate-y-1/2 rounded-sm bg-emerald-400"
                    aria-hidden
                    transition={motionSpring}
                  />
                )}
                <motion.div
                  className="flex items-center gap-3"
                  initial={false}
                  animate={{ x: active ? 2 : 0 }}
                  transition={motionSpring}
                >
                  <motion.div
                    className="flex items-center justify-center"
                    initial={false}
                    animate={{ scale: active ? 1.05 : 1 }}
                    transition={motionSpring}
                  >
                    <Icon size={18} />
                  </motion.div>
                  {!collapsed && (
                    <motion.div
                      className="hidden text-sm md:inline-flex"
                      initial={false}
                      animate={{ opacity: active ? 1 : 0.85 }}
                      transition={motionSpring}
                    >
                      {item.label}
                    </motion.div>
                  )}
                </motion.div>
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
