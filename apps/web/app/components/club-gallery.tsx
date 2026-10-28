'use client';
import Link from 'next/link';
import type { Route } from 'next';
import { useEffect, useMemo, useState } from 'react';
import type { WeekDetailWithRatings } from '../lib/api/weeks';
import {
  archiveUrl,
  filterArchive,
  formatUtc,
  newestFirst,
  parseArchiveState,
  winnerTitle,
} from '../lib/club';
import type { ArchiveState } from '../lib/club';
import { WeekCard } from './week-card';
import { RatingBadge } from './rating-badge';

export function ClubGallery({
  weeks,
  initialState,
}: {
  weeks: WeekDetailWithRatings[];
  initialState?: ArchiveState;
}) {
  const [state, setState] = useState<ArchiveState>(
    initialState ?? parseArchiveState(new URLSearchParams()),
  );
  useEffect(() => {
    const restore = () => setState(parseArchiveState(new URLSearchParams(window.location.search)));
    window.addEventListener('popstate', restore);
    return () => window.removeEventListener('popstate', restore);
  }, []);
  function update(next: ArchiveState) {
    setState(next);
    window.history.replaceState(window.history.state, '', archiveUrl(next));
  }
  const filtered = useMemo(() => filterArchive(weeks, state), [weeks, state]);
  const latest = [...weeks].filter((w) => w.winner_album_id).sort(newestFirst)[0];
  const tags = [
    ...new Set(
      weeks
        .flatMap((w) => w.nominations.flatMap((n) => [n.genre, n.decade, n.country]))
        .filter((value): value is string => Boolean(value)),
    ),
  ].sort();
  const returnTo = archiveUrl(state);
  if (!weeks.length)
    return (
      <section className="access-state">
        <h2>No archive weeks yet</h2>
        <p>Recorded winners will appear here.</p>
      </section>
    );
  return (
    <>
      {latest && (
        <p className="small muted">
          Latest winner: <Link href={`/club/weeks/${latest.id}`}>{winnerTitle(latest)}</Link> ·{' '}
          {formatUtc(latest.discussion_at ?? latest.created_at)}
        </p>
      )}
      <div className="archive-toolbar">
        <label className="field archive-search">
          Search archive
          <input
            type="search"
            placeholder="Album, artist or week"
            value={state.q}
            maxLength={160}
            onChange={(e) => update({ ...state, q: e.target.value })}
          />
        </label>
        <label className="field">
          Nomination metadata
          <select value={state.tag} onChange={(e) => update({ ...state, tag: e.target.value })}>
            <option value="">All tags</option>
            {tags.map((tag) => (
              <option key={tag}>{tag}</option>
            ))}
          </select>
        </label>
        <label className="field">
          Sort archive
          <select
            value={state.sort}
            onChange={(e) => update({ ...state, sort: e.target.value as ArchiveState['sort'] })}
          >
            <option value="newest">Newest first</option>
            <option value="rating">Highest rated</option>
          </select>
        </label>
        <label className="field">
          Archive view
          <select
            value={state.view}
            onChange={(e) => update({ ...state, view: e.target.value as ArchiveState['view'] })}
          >
            <option value="grid">Grid</option>
            <option value="list">List</option>
          </select>
        </label>
      </div>
      <p className="small muted" role="status">
        {filtered.length} {filtered.length === 1 ? 'week' : 'weeks'}
        {state.tag && ' · Tag matches nomination metadata'}
      </p>
      {!filtered.length ? (
        <section className="access-state">
          <h2>No weeks match these filters</h2>
          <p>Try another album, artist, week, or tag.</p>
          <button
            className="button"
            onClick={() => update(parseArchiveState(new URLSearchParams()))}
          >
            Clear filters
          </button>
        </section>
      ) : state.view === 'grid' ? (
        <div className="album-grid">
          {filtered.map((week) => (
            <WeekCard key={week.id} week={week} returnTo={returnTo} />
          ))}
        </div>
      ) : (
        <table className="archive-table">
          <thead>
            <tr>
              <th scope="col">Week</th>
              <th scope="col">Album / artist</th>
              <th scope="col" className="optional-column">
                Discussion
              </th>
              <th scope="col">Rating</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((week) => (
              <tr key={week.id}>
                <td>{week.week_number ?? week.label}</td>
                <td>
                  <Link
                    href={`/club/weeks/${week.id}?from=${encodeURIComponent(returnTo)}` as Route}
                  >
                    {winnerTitle(week)}
                  </Link>
                  {week.winner_album && (
                    <span className="small muted">{week.winner_album.artist_name}</span>
                  )}
                </td>
                <td className="small muted optional-column">
                  {formatUtc(week.discussion_at ?? week.created_at)}
                </td>
                <td>
                  <RatingBadge
                    value={week.aggregates.rating_average}
                    count={week.aggregates.rating_count}
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </>
  );
}
