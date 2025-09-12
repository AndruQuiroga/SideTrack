'use client';

import { useSources } from '../../lib/sources';
import Breadcrumbs from '../common/Breadcrumbs';
import SourceBadge from '../common/SourceBadge';

export default function Header() {
  const { data: sources } = useSources();

  return (
    <header className="sticky top-0 z-10 flex items-center justify-between gap-4 border-b bg-background/80 px-4 py-3 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <Breadcrumbs />
      <div className="flex items-center gap-2 ml-auto">
        {sources?.map((s) => (
          <SourceBadge key={s.type} source={s} />
        ))}
      </div>
    </header>
  );
}
