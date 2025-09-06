'use client';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Compass, Activity, Radar, Target, Settings, Home } from 'lucide-react';
import clsx from 'clsx';
import { motion } from 'framer-motion';

const nav = [
  { href: '/', label: 'Overview', icon: Home },
  { href: '/trajectory', label: 'Trajectory', icon: Compass },
  { href: '/moods', label: 'Moods', icon: Activity },
  { href: '/radar', label: 'Radar', icon: Radar },
  { href: '/outliers', label: 'Outliers', icon: Target },
  { href: '/settings', label: 'Settings', icon: Settings },
];

export default function NavRail() {
  const pathname = usePathname();
  return (
    <aside className="hidden md:flex h-dvh w-60 flex-col gap-2 p-3 glass">
      <div className="flex items-center gap-2 px-2 py-3">
        <div className="h-8 w-8 rounded-full bg-gradient-to-br from-emerald-400 to-sky-400" />
        <strong className="text-lg">SideTrack</strong>
      </div>
      <nav className="flex flex-col gap-1">
        {nav.map((item) => {
          const Icon = item.icon;
          const active = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={clsx(
                'flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors',
                active
                  ? 'bg-emerald-500/10 text-emerald-300'
                  : 'text-muted-foreground hover:text-foreground hover:bg-white/5',
              )}
            >
              <motion.div
                className="flex items-center gap-3"
                whileHover={{ x: 2 }}
                transition={{ type: 'spring', stiffness: 300, damping: 20 }}
              >
                <Icon size={18} />
                <span>{item.label}</span>
              </motion.div>
            </Link>
          );
        })}
      </nav>
      <div className="mt-auto px-2 py-3 text-xs text-muted-foreground">v0.1</div>
    </aside>
  );
}
