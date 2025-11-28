'use client';

import clsx from 'clsx';
import Link from 'next/link';
import { useMemo, useState } from 'react';

import { WeekDetailWithRatings } from '../../src/api/weeks';
import { Card, Pill, SectionHeading } from './ui';
import { WeekList } from './week-list';
import { RatingBadge } from './rating-badge';

interface ClubGalleryProps {
  weeks: WeekDetailWithRatings[];
}

function extractTags(weeks: WeekDetailWithRatings[]): string[] {
  const tags = new Set<string>();
  weeks.forEach((week) => {
    week.nominations.forEach((nom) => {
      [nom.genre, nom.decade, nom.country].forEach((tag) => {
        if (tag) tags.add(tag);
      });
    });
  });
  return Array.from(tags).slice(0, 12);
}

function formatShortDate(date?: string | null) {
  if (!date) return '';
  const parsed = new Date(date);
  if (Number.isNaN(parsed.getTime())) return '';
  return parsed.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}

function livePresenceCopy(weeks: WeekDetailWithRatings[]) {
  const activeListeners = 12 + weeks.length * 3;
  const presence = activeListeners > 42 ? 'Club buzzing right now' : 'Listeners are live';
  return `${presence} · ${activeListeners} online`;
}

export function ClubGallery({ weeks }: ClubGalleryProps) {
  const [search, setSearch] = useState('');
  const [tag, setTag] = useState<string | null>(null);
  const [sort, setSort] = useState<'recent' | 'rating'>('recent');

  const tags = useMemo(() => extractTags(weeks), [weeks]);

  const filtered = useMemo(() => {
    const query = search.trim().toLowerCase();
    const sorted = [...weeks].sort((a, b) => {
      if (sort === 'rating') {
        const aScore = a.rating_summary?.average ?? a.aggregates.rating_average ?? 0;
        const bScore = b.rating_summary?.average ?? b.aggregates.rating_average ?? 0;
        return bScore - aScore;
      }
      const aDate = new Date(a.discussion_at ?? a.created_at ?? '').getTime();
      const bDate = new Date(b.discussion_at ?? b.created_at ?? '').getTime();
      return bDate - aDate;
    });

    return sorted.filter((week) => {
      const winner = week.nominations[0];
      const tagMatch = tag
        ? week.nominations.some((nom) => nom.genre === tag || nom.decade === tag || nom.country === tag)
        : true;
      const textMatch = query
        ? [week.label, winner?.pitch, winner?.genre, winner?.country, winner?.decade]
            .filter(Boolean)
            .some((field) => field!.toLowerCase().includes(query))
        : true;
      return tagMatch && textMatch;
    });
  }, [weeks, search, tag, sort]);

  const newest = filtered[0];

  return (
    <div className="space-y-6">
      <Card className="space-y-5">
        <SectionHeading eyebrow="Live archive" title="Winners gallery" aside={<Pill>{livePresenceCopy(weeks)}</Pill>} />
        <div className="grid gap-4 lg:grid-cols-[1.4fr,1fr]">
          <div className="rounded-2xl border border-slate-800/70 bg-slate-900/60 p-4">
            <p className="text-xs uppercase tracking-wide text-slate-400">Search & filter</p>
            <div className="mt-3 flex flex-col gap-3 sm:flex-row">
              <input
                type="search"
                placeholder="Search by week, album, genre..."
                className="w-full rounded-2xl border border-slate-800 bg-slate-900 px-4 py-2 text-sm text-slate-100 outline-none ring-emerald-500/40 focus:ring"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
              <select
                value={sort}
                onChange={(e) => setSort(e.target.value as 'recent' | 'rating')}
                className="rounded-2xl border border-slate-800 bg-slate-900 px-4 py-2 text-sm text-slate-100 outline-none ring-emerald-500/40 focus:ring sm:w-40"
              >
                <option value="recent">Newest first</option>
                <option value="rating">Highest rated</option>
              </select>
            </div>
            <div className="mt-3 flex flex-wrap gap-2">
              {tags.map((option) => (
                <button
                  key={option}
                  onClick={() => setTag((prev) => (prev === option ? null : option))}
                  className={clsx(
                    'rounded-full border px-3 py-1 text-[0.75rem] font-semibold transition-colors',
                    tag === option
                      ? 'border-emerald-400/80 bg-emerald-400/10 text-emerald-200'
                      : 'border-slate-700/70 bg-slate-900/70 text-slate-200 hover:border-slate-500'
                  )}
                >
                  {option}
                </button>
              ))}
              {!tags.length && <span className="text-sm text-slate-400">Tags will appear when nominations include metadata.</span>}
              {tag && (
                <button
                  onClick={() => setTag(null)}
                  className="rounded-full bg-slate-800 px-3 py-1 text-xs font-semibold text-slate-200 underline-offset-2 hover:text-white"
                >
                  Clear filter
                </button>
              )}
            </div>
          </div>

          <div className="rounded-2xl border border-slate-800/70 bg-gradient-to-br from-purple-500/15 via-sky-500/10 to-emerald-400/10 p-4 shadow-soft">
            <p className="text-xs uppercase tracking-wide text-slate-300">Newest winner</p>
            {newest ? (
              <div className="mt-3 space-y-3">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="text-sm font-semibold text-white">{newest.nominations[0]?.pitch ?? 'Winner pending'}</p>
                    <p className="text-xs text-slate-200/80">{newest.label}</p>
                    <p className="text-xs text-slate-300">{formatShortDate(newest.discussion_at ?? newest.created_at)}</p>
                  </div>
                  <RatingBadge value={newest.rating_summary?.average ?? newest.aggregates.rating_average} count={newest.rating_summary?.count} />
                </div>
                <div className="flex flex-wrap gap-2 text-xs text-slate-200">
                  {[newest.nominations[0]?.genre, newest.nominations[0]?.decade, newest.nominations[0]?.country]
                    .filter(Boolean)
                    .slice(0, 3)
                    .map((chip) => (
                      <span
                        key={chip as string}
                        className="rounded-full bg-slate-900/70 px-3 py-1 text-[0.7rem] uppercase tracking-wide text-slate-200"
                      >
                        {chip as string}
                      </span>
                    ))}
                  <span className="rounded-full bg-slate-900/80 px-3 py-1 text-[0.7rem] text-slate-300">
                    {newest.aggregates.vote_count} votes · {newest.aggregates.nomination_count} nominees
                  </span>
                </div>
                <Link
                  href={`/club/weeks/${newest.id}`}
                  className="inline-flex items-center gap-2 text-sm font-semibold text-emerald-200 hover:text-white"
                >
                  View full week
                  <span aria-hidden>→</span>
                </Link>
              </div>
            ) : (
              <p className="text-sm text-slate-300">No weeks available yet.</p>
            )}
          </div>
        </div>
      </Card>

      <WeekList weeks={filtered} emptyMessage="No weeks match these filters yet." />
    </div>
  );
}
