import Link from "next/link";
import { PageShell } from "@/components/PageShell";
import { RatingBadge } from "@/components/RatingBadge";
import { weeks } from "@/lib/sample-data";

export default function HomePage() {
  const [latest, ...rest] = weeks;

  return (
    <PageShell
      title="Welcome to Sidetrack"
      description="Run your weekly album club on Discord, browse a living archive of winners, and explore each other's taste with rich listening stats."
      accent="Sidetrack Club · Weekly since 2025"
      actions={
        <div className="flex flex-wrap items-center gap-2">
          <Link
            href="/club"
            className="rounded-full bg-slate-50 px-4 py-2 text-xs font-semibold text-sidetrack-bg shadow-soft transition hover:bg-slate-200"
          >
            View club archive
          </Link>
          <Link
            href="/u/dreski"
            className="rounded-full border border-slate-600 bg-sidetrack-soft/70 px-3 py-2 text-xs font-medium text-slate-200 transition hover:border-sidetrack-accent hover:text-slate-50"
          >
            Peek a taste profile
          </Link>
        </div>
      }
    >
      <section className="grid gap-6 md:grid-cols-[3fr,2fr]">
        <div className="gradient-border relative overflow-hidden rounded-3xl border border-slate-800/80 bg-sidetrack-soft/80 p-6 shadow-soft">
          <div className="relative flex flex-col gap-6 md:flex-row">
            <div className="relative h-44 w-full shrink-0 overflow-hidden rounded-3xl border border-slate-700/60 bg-slate-900/80 md:h-52 md:w-52">
              {latest.winner.coverUrl ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={latest.winner.coverUrl}
                  alt={`${latest.winner.album} cover`}
                  className="h-full w-full object-cover"
                />
              ) : (
                <div className="flex h-full w-full items-center justify-center text-xs text-slate-500">
                  No cover
                </div>
              )}
            </div>
            <div className="flex flex-1 flex-col justify-between gap-4">
              <div>
                <p className="text-xs font-medium uppercase tracking-wide text-slate-400">
                  Latest Album of the Week
                </p>
                <h2 className="mt-2 text-lg font-semibold text-slate-50">
                  {latest.winner.album}{" "}
                  <span className="text-slate-400">
                    · {latest.winner.artist}
                  </span>
                </h2>
                <p className="mt-1 text-xs text-slate-400">
                  {latest.label} ·{" "}
                  {new Date(latest.date).toLocaleDateString(undefined, {
                    month: "short",
                    day: "numeric",
                    year: "numeric",
                  })}
                </p>
              </div>
              <div className="flex flex-wrap items-center gap-2 text-xs">
                <RatingBadge value={latest.avgRating} />
                <span className="rounded-full bg-slate-900/70 px-3 py-1 text-slate-300">
                  {latest.ratingsCount} ratings
                </span>
                <span className="rounded-full bg-slate-900/70 px-3 py-1 text-slate-300">
                  {latest.participants} participants
                </span>
                {latest.tags.slice(0, 3).map((tag) => (
                  <span
                    key={tag}
                    className="rounded-full bg-slate-900/60 px-3 py-1 text-slate-400"
                  >
                    {tag}
                  </span>
                ))}
              </div>
              <div className="mt-2 flex flex-wrap gap-2 text-xs">
                <Link
                  href={`/club/${latest.id}`}
                  className="rounded-full bg-slate-50 px-3 py-1.5 text-[0.7rem] font-semibold text-sidetrack-bg shadow-soft transition hover:bg-slate-200"
                >
                  Open this week&apos;s gallery
                </Link>
                <a
                  href="#club-explainer"
                  className="rounded-full border border-slate-600/80 bg-slate-900/60 px-3 py-1.5 text-[0.7rem] font-medium text-slate-200 hover:border-slate-400"
                >
                  How the club works
                </a>
              </div>
            </div>
          </div>
        </div>

        <aside className="flex flex-col gap-4 rounded-3xl border border-slate-800/80 bg-sidetrack-soft/70 p-5 shadow-soft">
          <h2 className="text-sm font-semibold text-slate-50">
            A quick glance at Sidetrack
          </h2>
          <p className="text-xs text-slate-300">
            Sidetrack runs your weekly album club on Discord, then turns each
            session into a permanent, browsable artifact. Over time, a shared
            history of picks, ratings, and listening habits emerges.
          </p>
          <div className="grid grid-cols-3 gap-3 text-xs">
            <div className="rounded-2xl bg-slate-900/70 p-3">
              <p className="text-[0.65rem] text-slate-400">Weeks logged</p>
              <p className="mt-1 text-lg font-semibold text-slate-50">3</p>
            </div>
            <div className="rounded-2xl bg-slate-900/70 p-3">
              <p className="text-[0.65rem] text-slate-400">Unique albums</p>
              <p className="mt-1 text-lg font-semibold text-slate-50">12</p>
            </div>
            <div className="rounded-2xl bg-slate-900/70 p-3">
              <p className="text-[0.65rem] text-slate-400">Club members</p>
              <p className="mt-1 text-lg font-semibold text-slate-50">8</p>
            </div>
          </div>
          <p className="text-[0.7rem] text-slate-400">
            Later, this home view can evolve into a personalised dashboard:
            synced listening stats, mood graphs, and what your friends are
            spinning right now.
          </p>
        </aside>
      </section>

      <section
        id="club-explainer"
        className="mt-4 grid gap-4 rounded-3xl border border-slate-800/80 bg-sidetrack-soft/60 p-5 text-xs text-slate-300 shadow-soft md:grid-cols-3"
      >
        <div className="space-y-2">
          <h3 className="text-sm font-semibold text-slate-50">
            1. Nominate & vote on Discord
          </h3>
          <p>
            The bot collects album nominations in a thread, then runs a 1st/2nd
            choice ranked poll. Results are stored in the Sidetrack API.
          </p>
        </div>
        <div className="space-y-2">
          <h3 className="text-sm font-semibold text-slate-50">
            2. Listen together, talk it out
          </h3>
          <p>
            Each week gets its own discussion and ratings threads. Those
            comments and scores power the archive you see here.
          </p>
        </div>
        <div className="space-y-2">
          <h3 className="text-sm font-semibold text-slate-50">
            3. Build a shared taste map
          </h3>
          <p>
            Over time, Sidetrack becomes a living map of your group&apos;s
            taste—per-week snapshots, personal profiles, and compatibility
            scores derived from your listening history.
          </p>
        </div>
      </section>
    </PageShell>
  );
}
