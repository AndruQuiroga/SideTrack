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

const motionSpring = { type: 'spring', stiffness: 300, damping: 20 } as const;
const labelSpring = { type: 'spring', stiffness: 260, damping: 25 } as const;

export default function NavRail() {
  const pathname = usePathname();
  const { collapsed, setCollapsed } = useNav();
  const items = useNavItems();
  return (
    <div className="flex h-full flex-col gap-2 p-3 glass">
      <div className="flex items-center gap-2 px-2 py-3">
        <Avatar size={32} />
        {!collapsed && <strong className="text-lg">SideTrack</strong>}
      </div>
      <Tooltip.Provider>
        <nav className="flex flex-col gap-2" aria-label="Primary">
          {items.map((item, idx) => {
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
                      'group relative flex h-11 items-center gap-3 rounded-lg px-4 text-sm transition-colors',
                      'text-muted-foreground hover:text-foreground hover:bg-white/5',
                      'aria-[current=page]:text-emerald-300',
                      'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-300 focus-visible:ring-offset-2 focus-visible:ring-offset-background',
                    )}
                  >
                    {active && (
                      <motion.span
                        layoutId="nav-active"
                        className="absolute inset-0 -z-10 rounded-lg bg-emerald-500/10"
                        transition={motionSpring}
                      />
                    )}
                    <motion.div
                      className="flex items-center gap-3"
                      initial={false}
                      animate={{ x: active ? 2 : 0 }}
                      whileHover={{ x: 4 }}
                      transition={motionSpring}
                    >
                      <motion.div
                        initial={false}
                        animate={{ scale: active ? 1.05 : 1 }}
                        transition={motionSpring}
                        className="flex items-center justify-center"
                      >
                        <Icon size={18} />
                      </motion.div>
                      {!collapsed && (
                        <motion.div
                          initial={false}
                          animate={{ opacity: active ? 1 : 0.75 }}
                          transition={labelSpring}
                          className="whitespace-nowrap"
                        >
                          {item.label}
                        </motion.div>
                      )}
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
        onClick={() => setCollapsed(!collapsed)}
        aria-label={collapsed ? 'Expand navigation' : 'Collapse navigation'}
        accessKey="b"
        className="mt-auto flex h-11 items-center gap-2 px-4 text-sm text-muted-foreground"
      >
        {collapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
        {!collapsed && <span>Collapse</span>}
      </button>
    </div>
  );
}
