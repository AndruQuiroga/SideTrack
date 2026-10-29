import Link from 'next/link';
import type { SinglesSessionRead, SinglesSessionDetail } from '@sidetrack/api-client';
import type { Access } from '../lib/server-api';
import { AccessNotice } from './ui';
import { SinglesSongGrid } from './singles-song-gallery';

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
      <SinglesSongGrid event={event} />
    </>
  );
}
