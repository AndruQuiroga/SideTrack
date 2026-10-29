import type { SinglesSessionDetail } from '@sidetrack/api-client';
import { AlbumArt } from './album-art';

type Song = SinglesSessionDetail['songs'][number];

export function SinglesSongCard({ song, sessionId }: { song: Song; sessionId: string }) {
  const first = song.rating_summary?.first;
  return (
    <article className="singles-pick" data-song-id={song.id} data-night-id={sessionId}>
      {song.artwork_source_url ? (
        <a
          href={song.artwork_source_url}
          target="_blank"
          rel="noreferrer"
          aria-label={`Artwork source for ${song.title}`}
        >
          <AlbumArt url={song.cover_url} title={`${song.title} by ${song.artist_name}`} />
        </a>
      ) : (
        <AlbumArt url={song.cover_url} title={`${song.title} by ${song.artist_name}`} />
      )}
      <div className="singles-pick-identity">
        <h3>{song.title}</h3>
        <p className="singles-pick-artist">{song.artist_name}</p>
        <p className="singles-pick-submitter">
          {song.submissions.length
            ? `Submitted by ${song.submissions.map((s) => s.display_name).join(', ')}`
            : 'Submitter unavailable'}
        </p>
      </div>
      <p className="singles-pick-score">
        {!first ? (
          'Rating summary unavailable'
        ) : first.average == null ? (
          'Not rated yet'
        ) : (
          <>
            <strong>
              {new Intl.NumberFormat('en-US', {
                minimumFractionDigits: 1,
                maximumFractionDigits: 1,
              }).format(first.average)}{' '}
              <span>/ 5</span>
            </strong>
            <span>
              {first.count} first-listen {first.count === 1 ? 'rating' : 'ratings'}
            </span>
          </>
        )}
      </p>
      <details className="singles-impressions">
        <summary>Listener impressions</summary>
        <div className="singles-impressions-body">
          {(['first', 'final'] as const).map((phase) => {
            const ratings = song.ratings.filter((rating) => rating.phase === phase);
            if (phase === 'final' && !ratings.length) return null;
            return (
              <section key={phase} aria-label={`${phase} ratings for ${song.title}`}>
                <h4>{phase === 'first' ? 'First listen' : 'Final ratings'}</h4>
                {ratings.length ? (
                  <ul>
                    {ratings.map((rating) => (
                      <li key={rating.id}>
                        <div className="singles-listener-score">
                          <strong>{rating.display_name}</strong>
                          <span>{rating.value} / 5</span>
                        </div>
                        {rating.review && <p className="singles-review">{rating.review}</p>}
                        {rating.source_url && (
                          <a
                            className="small"
                            href={rating.source_url}
                            target="_blank"
                            rel="noreferrer"
                          >
                            Rating source ↗
                          </a>
                        )}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="muted">No first-listen ratings recorded.</p>
                )}
              </section>
            );
          })}
          <div className="singles-pick-links">
            {song.url && (
              <a href={song.url} target="_blank" rel="noreferrer">
                Song link ↗
              </a>
            )}
            {song.artwork_source_url && (
              <a href={song.artwork_source_url} target="_blank" rel="noreferrer">
                Artwork source ↗
              </a>
            )}
            {song.source_url && (
              <a href={song.source_url} target="_blank" rel="noreferrer">
                Source message ↗
              </a>
            )}
          </div>
        </div>
      </details>
    </article>
  );
}

export function SinglesSongGrid({ event }: { event: SinglesSessionDetail }) {
  if (!event.songs.length) return <p className="muted">No songs were recorded for this session.</p>;
  return (
    <div className="singles-pick-grid">
      {event.songs.map((song) => (
        <SinglesSongCard key={`${event.id}:${song.id}`} song={song} sessionId={event.id} />
      ))}
    </div>
  );
}
