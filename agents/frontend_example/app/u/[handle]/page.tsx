import { notFound } from "next/navigation";
import { PageShell } from "@/components/PageShell";
import { profiles } from "@/lib/sample-data";

type ProfilePageProps = {
  params: { handle: string };
};

export default function ProfilePage({ params }: ProfilePageProps) {
  const profile = profiles[params.handle];

  if (!profile) {
    return notFound();
  }

  return (
    <PageShell
      title={profile.displayName}
      description={profile.tagline ?? "Sidetrack listener profile"}
      accent={`@${profile.handle}`}
    >
      <section className="grid gap-6 lg:grid-cols-[minmax(0,2fr),minmax(0,1.2fr)]">
        <div className="space-y-4 rounded-3xl border border-slate-800/80 bg-sidetrack-soft/70 p-5 shadow-soft">
          <h2 className="text-sm font-semibold text-slate-50">
            Snapshot · Club & ratings
          </h2>
          <div className="grid gap-3 text-xs text-slate-300 sm:grid-cols-3">
            <div className="rounded-2xl bg-slate-900/80 p-3">
              <p className="text-[0.65rem] text-slate-400">Albums rated</p>
              <p className="mt-1 text-xl font-semibold text-slate-50">
                {profile.stats.albumsRated}
              </p>
            </div>
            <div className="rounded-2xl bg-slate-900/80 p-3">
              <p className="text-[0.65rem] text-slate-400">Weeks joined</p>
              <p className="mt-1 text-xl font-semibold text-slate-50">
                {profile.stats.weeksJoined}
              </p>
            </div>
            <div className="rounded-2xl bg-slate-900/80 p-3">
              <p className="text-[0.65rem] text-slate-400">
                Avg album rating
              </p>
              <p className="mt-1 text-xl font-semibold text-slate-50">
                {profile.stats.avgRating.toFixed(1)}
              </p>
            </div>
          </div>

          <div className="space-y-2 text-xs text-slate-300">
            <h3 className="text-sm font-semibold text-slate-50">
              Recent club picks
            </h3>
            <ul className="space-y-2">
              {profile.recentAlbums.map((album) => (
                <li
                  key={`${album.album}-${album.artist}`}
                  className="flex items-center justify-between rounded-2xl bg-slate-900/80 px-3 py-2"
                >
                  <div>
                    <p className="text-[0.8rem] font-medium text-slate-50">
                      {album.album}
                    </p>
                    <p className="text-[0.7rem] text-slate-400">
                      {album.artist}
                    </p>
                  </div>
                  {album.rating && (
                    <span className="rounded-full bg-slate-800 px-2 py-1 text-[0.7rem] text-amber-300">
                      {album.rating.toFixed(1)}
                    </span>
                  )}
                </li>
              ))}
            </ul>
          </div>
        </div>

        <aside className="space-y-4 rounded-3xl border border-slate-800/80 bg-sidetrack-soft/70 p-5 shadow-soft">
          <h2 className="text-sm font-semibold text-slate-50">
            Taste sketch
          </h2>
          <div className="space-y-2 text-xs text-slate-300">
            <p>
              This column will eventually visualise full taste profiles: genre
              distributions, mood clusters, and how this listener overlaps with
              their friends.
            </p>
            <div className="flex flex-wrap gap-2">
              {profile.topGenres.map((genre) => (
                <span
                  key={genre}
                  className="rounded-full bg-slate-900/80 px-3 py-1 text-[0.7rem] text-slate-200"
                >
                  {genre}
                </span>
              ))}
            </div>
            <p className="text-[0.7rem] text-slate-400">
              For now, this is a static sketch wired to sample data. The next
              steps are wiring this to real listening history and compatibility
              metrics from the analysis layer.
            </p>
          </div>
        </aside>
      </section>
    </PageShell>
  );
}
