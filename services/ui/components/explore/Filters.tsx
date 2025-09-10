'use client';
import { useSearchParams, useRouter, usePathname } from 'next/navigation';
import { useCallback } from 'react';
import FilterBar from '../FilterBar';

export default function Filters() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();

  const range = searchParams.get('range') ?? '12w';
  const sources = searchParams.get('sources')?.split(',').filter(Boolean) ?? [];
  const genres = searchParams.get('genres')?.split(',').filter(Boolean) ?? [];

  const update = useCallback(
    (updates: Record<string, string | string[] | null>) => {
      const sp = new URLSearchParams(searchParams);
      Object.entries(updates).forEach(([key, value]) => {
        if (value === null) {
          sp.delete(key);
        } else if (Array.isArray(value)) {
          if (value.length) sp.set(key, value.join(','));
          else sp.delete(key);
        } else {
          sp.set(key, value);
        }
      });
      router.push(`${pathname}?${sp.toString()}`, { scroll: false });
    },
    [searchParams, router, pathname],
  );

  const toggleSource = (src: string) => {
    const next = sources.includes(src)
      ? sources.filter((s) => s !== src)
      : [...sources, src];
    update({ sources: next });
  };

  const toggleGenre = (g: string) => {
    const next = genres.includes(g)
      ? genres.filter((s) => s !== g)
      : [...genres, g];
    update({ genres: next });
  };

  return (
    <div className="space-y-4">
      <FilterBar
        options={[
          { label: '12w', value: '12w' },
          { label: '24w', value: '24w' },
          { label: '52w', value: '52w' },
        ]}
        value={range}
        onChange={(v) => update({ range: v })}
      />
      <div className="flex flex-wrap items-center gap-4 text-sm">
        {['spotify', 'local'].map((src) => (
          <label key={src} className="flex items-center gap-1">
            <input
              type="checkbox"
              checked={sources.includes(src)}
              onChange={() => toggleSource(src)}
            />
            {src}
          </label>
        ))}
      </div>
      <div className="flex flex-wrap gap-2 text-xs">
        {['rock', 'pop', 'indie'].map((g) => {
          const active = genres.includes(g);
          return (
            <button
              key={g}
              type="button"
              onClick={() => toggleGenre(g)}
              className={`rounded-full px-2 py-1 border ${
                active
                  ? 'bg-emerald-500/15 border-emerald-400 text-emerald-300'
                  : 'border-white/20 text-muted-foreground'
              }`}
            >
              {g}
            </button>
          );
        })}
      </div>
    </div>
  );
}
