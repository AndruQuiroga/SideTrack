import { notFound } from 'next/navigation';

import { fetchProfileForServer } from '../../../src/api/profile';
import { Card, SectionHeading } from '../../components/ui';
import { PageShell } from '../../components/page-shell';

interface ProfilePageProps {
  params: { id: string };
}

export default async function ProfilePage({ params }: ProfilePageProps) {
  const profile = await fetchProfileForServer(params.id);
  if (!profile) {
    notFound();
  }

  return (
    <PageShell
      title={profile.display_name ?? 'Sidetrack Listener'}
      description="A taste snapshot pulled from listening stats and club activity. More private data will appear once accounts are linked."
      accent="Profile preview"
      actions={<span className="pill text-[0.65rem]">Range: {profile.range ?? '30d'}</span>}
    >
      <div className="grid gap-5 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <SectionHeading
            eyebrow="Listener overview"
            title={profile.display_name ?? 'Sidetrack Listener'}
            aside={<span className="rounded-full bg-slate-900/70 px-3 py-1 text-xs text-slate-300">Visibility: {profile.visibility}</span>}
          />
          <p className="mt-2 text-sm text-slate-300">
            Quick stats and taste metrics based on recent listening. This view will grow with real Spotify/Last.fm data and club history.
          </p>
          {profile.now_playing ? (
            <div className="mt-4 rounded-2xl border border-emerald-500/40 bg-emerald-500/10 p-4 text-sm text-emerald-100">
              <p className="uppercase text-[0.7rem] tracking-wide">Now playing</p>
              <p className="text-base font-semibold text-white">
                {profile.now_playing.track_name} · <span className="text-emerald-200">{profile.now_playing.artist_name}</span>
              </p>
              {profile.now_playing.album_name && <p className="text-xs text-emerald-200/80">{profile.now_playing.album_name}</p>}
            </div>
          ) : (
            <div className="mt-4 rounded-2xl border border-slate-800/70 bg-slate-900/60 p-4 text-sm text-slate-300">
              <p className="uppercase text-[0.7rem] tracking-wide text-slate-400">Now playing</p>
              <p>Link Spotify or Last.fm to surface live playback here.</p>
            </div>
          )}
        </Card>

        <Card className="space-y-3">
          <SectionHeading eyebrow="Recency" title="Recent listens" />
          {profile.recent_listens?.length ? (
            <ul className="space-y-2 text-sm text-slate-200">
              {profile.recent_listens.slice(0, 5).map((listen, idx) => (
                <li key={idx} className="flex items-center justify-between rounded-2xl border border-slate-800/70 bg-slate-900/60 px-3 py-2">
                  <span className="truncate">{listen.track_name}</span>
                  <span className="text-xs text-slate-400">
                    {listen.listened_at
                      ? new Date(listen.listened_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
                      : 'Recently'}
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-slate-400">Recent listens will appear once private data is enabled.</p>
          )}
        </Card>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <Card className="space-y-3">
          <SectionHeading eyebrow="Top picks" title="Top Artists" />
          <ul className="space-y-2 text-sm text-slate-200">
            {profile.top_artists.slice(0, 5).map((artist) => (
              <li key={artist.name} className="flex items-center justify-between rounded-2xl border border-slate-800/70 bg-slate-900/60 px-3 py-2">
                <span>{artist.name}</span>
                <span className="rounded-full bg-slate-900/70 px-3 py-1 text-xs text-slate-300">
                  {artist.play_count} plays
                </span>
              </li>
            ))}
          </ul>
        </Card>

        <Card className="space-y-3">
          <SectionHeading eyebrow="Vibe map" title="Top Genres" />
          <ul className="space-y-2 text-sm text-slate-200">
            {profile.top_genres.slice(0, 5).map((genre) => (
              <li key={genre.name} className="flex items-center justify-between rounded-2xl border border-slate-800/70 bg-slate-900/60 px-3 py-2">
                <span>{genre.name}</span>
                <span className="text-xs text-slate-400">{genre.play_count} plays</span>
              </li>
            ))}
          </ul>
        </Card>
      </div>

      <Card className="space-y-3">
        <SectionHeading eyebrow="Taste metrics" title="Mood and energy profile" />
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 md:grid-cols-3">
          {profile.taste_metrics.map((metric) => (
            <div key={metric.id} className="rounded-2xl border border-slate-800 bg-slate-900/60 p-3">
              <p className="text-sm font-semibold text-white">{metric.label}</p>
              <p className="text-2xl font-bold text-sidetrack-accent">{metric.value}</p>
              {metric.percentile !== undefined && (
                <p className="text-xs text-slate-400">Percentile: {Math.round((metric.percentile ?? 0) * 100)}%</p>
              )}
            </div>
          ))}
        </div>
      </Card>
    </PageShell>
  );
}
