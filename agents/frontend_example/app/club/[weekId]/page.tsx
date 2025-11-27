import { notFound } from "next/navigation";
import { PageShell } from "@/components/PageShell";
import { RatingBadge } from "@/components/RatingBadge";
import { weekDetails } from "@/lib/sample-data";

type WeekPageProps = {
  params: { weekId: string };
};

export default function WeekDetailPage({ params }: WeekPageProps) {
  const week = weekDetails[params.weekId];

  if (!week) {
    return notFound();
  }

  const formatted = new Date(week.date).toLocaleDateString(undefined, {
    month: "long",
    day: "numeric",
    year: "numeric",
  });

  return (
    <PageShell
      title={week.winner.album}
      description={`Sidetrack Club · ${week.label}`}
      accent={`Album of the Week · ${formatted}`}
    >
      <section className="grid gap-6 lg:grid-cols-[minmax(0,2fr),minmax(0,1.3fr)]">
        <div className="space-y-4 rounded-3xl border border-slate-800/80 bg-sidetrack-soft/70 p-5 shadow-soft">
          <div className="flex flex-col gap-4 sm:flex-row">
            <div className="relative h-36 w-36 shrink-0 overflow-hidden rounded-3xl border border-slate-700/70 bg-slate-900/80 sm:h-40 sm:w-40">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={week.winner.coverUrl ?? "https://images.pexels.com/photos/164745/pexels-photo-164745.jpeg?auto=compress&cs=tinysrgb&w=400"}
                alt={`${week.winner.album} cover`}
                className="h-full w-full object-cover"
              />
            </div>
            <div className="flex flex-1 flex-col justify-between gap-3">
              <div>
                <h2 className="text-lg font-semibold text-slate-50">
                  {week.winner.album}
                </h2>
                <p className="text-sm text-slate-400">
                  {week.winner.artist} · {week.winner.year}
                </p>
                <p className="mt-1 text-xs text-slate-400">
                  {week.tags.join(" · ")}
                </p>
              </div>
              <div className="flex flex-wrap items-center gap-2 text-xs">
                <RatingBadge value={week.avgRating} />
                <span className="rounded-full bg-slate-900/70 px-3 py-1 text-slate-300">
                  {week.ratingsCount} ratings
                </span>
                <span className="rounded-full bg-slate-900/70 px-3 py-1 text-slate-300">
                  {week.participants} participants
                </span>
              </div>
            </div>
          </div>

          <div className="space-y-3 text-xs text-slate-300">
            <h3 className="text-sm font-semibold text-slate-50">
              What was in the running?
            </h3>
            <p>
              In the full app, this block can also show a visual breakdown of
              votes (1st vs 2nd place), nominee tags, and links back to the original
              Discord threads.
            </p>
          </div>

          <div className="space-y-2">
            {week.nominees.map((nominee) => (
              <div
                key={nominee.id}
                className="flex flex-col gap-2 rounded-2xl border border-slate-800/80 bg-slate-900/70 p-3 text-xs text-slate-200 sm:flex-row sm:items-center sm:justify-between"
              >
                <div>
                  <p className="font-medium text-slate-50">
                    {nominee.album}{" "}
                    <span className="text-slate-400">· {nominee.artist}</span>
                  </p>
                  <p className="mt-1 text-[0.7rem] text-slate-400">
                    Nominated by {nominee.nominator}
                  </p>
                  <p className="mt-1 text-[0.7rem] text-slate-300">
                    {nominee.pitch}
                  </p>
                </div>
                <div className="mt-2 flex items-center gap-2 sm:mt-0 sm:flex-col sm:items-end">
                  <span className="inline-flex items-center rounded-full bg-slate-800 px-2 py-1 text-[0.7rem] text-slate-200">
                    #{nominee.rank} in poll
                  </span>
                  <span className="text-[0.7rem] text-slate-400">
                    Score: {nominee.score.toFixed(1)}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>

        <aside className="space-y-4 rounded-3xl border border-slate-800/80 bg-sidetrack-soft/70 p-5 shadow-soft">
          <div className="space-y-1">
            <h3 className="text-sm font-semibold text-slate-50">
              How did everyone feel?
            </h3>
            <p className="text-xs text-slate-300">
              These are example ratings pulled from the Discord thread. In
              production, this panel will show per-user scores and links back
              to their profiles and listening stats.
            </p>
          </div>
          <div className="space-y-3">
            {week.ratings.map((rating) => (
              <div
                key={rating.user}
                className="rounded-2xl bg-slate-900/70 p-3 text-xs text-slate-200"
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="font-medium text-slate-50">
                    {rating.user}
                  </span>
                  <span className="rounded-full bg-slate-800 px-2 py-1 text-[0.7rem] text-amber-300">
                    {rating.value.toFixed(1)} / 5.0
                  </span>
                </div>
                {rating.favoriteTrack && (
                  <p className="mt-1 text-[0.7rem] text-slate-400">
                    Favorite track:{" "}
                    <span className="text-slate-200">
                      {rating.favoriteTrack}
                    </span>
                  </p>
                )}
                {rating.highlight && (
                  <p className="mt-2 text-[0.7rem] text-slate-300">
                    {rating.highlight}
                  </p>
                )}
              </div>
            ))}
          </div>
        </aside>
      </section>
    </PageShell>
  );
}
