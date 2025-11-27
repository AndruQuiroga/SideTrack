import { WeekDetailWithRatings } from '../api/weeks';
import { getDiscordGuildId } from '../config';
import { PageMetadata, buildWeekMetadata } from './metadata';

export interface WeekDetailRenderResult {
  metadata: PageMetadata;
  body: string;
  state: 'loading' | 'error' | 'ready';
  errorMessage?: string;
}

function buildDiscordThreadLink(threadId?: number | null): string | undefined {
  if (!threadId) return undefined;
  const guildId = getDiscordGuildId();
  const channelId = String(threadId);
  const serverPrefix = guildId ?? '@me';
  return `https://discord.com/channels/${serverPrefix}/${channelId}`;
}

function renderThreadLinks(week: WeekDetailWithRatings): string {
  const links = [
    { label: 'Nominations thread', id: week.nominations_thread_id },
    { label: 'Poll thread', id: week.poll_thread_id },
    { label: 'Winner thread', id: week.winner_thread_id },
    { label: 'Ratings thread', id: week.ratings_thread_id },
  ]
    .map((entry) => {
      const url = buildDiscordThreadLink(entry.id);
      if (!url) return '';
      return `<li><a href="${url}" rel="noopener" target="_blank">${entry.label}</a></li>`;
    })
    .filter(Boolean)
    .join('');

  return links ? `<ul class="thread-links" aria-label="Discord threads">${links}</ul>` : '';
}

function renderNomination(nomination: WeekDetailWithRatings['nominations'][number]): string {
  const pitch = nomination.pitch ?? 'No pitch provided';
  const ratingCopy = nomination.rating_summary.average
    ? `${nomination.rating_summary.average.toFixed(2)} avg / ${nomination.rating_summary.count} ratings`
    : 'Ratings pending';
  const tags = [nomination.genre, nomination.decade, nomination.country].filter(Boolean).join(' · ');

  return `
  <li class="nomination">
    <div class="nomination__heading">
      <h3>${nomination.album_id}</h3>
      <span class="nomination__votes" aria-label="${nomination.vote_summary.points} points">${nomination.vote_summary.points} pts</span>
    </div>
    <p class="pitch">${pitch}</p>
    <p class="tags">${tags || 'No tags'}</p>
    <dl class="nomination__stats">
      <div><dt>1st place</dt><dd>${nomination.vote_summary.first_place}</dd></div>
      <div><dt>2nd place</dt><dd>${nomination.vote_summary.second_place}</dd></div>
      <div><dt>Total ballots</dt><dd>${nomination.vote_summary.total_votes}</dd></div>
      <div><dt>Ratings</dt><dd>${ratingCopy}</dd></div>
    </dl>
  </li>`;
}

function renderNominations(week: WeekDetailWithRatings): string {
  if (!week.nominations.length) return '<p class="state state-empty">No nominees yet.</p>';

  const sorted = [...week.nominations].sort((a, b) => b.vote_summary.points - a.vote_summary.points);
  const items = sorted.map((nomination) => renderNomination(nomination)).join('\n');

  return `<ul class="nomination-list" aria-label="Nominees and poll results">${items}</ul>`;
}

function renderRatingSummary(week: WeekDetailWithRatings): string {
  const summary = week.rating_summary;
  if (!summary) {
    return '<p class="state state-empty">No rating summary available.</p>';
  }

  const histogramRows = summary.histogram
    ?.map((bin) => `<li aria-label="${bin.count} ratings at ${bin.value}"><span>${bin.value.toFixed(1)}</span><span>${bin.count}</span></li>`)
    .join('') ?? '';

  const reviewExcerpt = summary.count > 0 ? '<p class="reviews">Review excerpts not yet ingested; check Discord threads for context.</p>' : '';

  return `
<section class="rating-summary" aria-label="Ratings overview">
  <p>Average: ${summary.average?.toFixed(2) ?? '—'} from ${summary.count} ratings</p>
  ${histogramRows ? `<ul class="histogram" aria-label="Rating histogram">${histogramRows}</ul>` : ''}
  ${reviewExcerpt}
</section>
`;
}

export function renderWeekDetail(
  week: WeekDetailWithRatings | undefined,
  options?: { loading?: boolean; error?: string }
): WeekDetailRenderResult {
  if (options?.loading) {
    return {
      metadata: buildWeekMetadata('Loading week'),
      body: '<p class="state state-loading">Loading week details…</p>',
      state: 'loading',
    };
  }

  if (!week) {
    const errorMessage = options?.error ?? 'Week not found.';
    return {
      metadata: buildWeekMetadata('Week unavailable'),
      body: `<p class="state state-error">${errorMessage}</p>`,
      state: 'error',
      errorMessage,
    };
  }

  const metadata = buildWeekMetadata(week.label, `${week.aggregates.rating_average ?? 'No'} avg rating`);
  const header = `<header class="week-header">
    <div class="week-header__primary">
      <p class="week-label">${week.label}</p>
      <p class="week-date">Discussion: ${week.discussion_at ?? 'TBD'}</p>
      <p class="week-tags">${[week.nominations[0]?.genre, week.nominations[0]?.decade, week.nominations[0]?.country]
        .filter(Boolean)
        .join(' · ')}</p>
    </div>
    <div class="week-header__meta">
      <p class="week-rating">${week.aggregates.rating_average ? `${week.aggregates.rating_average.toFixed(2)} avg` : 'No ratings yet'}</p>
    </div>
  </header>`;

  const nominations = renderNominations(week);
  const ratingSummary = renderRatingSummary(week);
  const threadLinks = renderThreadLinks(week);

  return {
    metadata,
    body: `<article class="week-detail">${header}${threadLinks}<section class="week-section">${ratingSummary}</section><section class="week-section">${nominations}</section></article>`,
    state: 'ready',
  };
}
