'use client';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import clsx from 'clsx';
import { motion } from 'framer-motion';
import * as Tooltip from '@radix-ui/react-tooltip';
import { ChevronLeft, ChevronRight } from 'lucide-react';

import { useNavItems } from '../lib/nav';
import { useNav } from './NavContext';
import Avatar from './ui/Avatar';

export default function NavRail() {
  const pathname = usePathname();
  const { collapsed, setCollapsed } = useNav();
  const navItems = useNavItems();

  return (
    <motion.div
      className={clsx(
        'glass flex h-full flex-col gap-2 p-3 overflow-hidden',
        collapsed && 'items-center',
      )}
      initial={false}
      animate={{ width: collapsed ? 64 : 240 }}
      transition={{ type: 'spring', stiffness: 260, damping: 26 }}
    >
      <div className="flex w-full items-center gap-2 px-2 py-3">
        <Avatar
          size={32}
          className={clsx(
            'transition-opacity duration-300 ease-in-out',
            collapsed ? 'opacity-90' : 'opacity-100',
          )}
        />
        <span
          className={clsx(
            'overflow-hidden text-lg font-semibold tracking-wide text-foreground/90 transition-[max-width,opacity] duration-300 ease-in-out',
            collapsed ? 'max-w-0 opacity-0' : 'max-w-[160px] opacity-100',
          )}
          aria-hidden={collapsed ? 'true' : 'false'}
        >
          SideTrack
        </span>
      </div>
      <Tooltip.Provider>
        <nav className="flex flex-col gap-2" aria-label="Primary">
          {navItems.map((item, idx) => {
            const Icon = item.icon;
            const active = pathname === item.path || pathname.startsWith(`${item.path}/`);
            return (
              <Tooltip.Root key={item.path}>
                <Tooltip.Trigger asChild>
                  <Link
                    href={item.path}
                    aria-label={item.label}
                    aria-current={active ? 'page' : undefined}
                    accessKey={(idx + 1).toString()}
                    className={clsx(
                      'relative flex h-11 items-center rounded-lg px-4 text-sm transition-colors',
                      collapsed ? 'justify-center gap-0' : 'gap-3',
                      active
                        ? 'text-emerald-300'
                        : 'text-muted-foreground hover:bg-white/5 hover:text-foreground',
                    )}
                  >
                    {active && (
                      <motion.span
                        layoutId="nav-active"
                        className="absolute inset-0 -z-10 rounded-lg bg-emerald-500/10"
                        transition={{ type: 'spring', stiffness: 300, damping: 20 }}
                      />
                    )}
                    <motion.div
                      className={clsx(
                        'flex items-center',
                        collapsed ? 'justify-center gap-0' : 'gap-3',
                      )}
                      whileHover={{ x: 2 }}
                      transition={{ type: 'spring', stiffness: 300, damping: 20 }}
                    >
                      <Icon
                        size={18}
                        className={clsx(
                          'transition-opacity duration-300 ease-in-out',
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
                    </motion.div>
                  </Link>
                </Tooltip.Trigger>
                {collapsed && (
                  <Tooltip.Portal>
                    <Tooltip.Content
                      side="right"
                      sideOffset={8}
                      className="rounded-md bg-foreground px-2 py-1 text-xs text-background"
                    >
                      {item.label}
                    </Tooltip.Content>
                  </Tooltip.Portal>
                )}
              </Tooltip.Root>
            );
          })}
        </nav>
      </Tooltip.Provider>
      <button
        type="button"
        onClick={() => setCollapsed(!collapsed)}
        aria-label={collapsed ? 'Expand navigation' : 'Collapse navigation'}
        aria-expanded={!collapsed}
        accessKey="b"
        className="mt-auto flex h-11 w-full items-center justify-center gap-2 rounded-lg text-sm text-muted-foreground transition-colors duration-200 hover:bg-white/5 hover:text-foreground focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500"
      >
        {collapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
        <span
          className={clsx(
            'overflow-hidden transition-[max-width,opacity] duration-300 ease-in-out',
            collapsed ? 'max-w-0 opacity-0' : 'max-w-[80px] opacity-100',
          )}
          aria-hidden={collapsed ? 'true' : 'false'}
        >
          Collapse
        </span>
      </button>
    </motion.div>
  );
}
