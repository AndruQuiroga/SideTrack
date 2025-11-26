import { WeekDetailWithRatings } from '../api/weeks';
import { PageMetadata, buildWeekMetadata } from './metadata';

export interface WeekDetailRenderResult {
  metadata: PageMetadata;
  body: string;
  state: 'loading' | 'error' | 'ready';
  errorMessage?: string;
}

function renderNominations(week: WeekDetailWithRatings): string {
  if (!week.nominations.length) return '<p class="state state-empty">No nominees yet.</p>';

  const sorted = [...week.nominations].sort((a, b) => b.vote_summary.points - a.vote_summary.points);
  return `
<ul class="nomination-list">
  ${sorted
    .map((nomination) => {
      const pitch = nomination.pitch ?? 'No pitch provided';
      const ratingCopy = nomination.rating_summary.average
        ? `${nomination.rating_summary.average.toFixed(2)} avg / ${nomination.rating_summary.count} ratings`
        : 'Ratings pending';
      return `<li class="nomination">
        <h3>${nomination.album_id}</h3>
        <p class="pitch">${pitch}</p>
        <p class="tags">${[nomination.genre_tag, nomination.decade_tag, nomination.country_tag].filter(Boolean).join(' · ')}</p>
        <p class="votes">${nomination.vote_summary.points} pts (${nomination.vote_summary.first_place} first-place)</p>
        <p class="ratings">${ratingCopy}</p>
      </li>`;
    })
    .join('\n')}
</ul>`;
}

function renderRatingSummary(week: WeekDetailWithRatings): string {
  const summary = week.rating_summary;
  if (!summary) {
    return '<p class="state state-empty">No rating summary available.</p>';
  }

  const histogramRows = summary.histogram?.map((bin) => `<li>${bin.value}: ${bin.count}</li>`).join('') ?? '';
  return `
<section class="rating-summary">
  <p>Average: ${summary.average?.toFixed(2) ?? '—'} from ${summary.count} ratings</p>
  ${histogramRows ? `<ul class="histogram">${histogramRows}</ul>` : ''}
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
    <p class="week-label">${week.label}</p>
    <p class="week-date">Discussion: ${week.discussion_at ?? 'TBD'}</p>
    <p class="week-rating">${week.aggregates.rating_average ? `${week.aggregates.rating_average.toFixed(2)} avg` : 'No ratings yet'}</p>
    <p class="week-source">${week.source === 'legacy' ? 'Legacy data' : 'Live API'}</p>
  </header>`;

  const nominations = renderNominations(week);
  const ratingSummary = renderRatingSummary(week);

  return {
    metadata,
    body: `<article class="week-detail">${header}${ratingSummary}${nominations}</article>`,
    state: 'ready',
  };
}
