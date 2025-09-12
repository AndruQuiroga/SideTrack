'use client';

import { useSources } from '../../lib/sources';
import Breadcrumbs from '../common/Breadcrumbs';
import SourceBadge from '../common/SourceBadge';

export default function Header() {
  const { data: sources } = useSources();

  return (
    <header className="sticky top-0 z-20 flex items-center justify-between gap-4 border-b border-white/10 bg-white/5 px-4 py-3 backdrop-blur-md supports-[backdrop-filter]:bg-white/5 shadow-[0_10px_30px_-15px_rgba(0,0,0,0.5)]">
      <Breadcrumbs />
      <div className="ml-auto flex items-center gap-2">
        {sources?.map((s) => (
          <SourceBadge key={s.type} source={s} />
        ))}
      </div>
    </header>
  );
}
