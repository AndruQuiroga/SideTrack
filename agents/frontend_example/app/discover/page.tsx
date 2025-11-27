import { PageShell } from "@/components/PageShell";

export default function DiscoverPage() {
  return (
    <PageShell
      title="Discover & compare"
      description="This is where Sidetrack will grow into a social music tracker: listen-along sessions, shared queues, and compatibility-driven recommendations."
      accent="Coming soon · Taste graphs & friend blends"
    >
      <section className="grid gap-4 rounded-3xl border border-slate-800/80 bg-sidetrack-soft/70 p-5 text-xs text-slate-300 shadow-soft md:grid-cols-2">
        <div className="space-y-3">
          <h2 className="text-sm font-semibold text-slate-50">
            Listening right now
          </h2>
          <p>
            In the full app, this panel will reflect live or near-real-time
            listening from your club, powered by Spotify / Last.fm integration.
          </p>
          <p>
            For now, treat this page as a design stub. When the API and worker
            stack are ready, we&apos;ll wire it to real data and add filters,
            timelines, and &quot;listen with&quot; controls.
          </p>
        </div>
        <div className="space-y-3">
          <h2 className="text-sm font-semibold text-slate-50">
            Compatibility & shared picks
          </h2>
          <p>
            Sidetrack will surface who you secretly align with, where your
            tastes diverge, and which albums &quot;bridge&quot; different
            corners of the group.
          </p>
          <p>
            The layout here is intentionally minimal so the future graphs,
            timelines, and blended playlists have room to breathe.
          </p>
        </div>
      </section>
    </PageShell>
  );
}
