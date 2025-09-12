'use client';

import { useSources } from '../../lib/sources';
import HeaderActions from '../HeaderActions';
import { useAuth } from '../../lib/auth';
import { Disc3 } from 'lucide-react';
import Breadcrumbs from '../common/Breadcrumbs';
import SourceBadge from '../common/SourceBadge';

export default function Header() {
  const { data: sources } = useSources();
  const { userId } = useAuth();
  const initials = (userId || 'U').slice(0, 2).toUpperCase();

  return (
    <header className="sticky top-0 z-20 flex items-center justify-between gap-4 border-b border-white/10 bg-white/5 px-4 py-3 backdrop-blur-md supports-[backdrop-filter]:bg-white/5 shadow-[0_10px_30px_-15px_rgba(0,0,0,0.5)]">
      <div className="flex items-center gap-3">
        <Disc3 size={18} className="text-emerald-300" />
        <Breadcrumbs />
      </div>

      <div className="hidden md:flex items-center gap-2 text-xs text-muted-foreground">
        <span className="rounded-full bg-white/5 px-2 py-1">Now playing</span>
        <span className="truncate max-w-[220px]">— nothing yet</span>
      </div>

      <div className="ml-auto flex items-center gap-3">
        {sources?.map((s) => (
          <SourceBadge key={s.type} source={s} />
        ))}
        <HeaderActions />
        <div className="ml-1 hidden md:inline-flex h-8 w-8 items-center justify-center rounded-full border border-white/10 bg-white/10 text-xs font-medium">
          {initials}
        </div>
      </div>
    </header>
  );
}
