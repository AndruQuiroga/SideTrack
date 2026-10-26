import Link from 'next/link';
import { notFound } from 'next/navigation';
import { ListeningTimelinePoint } from '@sidetrack/api-client';

import { fetchProfileForServer } from '../../lib/api/profile';
import { loadAs } from '../../lib/server-api';
import { sessionUserId } from '../../lib/session';
import { AccessNotice, Card, Pill, SectionHeading } from '../../components/ui';
import { TasteRadar } from '../../components/taste-radar';
import { PageShell } from '../../components/page-shell';

interface ProfilePageProps {
  params: { id: string };
}

function Sparkline({ points }: { points: ListeningTimelinePoint[] }) {
  if (!points.length)
    return <p className="text-xs text-slate-400">Timeline coming soon once listens sync.</p>;
  const max = Math.max(...points.map((p) => p.play_count), 1);
  const coords = points
    .map((point, idx) => {
      const x = (idx / Math.max(points.length - 1, 1)) * 100;
      const y = 40 - (point.play_count / max) * 35;
      return `${x},${y}`;
    })
    .join(' ');
  return (
    <svg viewBox="0 0 100 40" className="h-16 w-full text-emerald-300">
      <polyline fill="none" stroke="currentColor" strokeWidth="2" points={coords} />
    </svg>
  );
}

function formatListenTime(input?: string) {
  if (!input) return 'Recently';
  const date = new Date(input);
  if (Number.isNaN(date.getTime())) return 'Recently';
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

export default async function ProfilePage({ params }: ProfilePageProps) {
  // The API call acts for the session user, never for the user named in the URL.
  const result = await loadAs(await sessionUserId(), (api) =>
    fetchProfileForServer(api, params.id),
  );
  if (result.state === 'not-found') notFound();
  if (result.state !== 'ok') {
    return (
      <PageShell title="Profile" accent="Profile">
        <AccessNotice state={result.state} what="profile" audience="its owner and club members" />
      </PageShell>
    );
  }
  const profile = result.data;

  return (
    <PageShell
      title={profile.display_name ?? 'Sidetrack Listener'}
      description="Stats, taste graphs, compatibility, and live now-playing once accounts are linked."
      accent="Profile preview"
      actions={
        <Pill className="bg-slate-900/70 text-[0.65rem]">Range: {profile.range ?? '30d'}</Pill>
      }
    >
      <div className="grid gap-5 lg:grid-cols-[1.6fr,1fr]">
        <Card className="space-y-4">
          <SectionHeading
            eyebrow="Listener overview"
            title={profile.display_name ?? 'Sidetrack Listener'}
            aside={
              <span className="rounded-full bg-slate-900/70 px-3 py-1 text-xs text-slate-300">
                Visibility: {profile.visibility}
              </span>
            }
          />
          <div className="flex flex-wrap items-center gap-3 text-sm text-slate-300">
            <span className="rounded-full bg-slate-900 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-slate-200">
              Follow
            </span>
            <Link
              href={`/compare?userA=${params.id}`}
              className="rounded-full bg-slate-800 px-3 py-1 text-xs font-semibold text-emerald-200 hover:text-white"
            >
              Compare tastes →
            </Link>
          </div>

          {profile.now_playing ? (
            <div className="rounded-2xl border border-emerald-500/40 bg-emerald-500/10 p-4 text-sm text-emerald-100">
              <p className="uppercase text-[0.7rem] tracking-wide">Now playing</p>
              <p className="text-base font-semibold text-white">
                {profile.now_playing.track_name} ·{' '}
                <span className="text-emerald-200">{profile.now_playing.artist_name}</span>
              </p>
              {profile.now_playing.album_name && (
                <p className="text-xs text-emerald-200/80">{profile.now_playing.album_name}</p>
              )}
            </div>
          ) : (
            <div className="rounded-2xl border border-slate-800/70 bg-slate-900/60 p-4 text-sm text-slate-300">
              <p className="uppercase text-[0.7rem] tracking-wide text-slate-400">Now playing</p>
              <p>Link Spotify or Last.fm to surface live playback here.</p>
            </div>
          )}
        </Card>

        <Card className="space-y-3">
          <SectionHeading eyebrow="Recency" title="Recent listens" />
          {profile.recent_listens?.length ? (
            <ul className="space-y-2 text-sm text-slate-200">
              {profile.recent_listens.slice(0, 6).map((listen, idx) => (
                <li
                  key={idx}
                  className="flex items-center justify-between rounded-2xl border border-slate-800/70 bg-slate-900/60 px-3 py-2"
                >
                  <span className="truncate">{listen.track_name}</span>
                  <span className="text-xs text-slate-400">
                    {formatListenTime(listen.listened_at)}
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-slate-400">
              Recent listens will appear once private data is enabled.
            </p>
          )}
          <div className="flex items-center justify-between">
            <p className="text-xs text-slate-400">
              Real-time presence lights up when accounts are linked.
            </p>
            <Link
              href={`/u/${params.id}/listening`}
              className="text-xs text-emerald-200 hover:text-white"
            >
              View full history →
            </Link>
          </div>
        </Card>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <Card className="space-y-3">
          <SectionHeading eyebrow="Top picks" title="Top Artists" />
          <ul className="space-y-2 text-sm text-slate-200">
            {profile.top_artists.slice(0, 5).map((artist) => (
              <li
                key={artist.name}
                className="flex items-center justify-between rounded-2xl border border-slate-800/70 bg-slate-900/60 px-3 py-2"
              >
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
              <li
                key={genre.name}
                className="flex items-center justify-between rounded-2xl border border-slate-800/70 bg-slate-900/60 px-3 py-2"
              >
                <span>{genre.name}</span>
                <span className="text-xs text-slate-400">{genre.play_count} plays</span>
              </li>
            ))}
          </ul>
        </Card>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[1.2fr,1fr]">
        <Card className="space-y-3">
          <SectionHeading eyebrow="Taste metrics" title="Mood + energy fingerprint" />
          {profile.taste_metrics.length === 0 ? (
            <p className="text-sm text-slate-400">
              Taste metrics aren&apos;t available yet. They&apos;ll come from Sidetrack&apos;s own
              audio analysis once it ships.
            </p>
          ) : (
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-3">
                <p className="mb-2 text-sm font-semibold text-white">Radar</p>
                <TasteRadar metrics={profile.taste_metrics} />
              </div>
              <div className="space-y-3">
                {profile.taste_metrics.slice(0, 3).map((metric) => (
                  <div
                    key={metric.id}
                    className="rounded-2xl border border-slate-800 bg-slate-900/60 p-3"
                  >
                    <div className="flex items-center justify-between">
                      <p className="text-sm font-semibold text-white">{metric.label}</p>
                      {metric.percentile !== undefined && (
                        <span className="text-xs text-slate-400">
                          {Math.round((metric.percentile ?? 0) * 100)}%
                        </span>
                      )}
                    </div>
                    <div className="mt-2 h-2 rounded-full bg-slate-800">
                      <div
                        className="h-full rounded-full bg-gradient-to-r from-emerald-400 via-sky-400 to-purple-500"
                        style={{
                          width: `${Math.min((metric.value / 1) * 100, 100)}%`,
                          minWidth: '6%',
                        }}
                      />
                    </div>
                    <p className="mt-1 text-xs text-slate-400">
                      {metric.value} {metric.unit ?? ''}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </Card>

        <Card className="space-y-3">
          <SectionHeading eyebrow="Trend" title="Listening timeline" />
          <Sparkline points={profile.timeline} />
          <p className="text-xs text-slate-400">
            Showing {profile.timeline.length} data points across {profile.range ?? 'recent weeks'}.
            Peaks highlight heavy listening days.
          </p>
        </Card>
      </div>

      <Card className="space-y-3">
        <SectionHeading eyebrow="Social" title="Compare with a friend" />
        <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4 text-sm text-slate-200">
          <p className="text-slate-400">
            Share this profile link, or compare it with another listener&apos;s profile.
          </p>
          <Link
            href={`/compare?userA=${params.id}`}
            className="mt-2 inline-flex text-emerald-200 hover:text-white"
          >
            Compare →
          </Link>
        </div>
      </Card>
    </PageShell>
  );
}
