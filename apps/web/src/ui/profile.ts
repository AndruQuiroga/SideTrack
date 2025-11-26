import { ProfilePageData } from '../api/profile';
import { renderBarChart, renderLineChart } from './components/chart';
import { renderMetricGrid } from './components/metricCard';
import { PageMetadata, buildProfileMetadata } from './metadata';

export interface ProfileRenderResult {
  metadata: PageMetadata;
  body: string;
  state: 'loading' | 'error' | 'ready';
  errorMessage?: string;
}

function renderNowPlaying(profile: ProfilePageData): string {
  if (!profile.private_data_allowed) {
    return `
<section class="profile-now-playing gated">
  <h3>Now Playing & Recent Listens</h3>
  <p class="state state-locked">Sign in to view live listening data.</p>
</section>
`.trim();
  }

  if (!profile.worker_sync_ready) {
    return `
<section class="profile-now-playing gated">
  <h3>Now Playing & Recent Listens</h3>
  <p class="state state-empty">Listening sync is not ready yet. Once workers connect, this section will light up.</p>
</section>
`.trim();
  }

  const nowPlayingCopy = profile.now_playing
    ? `<p class="now-playing-track"><strong>${profile.now_playing.track_name}</strong> — ${profile.now_playing.artist_name}</p>`
    : '<p class="state state-empty">Nothing is playing right now.</p>';

  const recentListens = (profile.recent_listens ?? []).slice(0, 5);
  const recentCopy = recentListens.length
    ? `<ul class="recent-listens">${recentListens
        .map(
          (listen) =>
            `<li><span class="recent-track">${listen.track_name}</span><span class="recent-artist">${listen.artist_name}</span></li>`
        )
        .join('')}</ul>`
    : '<p class="state state-empty">No listens have been synced yet.</p>';

  return `
<section class="profile-now-playing">
  <h3>Now Playing & Recent Listens</h3>
  ${nowPlayingCopy}
  ${recentCopy}
</section>
`.trim();
}

export function renderProfilePage(profile?: ProfilePageData, options?: { loading?: boolean; error?: string }): ProfileRenderResult {
  const displayName = profile?.display_name ?? 'Sidetrack Listener';
  const metadata = buildProfileMetadata(displayName);

  if (options?.loading) {
    return { metadata, body: '<p class="state state-loading">Loading profile…</p>', state: 'loading' };
  }

  if (options?.error || !profile) {
    const errorMessage = options?.error ?? 'Profile not found.';
    return {
      metadata,
      body: `<p class="state state-error">${errorMessage}</p>`,
      state: 'error',
      errorMessage,
    };
  }

  const metricCards = profile.taste_metrics.map((metric) => ({
    title: metric.label,
    value: metric.unit === 'bpm' ? `${metric.value.toFixed(0)} ${metric.unit}` : metric.value.toFixed(2),
    subtitle: metric.description ?? (metric.percentile ? `Top ${(metric.percentile * 100).toFixed(0)}%` : undefined),
    trend: metric.unit === 'index' && metric.percentile ? `↑ ${(metric.percentile * 100).toFixed(0)} percentile` : undefined,
  }));

  const artistChart = renderBarChart(
    profile.top_artists.map((artist, index) => ({ label: artist.name, value: artist.play_count, accent: index === 0 })),
    { title: 'Top Artists', unit: 'plays', cta: 'These refresh as new listens sync from workers.' }
  );

  const genreChart = renderBarChart(
    profile.top_genres.map((genre, index) => ({ label: genre.name, value: genre.play_count, accent: index === 0 })),
    { title: 'Top Genres', unit: 'plays' }
  );

  const timelineChart = renderLineChart(
    profile.timeline.map((point) => ({
      label: new Date(point.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
      value: point.play_count,
    })),
    { title: 'Listening Timeline', unit: ' plays', cta: 'Responsive SVG keeps the chart crisp on any screen.' }
  );

  const body = `
<article class="profile-page">
  <header class="profile-hero">
    <p class="profile-source">${profile.source === 'api' ? 'Live API' : 'Fallback sample data'}</p>
    <h1>${displayName}</h1>
    <p class="profile-range">Range: ${profile.range ?? 'custom'} · Updated ${new Date(profile.fetched_at).toLocaleString()}</p>
  </header>
  ${renderMetricGrid(metricCards)}
  <div class="profile-charts">
    ${artistChart}
    ${genreChart}
    ${timelineChart}
  </div>
  ${renderNowPlaying(profile)}
</article>
  `.trim();

  return { metadata, body, state: 'ready' };
}
