'use client';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import clsx from 'clsx';
import { motion } from 'framer-motion';
import * as Tooltip from '@radix-ui/react-tooltip';
import * as Icons from 'lucide-react';
import nav from '../nav.json';
import { useNav } from './NavContext';
import Avatar from './ui/Avatar';

const { ChevronLeft, ChevronRight } = Icons;

type NavItem = {
  path: string;
  label: string;
  icon: keyof typeof Icons;
  featureFlag?: string | null;
};

const items = nav as NavItem[];

export default function NavRail() {
  const pathname = usePathname();
  const { collapsed, setCollapsed } = useNav();
  return (
    <div className="flex h-full flex-col gap-2 p-3 glass">
      <div className="flex items-center gap-2 px-2 py-3">
        <Avatar size={32} />
        {!collapsed && <strong className="text-lg">SideTrack</strong>}
      </div>
      <Tooltip.Provider>
        <nav className="flex flex-col gap-2">
          {items.map((item) => {
            const Icon = Icons[item.icon];
            const active = pathname === item.path || pathname.startsWith(`${item.path}/`);
            return (
              <Tooltip.Root key={item.path}>
                <Tooltip.Trigger asChild>
                  <Link
                    href={item.path}
                    className={clsx(
                      'relative flex h-11 items-center gap-3 rounded-lg px-4 text-sm transition-colors',
                      active
                        ? 'text-emerald-300'
                        : 'text-muted-foreground hover:text-foreground hover:bg-white/5',
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
                      className="flex items-center gap-3"
                      whileHover={{ x: 2 }}
                      transition={{ type: 'spring', stiffness: 300, damping: 20 }}
                    >
                      <Icon size={18} />
                      {!collapsed && <span>{item.label}</span>}
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
        className="mt-auto flex h-11 items-center gap-2 px-4 text-sm text-muted-foreground"
      >
        {collapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
        {!collapsed && <span>Collapse</span>}
      </button>
    </div>
  );
}
