import { WeekDetailWithRatings } from '../api/weeks';
import { PageMetadata, buildWinnersMetadata } from './metadata';

export interface GalleryRenderResult {
  metadata: PageMetadata;
  body: string;
  state: 'loading' | 'error' | 'ready';
  errorMessage?: string;
}

export interface TagFilters {
  genre?: string;
  decade?: string;
  country?: string;
}

interface FilterOptions {
  genres: string[];
  decades: string[];
  countries: string[];
}

function buildFilterOptions(weeks: WeekDetailWithRatings[]): FilterOptions {
  const genres = new Set<string>();
  const decades = new Set<string>();
  const countries = new Set<string>();

  weeks.forEach((week) => {
    week.nominations.forEach((nomination) => {
      if (nomination.genre) genres.add(nomination.genre);
      if (nomination.decade) decades.add(nomination.decade);
      if (nomination.country) countries.add(nomination.country);
    });
  });

  return {
    genres: Array.from(genres).sort(),
    decades: Array.from(decades).sort(),
    countries: Array.from(countries).sort(),
  };
}

function applyTagFilters(weeks: WeekDetailWithRatings[], filters?: TagFilters): WeekDetailWithRatings[] {
  if (!filters || (!filters.genre && !filters.decade && !filters.country)) return weeks;

  return weeks.filter((week) => {
    return week.nominations.some((nomination) => {
      const matchesGenre = !filters.genre || nomination.genre === filters.genre;
      const matchesDecade = !filters.decade || nomination.decade === filters.decade;
      const matchesCountry = !filters.country || nomination.country === filters.country;
      return matchesGenre && matchesDecade && matchesCountry;
    });
  });
}

function renderFilters(options: FilterOptions, filters?: TagFilters): string {
  const renderSelect = (label: string, name: keyof TagFilters, values: string[]): string => {
    const choices = ['<option value="">All</option>', ...values.map((value) => `<option value="${value}">${value}</option>`)].join('');
    const selectedValue = filters?.[name] ?? '';
    return `
    <label class="filter-field">
      <span>${label}</span>
      <select name="${name}" aria-label="Filter by ${label.toLowerCase()}" data-selected="${selectedValue}">
        ${choices}
      </select>
    </label>`;
  };

  return `
  <form class="filters" aria-label="Filter weeks by tag">
    ${renderSelect('Genre', 'genre', options.genres)}
    ${renderSelect('Decade', 'decade', options.decades)}
    ${renderSelect('Country', 'country', options.countries)}
  </form>`;
}

function renderCard(week: WeekDetailWithRatings): string {
  const ratingCopy = week.aggregates.rating_average
    ? `${week.aggregates.rating_average.toFixed(2)} avg · ${week.aggregates.rating_count} ratings`
    : 'No ratings yet';

  const topNomination = week.nominations[0];
  const winnerLine = topNomination
    ? `${topNomination.pitch ?? 'Winner announced'} (${topNomination.genre ?? 'Genre TBD'})`
    : 'Winner pending';

  const tags = [topNomination?.genre, topNomination?.decade, topNomination?.country].filter(Boolean).join(' · ');

  const ratingSummaryCopy = week.rating_summary
    ? `${week.rating_summary.average?.toFixed(2) ?? '—'} (${week.rating_summary.count} reviews)`
    : ratingCopy;

  return `
<article class="week-card" aria-labelledby="week-${week.id}-title">
  <header class="week-card__header">
    <p class="week-label">${week.label}</p>
    <p class="week-meta">${ratingSummaryCopy}</p>
  </header>
  <p id="week-${week.id}-title" class="week-summary">${winnerLine}</p>
  <p class="week-tags">${tags || 'Tags pending'}</p>
  <a class="week-link" href="/weeks/${week.id}" aria-label="View details for ${week.label}">Open week detail</a>
</article>
`;
}

function renderResponsiveEmptyState(): string {
  return '<p class="state state-empty" role="status">No winners found yet — check back soon.</p>';
}

export function renderWinnersGallery(
  weeks: WeekDetailWithRatings[] | undefined,
  options?: { loading?: boolean; error?: string; filters?: TagFilters }
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

  const filters = options?.filters;
  const filteredWeeks = applyTagFilters(weeks ?? [], filters);
  const filterOptions = buildFilterOptions(weeks ?? []);

  const sortedWeeks = [...filteredWeeks].sort((a, b) => {
    const aDate = a.discussion_at ?? a.created_at ?? '';
    const bDate = b.discussion_at ?? b.created_at ?? '';
    return bDate.localeCompare(aDate);
  });

  const cards = sortedWeeks.map((week) => renderCard(week)).join('\n');
  const emptyCopy = renderResponsiveEmptyState();
  const filterBar = renderFilters(filterOptions, filters);

  return {
    metadata: buildWinnersMetadata(sortedWeeks.length),
    body: `${filterBar}${sortedWeeks.length ? `<section class="gallery">${cards}</section>` : emptyCopy}`,
    state: 'ready',
  };
}
