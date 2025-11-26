import { WeekDetailWithRatings } from '../api/weeks';
import { PageMetadata, buildWinnersMetadata } from './metadata';

export interface GalleryRenderResult {
  metadata: PageMetadata;
  body: string;
  state: 'loading' | 'error' | 'ready';
  errorMessage?: string;
}

function renderCard(week: WeekDetailWithRatings): string {
  const ratingCopy = week.aggregates.rating_average
    ? `${week.aggregates.rating_average.toFixed(2)} avg · ${week.aggregates.rating_count} ratings`
    : 'No ratings yet';

  const topNomination = week.nominations[0];
  const winnerLine = topNomination
    ? `${topNomination.pitch ?? 'Winner announced'} (${topNomination.genre_tag ?? 'Genre TBD'})`
    : 'Winner pending';

  const tags = [topNomination?.genre_tag, topNomination?.decade_tag, topNomination?.country_tag]
    .filter(Boolean)
    .join(' · ');

  const sourceBadge = week.source === 'legacy' ? 'Legacy data' : 'Live API';

  return `
<article class="week-card">
  <header>
    <p class="week-label">${week.label}</p>
    <p class="week-meta">${ratingCopy}</p>
  </header>
  <p class="week-summary">${winnerLine}</p>
  <p class="week-tags">${tags || 'Tags pending'}</p>
  <p class="week-source">${sourceBadge}</p>
</article>
`;
}

export function renderWinnersGallery(
  weeks: WeekDetailWithRatings[] | undefined,
  options?: { loading?: boolean; error?: string }
): GalleryRenderResult {
  if (options?.loading) {
    return {
      metadata: buildWinnersMetadata(weeks?.length ?? 0),
      body: '<p class="state state-loading">Loading winners…</p>',
      state: 'loading',
    };
  }

  if (options?.error) {
    return {
      metadata: buildWinnersMetadata(weeks?.length ?? 0),
      body: `<p class="state state-error">${options.error}</p>`,
      state: 'error',
      errorMessage: options.error,
    };
  }

  const sortedWeeks = [...(weeks ?? [])].sort((a, b) => {
    const aDate = a.discussion_at ?? a.created_at ?? '';
    const bDate = b.discussion_at ?? b.created_at ?? '';
    return bDate.localeCompare(aDate);
  });

  const cards = sortedWeeks.map((week) => renderCard(week)).join('\n');
  const emptyCopy = '<p class="state state-empty">No winners found yet — check back soon.</p>';

  return {
    metadata: buildWinnersMetadata(sortedWeeks.length),
    body: sortedWeeks.length ? `<section class="gallery">${cards}</section>` : emptyCopy,
    state: 'ready',
  };
}
