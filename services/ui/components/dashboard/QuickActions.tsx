'use client';

import Link from 'next/link';
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
      <div className="text-sm font-medium mb-2">Quick Actions</div>
      <ul className="space-y-1">
        {actions.map((a) => (
          <li key={a.label}>
            <Link href={a.href} className="text-sm text-emerald-300 hover:underline">
              {a.label}
            </Link>
          </li>
        ))}
      </ul>
    </Card>
  );
}

