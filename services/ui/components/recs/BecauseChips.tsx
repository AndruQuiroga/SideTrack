'use client';

import SourceBadge from '../layout/SourceBadge';
import { chipFromReason, type Reason, type Source } from '../../lib/sources';

export default function BecauseChips({ reasons }: { reasons: Reason[] }) {
  const chips = reasons?.map(chipFromReason).filter(Boolean) ?? [];
  if (!chips.length) return null;
  return (
    <div className="flex flex-wrap gap-2">
      {chips.map((c, idx) => {
        const source: Source = { type: c.source, status: 'connected' } as Source;
        return (
          <span
            key={idx}
            className="inline-flex items-center gap-1 rounded-full bg-secondary px-2 py-0.5 text-xs"
          >
            <SourceBadge source={source} />
            <span>{c.text}</span>
          </span>
        );
      })}
    </div>
  );
}

