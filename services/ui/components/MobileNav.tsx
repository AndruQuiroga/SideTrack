'use client';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import clsx from 'clsx';
import { motion } from 'framer-motion';

import { useNavItems } from '../lib/nav';

const motionSpring = { type: 'spring', stiffness: 320, damping: 24 } as const;

export default function MobileNav() {
  const pathname = usePathname();
  const visibleItems = useNavItems();
  return (
    <nav
      className="fixed bottom-0 left-0 right-0 z-40 flex border-t border-white/10 bg-black/70 p-2 backdrop-blur md:hidden"
      aria-label="Primary"
    >
      {visibleItems.map((item, idx) => {
        const active = pathname === item.path || pathname.startsWith(`${item.path}/`);
        return (
          <Link
            key={item.path}
            href={item.path}
            aria-label={item.label}
            aria-current={active ? 'page' : undefined}
            accessKey={(idx + 1).toString()}
            className={clsx(
              'relative flex min-h-[48px] flex-1 flex-col items-center justify-center gap-1 rounded-md p-3 text-sm text-muted-foreground transition-colors',
              'hover:text-foreground',
              'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-300 focus-visible:ring-offset-2 focus-visible:ring-offset-black/60',
              'aria-[current=page]:text-emerald-300 aria-[current=page]:font-medium',
            )}
          >
            <motion.div
              className="flex flex-col items-center gap-1"
              initial={false}
              animate={{ y: active ? -2 : 0 }}
              transition={motionSpring}
            >
              <motion.div
                className="flex items-center justify-center"
                initial={false}
                animate={{ scale: active ? 1.05 : 1 }}
                transition={motionSpring}
              >
                <item.icon size={18} />
              </motion.div>
              <motion.div
                className="text-xs"
                initial={false}
                animate={{ opacity: active ? 1 : 0.8 }}
                transition={motionSpring}
              >
                {item.label}
              </motion.div>
            </motion.div>
          </Link>
        );
      })}
    </nav>
  );
}
