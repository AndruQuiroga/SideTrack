'use client';

import Link from 'next/link';
import { motion } from 'framer-motion';
import { Card } from '../ui/card';

type Props = {
  lastArtist: string;
};

export default function QuickActions({ lastArtist }: Props) {
  const actions = [
    {
      label: `Recommend like ${lastArtist}`,
      href: `/recommendations?seed=${encodeURIComponent(lastArtist)}`,
    },
    { label: 'Build 60-min mixtape', href: '/mixtape?duration=60' },
    { label: 'Connect sources', href: '/settings/sources' },
  ];

  return (
    <Card variant="glass" className="p-4 shadow-soft">
      <div className="mb-2 text-sm font-medium">Quick Actions</div>
      <ul className="space-y-2">
        {actions.map((a) => (
          <li key={a.label}>
            <motion.div
              whileHover={{ scale: 1.02, x: 4 }}
              whileTap={{ scale: 0.98 }}
              transition={{ duration: 0.15 }}
              className="inline-block"
            >
              <Link
                href={a.href}
                className="rounded-md border border-white/10 bg-white/5 px-3 py-1.5 text-sm text-emerald-300 backdrop-blur hover:bg-white/10"
              >
                {a.label}
              </Link>
            </motion.div>
          </li>
        ))}
      </ul>
    </Card>
  );
}
