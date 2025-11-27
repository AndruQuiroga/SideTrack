import Link from "next/link";
import type { WeekSummary } from "@/lib/sample-data";

type WeekCardProps = {
  week: WeekSummary;
};

export function WeekCard({ week }: WeekCardProps) {
  const formatted = new Date(week.date).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  });

  return (
    <Link
      href={`/club/${week.id}`}
      className="group relative overflow-hidden rounded-3xl border border-slate-800/80 bg-sidetrack-soft/70 p-4 shadow-soft transition-transform hover:-translate-y-1 hover:border-sidetrack-accent/70 hover:bg-sidetrack-soft/90"
    >
      <div className="absolute inset-x-0 -top-24 h-40 bg-gradient-to-b from-purple-500/20 via-sky-400/10 to-transparent opacity-70 transition-opacity group-hover:opacity-100" />
      <div className="relative flex gap-4">
        <div className="relative h-20 w-20 shrink-0 overflow-hidden rounded-2xl border border-slate-700/60 bg-slate-900/80">
          {week.winner.coverUrl ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={week.winner.coverUrl}
              alt={`${week.winner.album} cover`}
              className="h-full w-full object-cover"
            />
          ) : (
            <div className="flex h-full w-full items-center justify-center text-[0.6rem] text-slate-500">
              No cover
            </div>
          )}
        </div>
        <div className="flex flex-1 flex-col justify-between">
          <div className="space-y-1">
            <p className="text-[0.7rem] font-medium uppercase tracking-wide text-slate-400">
              {formatted}
            </p>
            <h3 className="text-sm font-semibold text-slate-50">
              {week.winner.album}{" "}
              <span className="text-slate-400">· {week.winner.artist}</span>
            </h3>
            <p className="text-xs text-slate-400">{week.label}</p>
          </div>
          <div className="mt-3 flex flex-wrap items-center gap-2 text-[0.7rem] text-slate-300">
            <span className="inline-flex items-center gap-1 rounded-full bg-slate-900/70 px-2 py-1">
              <span className="h-1.5 w-1.5 rounded-full bg-amber-400" />
              {week.avgRating.toFixed(1)} avg · {week.ratingsCount} ratings
            </span>
            <span className="rounded-full bg-slate-900/60 px-2 py-1 text-slate-400">
              {week.participants} listeners
            </span>
            {week.tags.slice(0, 2).map((tag) => (
              <span
                key={tag}
                className="rounded-full bg-slate-900/60 px-2 py-1 text-slate-400"
              >
                {tag}
              </span>
            ))}
          </div>
        </div>
      </div>
    </Link>
  );
}
