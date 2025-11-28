import Link from 'next/link';
import { notFound } from 'next/navigation';
import { ListeningTimelinePoint } from '@sidetrack/shared';

import { fetchProfileForServer } from '../../../src/api/profile';
import { Card, Pill, SectionHeading } from '../../components/ui';
import { PageShell } from '../../components/page-shell';

interface ProfilePageProps {
  params: { id: string };
}

function Sparkline({ points }: { points: ListeningTimelinePoint[] }) {
  if (!points.length) return <p className="text-xs text-slate-400">Timeline coming soon once listens sync.</p>;
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
  const profile = await fetchProfileForServer(params.id);
  if (!profile) {
    notFound();
  }

  const compatibility = Math.round((profile.taste_metrics[0]?.percentile ?? 0.72) * 100);
  const recommendations = profile.top_genres.slice(0, 3).map((genre) => `${genre.name} essentials`);

  return (
    <PageShell
      title={profile.display_name ?? 'Sidetrack Listener'}
      description="Stats, taste graphs, compatibility, and live now-playing once accounts are linked."
      accent="Profile preview"
      actions={<Pill className="bg-slate-900/70 text-[0.65rem]">Range: {profile.range ?? '30d'}</Pill>}
    >
      <div className="grid gap-5 lg:grid-cols-[1.6fr,1fr]">
        <Card className="space-y-4">
          <SectionHeading
            eyebrow="Listener overview"
            title={profile.display_name ?? 'Sidetrack Listener'}
            aside={<span className="rounded-full bg-slate-900/70 px-3 py-1 text-xs text-slate-300">Visibility: {profile.visibility}</span>}
          />
          <div className="flex flex-wrap items-center gap-3 text-sm text-slate-300">
            <span className="rounded-full bg-slate-900 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-slate-200">
              Follow
            </span>
            <Link href={`/compare?userA=${params.id}&userB=demo`} className="rounded-full bg-slate-800 px-3 py-1 text-xs font-semibold text-emerald-200 hover:text-white">
              Compare tastes →
            </Link>
            <span className="rounded-full bg-emerald-500/20 px-3 py-1 text-xs font-semibold text-emerald-200">
              Compatibility {compatibility}%
            </span>
          </div>

          {profile.now_playing ? (
            <div className="rounded-2xl border border-emerald-500/40 bg-emerald-500/10 p-4 text-sm text-emerald-100">
              <p className="uppercase text-[0.7rem] tracking-wide">Now playing</p>
              <p className="text-base font-semibold text-white">
                {profile.now_playing.track_name} · <span className="text-emerald-200">{profile.now_playing.artist_name}</span>
              </p>
              {profile.now_playing.album_name && <p className="text-xs text-emerald-200/80">{profile.now_playing.album_name}</p>}
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
                <li key={idx} className="flex items-center justify-between rounded-2xl border border-slate-800/70 bg-slate-900/60 px-3 py-2">
                  <span className="truncate">{listen.track_name}</span>
                  <span className="text-xs text-slate-400">{formatListenTime(listen.listened_at)}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-slate-400">Recent listens will appear once private data is enabled.</p>
          )}
          <p className="text-xs text-slate-400">Real-time presence lights up when accounts are linked.</p>
        </Card>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <Card className="space-y-3">
          <SectionHeading eyebrow="Top picks" title="Top Artists" />
          <ul className="space-y-2 text-sm text-slate-200">
            {profile.top_artists.slice(0, 5).map((artist) => (
              <li key={artist.name} className="flex items-center justify-between rounded-2xl border border-slate-800/70 bg-slate-900/60 px-3 py-2">
                <span>{artist.name}</span>
                <span className="rounded-full bg-slate-900/70 px-3 py-1 text-xs text-slate-300">{artist.play_count} plays</span>
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

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[1.2fr,1fr]">
        <Card className="space-y-3">
          <SectionHeading eyebrow="Taste metrics" title="Mood + energy fingerprint" />
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            {profile.taste_metrics.map((metric) => (
              <div key={metric.id} className="rounded-2xl border border-slate-800 bg-slate-900/60 p-3">
                <div className="flex items-center justify-between">
                  <p className="text-sm font-semibold text-white">{metric.label}</p>
                  {metric.percentile !== undefined && (
                    <span className="text-xs text-slate-400">{Math.round((metric.percentile ?? 0) * 100)}%</span>
                  )}
                </div>
                <div className="mt-2 h-2 rounded-full bg-slate-800">
                  <div
                    className="h-full rounded-full bg-gradient-to-r from-emerald-400 via-sky-400 to-purple-500"
                    style={{ width: `${Math.min((metric.value / 1) * 100, 100)}%`, minWidth: '6%' }}
                  />
                </div>
                <p className="mt-1 text-xs text-slate-400">{metric.value} {metric.unit ?? ''}</p>
              </div>
            ))}
          </div>
          <p className="text-xs text-slate-400">
            These bars will come straight from Spotify/Last.fm audio features once linked. They also power compatibility and recommendations.
          </p>
        </Card>

        <Card className="space-y-3">
          <SectionHeading eyebrow="Trend" title="Listening timeline" />
          <Sparkline points={profile.timeline} />
          <p className="text-xs text-slate-400">
            Showing {profile.timeline.length} data points across {profile.range ?? 'recent weeks'}. Peaks highlight heavy listening days.
          </p>
        </Card>
      </div>

      <Card className="space-y-3">
        <SectionHeading eyebrow="Social" title="Recommendations + actions" />
        <div className="grid gap-3 md:grid-cols-3">
          {recommendations.map((rec) => (
            <div key={rec} className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4 text-sm text-slate-200">
              <p className="font-semibold text-white">{rec}</p>
              <p className="mt-1 text-slate-400">
                Auto playlists and friend blends will appear here once listening data and club ratings sync.
              </p>
            </div>
          ))}
          <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4 text-sm text-slate-200">
            <p className="font-semibold text-white">Invite a friend</p>
            <p className="mt-1 text-slate-400">Share your profile link to compare compatibility instantly.</p>
            <Link href="/compare?userA=demo&userB=demo2" className="mt-2 inline-flex text-emerald-200 hover:text-white">
              Compare →
            </Link>
          </div>
        </div>
      </Card>
    </PageShell>
  );
}
