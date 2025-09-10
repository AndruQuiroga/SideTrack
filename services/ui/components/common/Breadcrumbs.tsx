'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { ChevronRight } from 'lucide-react';

export default function Breadcrumbs() {
  const pathname = usePathname();
  const segments = pathname.split('/').filter(Boolean);

  return (
    <nav aria-label="Breadcrumb" className="hidden text-sm text-muted-foreground md:block">
      <ol className="flex items-center gap-1">
        <li>
          <Link href="/" className="hover:underline">
            Home
          </Link>
        </li>
        {segments.map((seg, idx) => (
          <li key={seg} className="flex items-center gap-1">
            <ChevronRight size={12} aria-hidden="true" />
            {idx === segments.length - 1 ? (
              <span className="capitalize" aria-current="page">
                {seg.replace(/-/g, ' ')}
              </span>
            ) : (
              <Link
                href={`/${segments.slice(0, idx + 1).join('/')}`}
                className="hover:underline capitalize"
              >
                {seg.replace(/-/g, ' ')}
              </Link>
            )}
          </li>
        ))}
      </ol>
    </nav>
  );
}

