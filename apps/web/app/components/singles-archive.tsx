import Link from 'next/link';
import type { SinglesSessionRead, SinglesSessionDetail } from '@sidetrack/api-client';
import type { Access } from '../lib/server-api';
import { AccessNotice } from './ui';

export function singlesDate(value: string | null): string {
  if (!value) return 'Date unavailable';
  return new Intl.DateTimeFormat('en-US', {
    timeZone: 'UTC',
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  }).format(new Date(`${value}T12:00:00Z`));
}

function sessionTitle(session: SinglesSessionRead) {
  return session.week_number == null ? 'Singles Night' : `Singles Night ${session.week_number}`;
}

export function SinglesArchive({ archive }: { archive: Access<SinglesSessionRead[]> }) {
  if (archive.state !== 'ok')
    return (
      <AccessNotice
        state={archive.state === 'not-found' ? 'unavailable' : archive.state}
        what="Singles Night archive"
        returnTo="/club/singles"
      />
    );
  if (!archive.data.length)
    return (
      <section className="access-state">
        <h2>No Singles Night sessions yet</h2>
        <p>Imported sessions will appear here.</p>
      </section>
    );
  return (
    <div className="singles-sessions">
      {archive.data.map((session) => (
        <article key={session.id}>
          <p className="eyebrow">{singlesDate(session.event_date)}</p>
          <h2>
            <Link href={`/club/singles/${session.id}`}>{sessionTitle(session)}</Link>
          </h2>
          <p>
            {session.song_count} {session.song_count === 1 ? 'song' : 'songs'} ·{' '}
            {session.rating_count} {session.rating_count === 1 ? 'rating' : 'ratings'}
          </p>
          <a href={session.source_url} target="_blank" rel="noreferrer">
            View Discord thread ↗
          </a>
        </article>
      ))}
    </div>
  );
}

export function SinglesDetail({
  session,
  id,
}: {
  session: Access<SinglesSessionDetail>;
  id: string;
}) {
  if (session.state === 'not-found')
    return (
      <section className="access-state">
        <h2>Session not found</h2>
        <Link href="/club/singles">Back to Singles Night</Link>
      </section>
    );
  if (session.state !== 'ok')
    return (
      <AccessNotice
        state={session.state}
        what="Singles Night session"
        returnTo={`/club/singles/${id}`}
      />
    );
  const event = session.data;
  return (
    <>
      <header className="singles-heading">
        <h2>{sessionTitle(event)}</h2>
        <p>{singlesDate(event.event_date)}</p>
        {event.event_at && (
          <p>
            {new Intl.DateTimeFormat('en-US', {
              timeZone: 'UTC',
              hour: '2-digit',
              minute: '2-digit',
              timeZoneName: 'short',
            }).format(new Date(event.event_at))}
          </p>
        )}
        <a href={event.source_url} target="_blank" rel="noreferrer">
          View Discord thread ↗
        </a>
        <details>
          <summary>Original Discord label</summary>
          <p>{event.original_label}</p>
        </details>
      </header>
      {!event.songs.length && <p>No songs were recorded for this session.</p>}
      <div className="singles-songs">
        {event.songs.map((song, index) => (
          <article key={song.id}>
            <div className="singles-song-heading">
              <span className="eyebrow">Track {index + 1}</span>
              <h3>{song.title}</h3>
              <p>{song.artist_name}</p>
              <p>
                {song.submissions.length
                  ? `Submitted by ${song.submissions.map((s) => s.display_name).join(', ')}`
                  : 'Submitter unavailable'}
              </p>
              <div className="actions">
                {song.url && (
                  <a href={song.url} target="_blank" rel="noreferrer">
                    Song link ↗
                  </a>
                )}
                {song.source_url && (
                  <a href={song.source_url} target="_blank" rel="noreferrer">
                    Source message ↗
                  </a>
                )}
              </div>
            </div>
            <div className="singles-phases">
              {(['first', 'final'] as const).map((phase) => {
                const ratings = song.ratings.filter((rating) => rating.phase === phase);
                return (
                  <section key={phase} aria-label={`${phase} ratings for ${song.title}`}>
                    <h4>{phase === 'first' ? 'First listen' : 'Final ratings'}</h4>
                    {ratings.length ? (
                      <ul>
                        {ratings.map((rating) => (
                          <li key={rating.id}>
                            <div>
                              <strong>{rating.display_name}</strong>
                              <span>{rating.value} / 5</span>
                            </div>
                            {rating.review && <p className="singles-review">{rating.review}</p>}
                            {rating.source_url && (
                              <a href={rating.source_url} target="_blank" rel="noreferrer">
                                Source ↗
                              </a>
                            )}
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <p className="muted">
                        No {phase === 'first' ? 'first-listen' : 'final'} ratings recorded.
                      </p>
                    )}
                  </section>
                );
              })}
            </div>
          </article>
        ))}
      </div>
    </>
  );
}
