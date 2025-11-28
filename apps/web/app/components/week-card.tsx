import Link from 'next/link';

import { WeekDetailWithRatings } from '../../src/api/weeks';
import { RatingBadge } from './rating-badge';

interface WeekCardProps {
  week: WeekDetailWithRatings;
}

function formatDate(date?: string | null) {
  if (!date) return 'Date TBC';
  const parsed = new Date(date);
  if (Number.isNaN(parsed.getTime())) return 'Date TBC';
  return parsed.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
}

function gradientFromSeed(seed: string) {
  const hash = seed.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0);
  const hue = hash % 360;
  const hue2 = (hash * 3) % 360;
  return `linear-gradient(135deg, hsl(${hue}, 70%, 55%), hsl(${hue2}, 70%, 45%))`;
}

function parseAlbumAndArtist(pitch?: string | null) {
  if (!pitch) return { album: 'Winner pending', artist: 'Nominations open' };
  const [left, right] = pitch.split('—').map((part) => part.trim());
  return { album: left ?? pitch, artist: right ?? '' };
}

export function WeekCard({ week }: WeekCardProps) {
  const winner = week.nominations[0];
  const ratingAvg = week.rating_summary?.average ?? week.aggregates.rating_average;
  const ratingCount = week.rating_summary?.count ?? week.aggregates.rating_count;
  const tags = [winner?.genre, winner?.decade, winner?.country].filter(Boolean) as string[];
  const { album, artist } = parseAlbumAndArtist(winner?.pitch);
  const coverStyle = { backgroundImage: gradientFromSeed(winner?.album_id ?? week.id) };

  return (
    <Link
      href={`/club/weeks/${week.id}`}
      className="group relative flex flex-col overflow-hidden rounded-3xl border border-slate-800/80 bg-sidetrack-soft/70 p-4 shadow-soft transition-transform hover:-translate-y-1 hover:border-sidetrack-accent/70 hover:bg-sidetrack-soft/90"
    >
      <div className="absolute inset-x-0 -top-24 h-40 bg-gradient-to-b from-purple-500/20 via-sky-400/10 to-transparent opacity-70 transition-opacity group-hover:opacity-100" />
      <div className="relative flex gap-4">
        <div
          className="relative aspect-square w-24 shrink-0 overflow-hidden rounded-2xl border border-slate-800/60 shadow-soft"
          style={coverStyle}
        >
          <div className="absolute inset-0 bg-gradient-to-br from-black/40 via-transparent to-black/20" />
          <div className="absolute bottom-2 left-2 rounded-full bg-black/60 px-2 py-0.5 text-[0.65rem] font-semibold uppercase tracking-wide text-white">
            {week.label}
          </div>
        </div>
        <div className="flex-1 space-y-2">
          <div className="flex items-start justify-between gap-2">
            <div className="space-y-0.5">
              <p className="text-xs uppercase tracking-wide text-slate-400">{formatDate(week.discussion_at ?? week.created_at)}</p>
              <h3 className="text-base font-semibold text-slate-50">{album}</h3>
              <p className="text-xs text-slate-300">{artist || 'Queued to win'}</p>
            </div>
            <RatingBadge value={ratingAvg ?? undefined} count={ratingCount} />
          </div>

          <div className="flex flex-wrap items-center gap-2 text-[0.75rem] text-slate-300">
            <span className="inline-flex items-center gap-1 rounded-full bg-slate-900/70 px-2.5 py-1">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
              {week.aggregates.vote_count} votes
            </span>
            <span className="inline-flex items-center gap-1 rounded-full bg-slate-900/70 px-2.5 py-1 text-slate-300">
              <span className="h-1.5 w-1.5 rounded-full bg-sky-400" />
              {week.aggregates.nomination_count} nominations
            </span>
            {week.source === 'fallback' && (
              <span className="rounded-full bg-amber-500/20 px-2.5 py-1 text-[0.7rem] font-semibold text-amber-200">
                Demo data
              </span>
            )}
            {tags.slice(0, 3).map((tag) => (
              <span key={tag} className="rounded-full bg-slate-900/70 px-2.5 py-1 text-slate-400">
                {tag}
              </span>
            ))}
            {!tags.length && <span className="rounded-full bg-slate-900/60 px-2.5 py-1 text-slate-500">Tags incoming</span>}
          </div>
        </div>
      </div>
    </Link>
  );
}
