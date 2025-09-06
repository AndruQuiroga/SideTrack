'use client';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import dynamic from 'next/dynamic';
import clsx from 'clsx';
import { motion } from 'framer-motion';
import * as Tooltip from '@radix-ui/react-tooltip';
import { useNav } from './NavContext';
import Avatar from './ui/Avatar';

const Home = dynamic(() => import('lucide-react/lib/esm/icons/home'));
const Compass = dynamic(() => import('lucide-react/lib/esm/icons/compass'));
const Activity = dynamic(() => import('lucide-react/lib/esm/icons/activity'));
const Radar = dynamic(() => import('lucide-react/lib/esm/icons/radar'));
const Target = dynamic(() => import('lucide-react/lib/esm/icons/target'));
const Settings = dynamic(() => import('lucide-react/lib/esm/icons/settings'));
const User = dynamic(() => import('lucide-react/lib/esm/icons/user'));
const ChevronLeft = dynamic(() => import('lucide-react/lib/esm/icons/chevron-left'));
const ChevronRight = dynamic(() => import('lucide-react/lib/esm/icons/chevron-right'));

export const nav = [
  { href: '/', label: 'Overview', icon: Home },
  { href: '/trajectory', label: 'Trajectory', icon: Compass },
  { href: '/moods', label: 'Moods', icon: Activity },
  { href: '/radar', label: 'Radar', icon: Radar },
  { href: '/outliers', label: 'Outliers', icon: Target },
  { href: '/account', label: 'Account', icon: User },
  { href: '/settings', label: 'Settings', icon: Settings },
];

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
        <nav className="flex flex-col gap-1">
          {nav.map((item) => {
            const Icon = item.icon;
            const active = pathname === item.href;
            return (
              <Tooltip.Root key={item.href}>
                <Tooltip.Trigger asChild>
                  <Link
                    href={item.href}
                    className={clsx(
                      'relative flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors',
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
        className="mt-auto flex items-center gap-2 px-2 py-3 text-xs text-muted-foreground"
      >
        {collapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
        {!collapsed && <span>Collapse</span>}
      </button>
    </div>
  );
}
